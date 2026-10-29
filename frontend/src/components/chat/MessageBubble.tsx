import { motion } from "motion/react";
import { Info } from "lucide-react";
import { memo } from "react";
import { INTENT_LABEL } from "../../lib/labels";
import { spring } from "../../lib/motion";
import { SentimentChip, SourceChip } from "../ui/Badges";
import type { ChatMessage } from "../../types";

interface Props { m: ChatMessage; selected: boolean; onInspect: (m: ChatMessage) => void }

function MessageBubbleImpl({ m, selected, onInspect }: Props) {
  const isUser = m.role === "user";
  const a = isUser ? m.analysisFor : m.response?.analysis;
  return (
    <motion.li className={`row ${isUser ? "user" : "bot"}`}
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={spring.soft}>
      {/* user: restrained accent bubble; assistant: calm editorial text, no card */}
      <div className={isUser ? `bubble-user ${selected ? "selected" : ""}` : `reply ${selected ? "selected" : ""}`}>
        <p>{m.text}</p>
      </div>
      {a && (
        <div className="meta">
          {isUser && <SentimentChip s={a.sentiment} />}
          {isUser && <span className="chip">{INTENT_LABEL[a.intent.intent] ?? a.intent.intent}</span>}
          {!isUser && m.response && <SourceChip source={m.response.reply_source} provider={m.response.provider} />}
          {!isUser && m.response?.fallback.used && <span className="chip chip-warn">Fallback to local</span>}
          <button className="link-btn" onClick={() => onInspect(m)} aria-label={`View analysis for ${isUser ? "your" : "this"} message`}>
            <Info size={12} aria-hidden /> Details
          </button>
        </div>
      )}
    </motion.li>
  );
}
export const MessageBubble = memo(MessageBubbleImpl);
