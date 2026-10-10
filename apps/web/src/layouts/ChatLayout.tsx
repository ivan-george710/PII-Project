import type { ReactNode } from "react";
import type { Conversation } from "../lib/schemas";
import { WorkspaceShell } from "../components/WorkspaceShell";
export function ChatLayout({conversations, activeConversation, onSelect, onNew, children}: {conversations: Conversation[]; activeConversation?: string; onSelect:(id:string)=>void; onNew:()=>void; children:ReactNode}) {
  return <WorkspaceShell title="Chat" navigation={<><button className="new-chat-button" type="button" onClick={onNew}>New chat</button><nav className="conversation-history" aria-label="Chat history"><p className="nav-label">Recent chats</p>{conversations.map(item => <button className="history-item" type="button" key={item.id} aria-current={item.id === activeConversation ? "page" : undefined} onClick={() => onSelect(item.id)}>{item.title === "New chat" ? "Untitled conversation" : item.title}</button>)}</nav></>}><div className="chat-main">{children}</div></WorkspaceShell>;
}
