import { useEffect, useRef } from "react";
import type { Message } from "../../lib/schemas";
import { AttachmentList } from "./AttachmentList";

export function MessageList({ messages }: { messages: Message[] }) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);
  return (
    <section className="message-list" aria-label="Conversation">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`message message-${message.role}`}
          aria-label={`${message.role} message`}
        >
          {message.text && <p>{message.text}</p>}
          {message.attachment_ids.length > 0 && (
            <span>{message.attachment_ids.length} attachment(s)</span>
          )}
          {message.state !== "completed" && (
            <span className="message-state">{message.state}</span>
          )}
        </article>
      ))}
      <div ref={bottom} />
    </section>
  );
}
