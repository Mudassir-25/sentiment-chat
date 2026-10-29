import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "./App";
import { caps, chatResponse } from "./test/fixtures";

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;
const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { "Content-Type": "application/json" } });

function mockApi(over: { caps?: ReturnType<typeof caps>; chat?: Handler; analytics?: Handler } = {}) {
  const calls: { url: string; body?: any }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    if (url === "/api/capabilities") return json(over.caps ?? caps());
    if (url === "/api/chat") return over.chat ? over.chat(url, init) : json(chatResponse());
    if (url === "/api/analytics") return over.analytics ? over.analytics(url, init) : json({}, 404);
    if (url.startsWith("/api/sessions")) return json({ cleared: true });
    if (url.includes("/test")) return json({ id: "openai", label: "OpenAI-compatible", configured: true, model: "m", connection: "ok", last_error: null });
    return json({}, 404);
  }));
  return calls;
}
const type = async (text: string) => {
  await userEvent.type(screen.getByLabelText("Message"), text);
  await userEvent.click(screen.getByRole("button", { name: "Send message" }));
};

test("renders main interface with empty state, mode indicator and labelled controls", async () => {
  mockApi();
  render(<App />);
  expect(screen.getByRole("heading", { name: "Sentiment Chat" })).toBeInTheDocument();
  expect(await screen.findByLabelText("Active mode: Local NLP")).toBeInTheDocument();
  expect(screen.getByText(/I'll read the room/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Open settings" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
});

test("theme toggle switches, persists, and explicit choice beats system preference", async () => {
  mockApi();
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: true, media: q, addEventListener() {}, removeEventListener() {} }));
  render(<App />);
  expect(document.documentElement.dataset.theme).toBe("dark"); // system preference on first launch
  await userEvent.click(screen.getByRole("button", { name: /Switch to Pearl/ }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("sc-theme")).toBe("light");
  cleanupAndRerender();
  expect(document.documentElement.dataset.theme).toBe("light"); // OS still dark, explicit pref wins
});
function cleanupAndRerender() {
  document.body.innerHTML = "";
  render(<App />);
}

test("mode selection works and persists", async () => {
  mockApi();
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  const dialog = screen.getByRole("dialog", { name: "Settings" });
  await userEvent.click(within(dialog).getByRole("radio", { name: /Local only/ }));
  expect(within(dialog).getByRole("radio", { name: /Local only/ })).toBeChecked();
  expect(localStorage.getItem("sc-mode")).toBe("local_only");
  expect(within(dialog).getByText(/No provider configured/)).toBeInTheDocument();
});

test("sends a message, shows reply, loading state and sentiment analysis", async () => {
  let release!: () => void;
  const gate = new Promise<void>((r) => (release = r));
  const calls = mockApi({ chat: async () => { await gate; return json(chatResponse()); } });
  render(<App />);
  await type("I finally passed my exam!");
  expect(await screen.findByRole("status", { name: "Analysing and replying" })).toBeInTheDocument();
  release();
  expect(await screen.findByText("Congratulations on your exam!")).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("status", { name: "Analysing and replying" })).not.toBeInTheDocument());
  expect(calls.find((c) => c.url === "/api/chat")?.body).toMatchObject({ message: "I finally passed my exam!", mode: "automatic" });
  expect(screen.getByTestId("sentiment-chip")).toHaveTextContent("Positive");
  await userEvent.click(screen.getAllByRole("button", { name: /View analysis/ })[0]);
  const drawer = screen.getByRole("complementary", { name: "Message analysis" });
  expect(within(drawer).getByTestId("drawer-sentiment")).toHaveTextContent("Positive");
  expect(within(drawer).getByText("Good news")).toBeInTheDocument();
  expect(within(drawer).getByText(/Not a guaranteed probability|not a guaranteed probability/i)).toBeInTheDocument();
  expect(within(drawer).getByText("exam")).toBeInTheDocument();
});

test("Enter sends and Shift+Enter does not", async () => {
  mockApi();
  render(<App />);
  const box = screen.getByLabelText("Message");
  await userEvent.type(box, "hello{Shift>}{Enter}{/Shift}there");
  expect((box as HTMLTextAreaElement).value).toBe("hello\nthere");
  await userEvent.type(box, "{Enter}");
  expect(await screen.findByText("Congratulations on your exam!")).toBeInTheDocument();
});

test("shows the sent mode in requests (local only)", async () => {
  const calls = mockApi();
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  await userEvent.click(screen.getByRole("radio", { name: /Local only/ }));
  await userEvent.click(screen.getByRole("button", { name: "Close settings" }));
  await type("hi");
  await screen.findByText("Congratulations on your exam!");
  expect(calls.find((c) => c.url === "/api/chat")?.body.mode).toBe("local_only");
});

test("backend unavailable shows instructions and never fakes a reply", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
  render(<App />);
  expect(await screen.findByText(/Backend not reachable/)).toBeInTheDocument();
  expect(screen.getByText(/uvicorn app.main:app/)).toBeInTheDocument();
  expect(screen.getByLabelText("Message")).toBeDisabled();
  expect(screen.getByLabelText("Active mode: Backend offline")).toBeInTheDocument();
});

test("chat request failure shows error, keeps text, no fake reply", async () => {
  mockApi({ chat: () => json({ detail: "Message is too long (max 1000 characters)." }, 422) });
  render(<App />);
  await type("something");
  expect(await screen.findByRole("alert")).toHaveTextContent("too long");
  expect(screen.queryByText("Congratulations on your exam!")).not.toBeInTheDocument();
  await waitFor(() => expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("something"));
});

test("fallback from AI to local is communicated", async () => {
  mockApi({
    caps: caps({ providers: [{ id: "openai", label: "OpenAI-compatible", configured: true, model: "m", connection: "untested", last_error: null }, caps().providers[1]], default_provider: "openai" }),
    chat: () => json(chatResponse({ fallback: { used: true, reason: "timeout", detail: "The provider request timed out." } })),
  });
  render(<App />);
  expect(await screen.findByLabelText("Active mode: AI enhanced")).toBeInTheDocument();
  await type("hi");
  expect(await screen.findByText(/Used local reply instead of AI: The provider timed out/)).toBeInTheDocument();
  expect(screen.getByText("Fallback to local")).toBeInTheDocument();
});

test("provider test button reports connection result", async () => {
  mockApi({ caps: caps({ providers: [{ id: "openai", label: "OpenAI-compatible", configured: true, model: "m", connection: "untested", last_error: null }, caps().providers[1]], default_provider: "openai" }) });
  render(<App />);
  await screen.findByLabelText("Active mode: AI enhanced");
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  await userEvent.click(screen.getByRole("button", { name: /Test connection/ }));
  expect(await screen.findByText(/Connection OK/)).toBeInTheDocument();
});

test("an explicitly selected unconfigured provider is not reported as usable", async () => {
  const unavailable = { id: "groq", label: "Groq", configured: false, model: "model", connection: "untested" as const, last_error: null };
  mockApi({ caps: caps({ providers: [...caps().providers, unavailable] }) });
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "groq");
  expect(screen.getByText("Groq is not configured. Choose a configured provider or use local mode.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Test connection/ })).toBeDisabled();
});

test("analytics shows real backend request metrics", async () => {
  mockApi({
    analytics: () => json({
      total_requests: 7, success_count: 6, failure_count: 1, fallback_count: 1, provider_failure_count: 1, average_latency_ms: 21.7,
      sentiment_counts: { positive: 3, neutral: 2, negative: 1 }, source_counts: { local: 4, llm: 1 },
      provider_usage: { local: 4, groq: 1 }, mode_usage: { local_only: 4, ai_enhanced: 1 },
      activity: [{ hour: "2026-10-29T12:00:00+00:00", requests: 7, failures: 1 }], retention_limit: 2000,
    }),
  });
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Analytics" }));
  expect(await screen.findByText("7")).toBeInTheDocument();
  expect(screen.getByText("22 ms")).toBeInTheDocument();
  expect(screen.getByText("groq")).toBeInTheDocument();
  expect(screen.getByText(/Actual backend requests/)).toBeInTheDocument();
});

test("Escape closes the settings dialog", async () => {
  mockApi();
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
});

test("theme change adds a temporary cross-fade class, then removes it", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  mockApi();
  render(<App />);
  expect(document.documentElement.classList.contains("theme-shift")).toBe(false);
  await userEvent.click(screen.getByRole("button", { name: /Switch to/ }));
  expect(document.documentElement.classList.contains("theme-shift")).toBe(true);
  await vi.advanceTimersByTimeAsync(500);
  expect(document.documentElement.classList.contains("theme-shift")).toBe(false);
  vi.useRealTimers();
});

test("settings separate configured AI availability from the active reply mode", async () => {
  mockApi();
  render(<App />);
  await screen.findByLabelText("Active mode: Local NLP");
  await userEvent.click(screen.getByRole("button", { name: "Open settings" }));
  const status = screen.getByLabelText("Current status");
  expect(within(status).getByText("Not configured")).toBeInTheDocument();
  expect(within(status).getByText("Local NLP")).toBeInTheDocument();
});

test("welcome content leaves once a conversation starts; technical evidence is collapsed by default", async () => {
  mockApi();
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "I finally passed my exam!" }));
  await screen.findByText("Congratulations on your exam!");
  await waitFor(() => expect(screen.queryByText(/I'll read the room/)).not.toBeInTheDocument());
  await userEvent.click(screen.getAllByRole("button", { name: /View analysis/ })[0]);
  const details = screen.getByText("Evidence, kept separate").closest("details")!;
  expect(details).not.toHaveAttribute("open");
});
