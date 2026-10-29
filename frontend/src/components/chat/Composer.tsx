import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Loader2 } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { dur, ease, spring } from "../../lib/motion";

interface Props { onSend: (t: string) => Promise<boolean | string>; disabled: boolean; pending?: boolean; offline?: boolean; max: number }

export function Composer({ onSend, disabled, pending = false, offline = false, max }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const tooLong = text.length > max;
  const canSend = !disabled && !tooLong && text.trim().length > 0;

  // Grow with content up to the CSS max-height (works in browsers without field-sizing support).
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  async function submit() {
    if (!canSend) return;
    const t = text;
    setText("");
    const r = await onSend(t);
    if (typeof r === "string") setText(r); // restore text if sending failed
    ref.current?.focus();
  }

  return (
    <form className="composer inset" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <label htmlFor="composer-input" className="sr-only">Message</label>
      <textarea
        id="composer-input" ref={ref} rows={1} value={text} disabled={offline} placeholder="Tell me how your day is going…"
        onChange={(e) => setText(e.target.value)} aria-describedby="composer-hint"
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void submit(); } }}
      />
      <div className="composer-side">
        <span id="composer-hint" className={`counter ${tooLong ? "over" : text.length > max * 0.8 ? "" : "hint"}`} aria-live="polite">
          {text.length > max * 0.8 ? `${text.length}/${max}` : "Return to send · Shift+Return for a new line"}
        </span>
        <motion.button type="submit" className={`send-btn ${pending ? "pending" : ""}`} disabled={!canSend && !pending} aria-label="Send message" aria-busy={pending}
          whileHover={canSend ? { y: -1 } : undefined} whileTap={canSend ? { scale: 0.9 } : undefined} transition={spring.snappy}
          onClick={(e) => { if (pending) e.preventDefault(); }}>
          <AnimatePresence mode="wait" initial={false}>
            {pending ? (
              <motion.span key="p" initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.6 }} transition={{ duration: dur.fast, ease }}><Loader2 size={17} className="spin" /></motion.span>
            ) : (
              <motion.span key="s" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: dur.fast, ease }}><ArrowUp size={18} strokeWidth={2.4} /></motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>
    </form>
  );
}
