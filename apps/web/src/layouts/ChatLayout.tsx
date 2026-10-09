import type { ReactNode } from "react";
import type { Conversation } from "../lib/schemas";

export function ChatLayout({
  conversations,
  activeConversation,
  onSelect,
  onNew,
  children,
}: {
  conversations: Conversation[];
  activeConversation?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  children: ReactNode;
}) {
  return (
    <div className="chat-layout">
      <aside aria-label="Chat history">
        <button type="button" onClick={onNew}>New chat</button>
        <nav>
          {conversations.map((item) => (
            <button
              type="button"
              key={item.id}
              aria-current={item.id === activeConversation ? "page" : undefined}
              onClick={() => onSelect(item.id)}
            >
              {item.title}
            </button>
          ))}
        </nav>
      </aside>
      <div className="chat-main">{children}</div>
    </div>
  );
}
