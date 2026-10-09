import { useChat } from "../features/chat/useChat";
import { useDemoSamples } from "../features/chat/useDemoSamples";
import { ChatComposer } from "../features/chat/ChatComposer";
import { MessageList } from "../features/chat/MessageList";
import { ChatLayout } from "../layouts/ChatLayout";
import { LoadingIndicator } from "../components/LoadingIndicator";
export default function Chat() {
  const chat = useChat();
  const samples = useDemoSamples({
    setDraft: chat.setDraft,
    addAttachment: chat.addAttachment,
  });
  return (
    <ChatLayout
      conversations={chat.conversations}
      activeConversation={chat.activeConversation}
      onSelect={(id) => void chat.selectConversation(id)}
      onNew={() => void chat.newConversation()}
    >
      {chat.loading ? (
        <div className="chat-loading">
          <LoadingIndicator label="Loading your chats…" />
        </div>
      ) : (
        <div
          className={`conversation-surface ${chat.messages.length ? "has-messages" : "is-empty"}`}
        >
          {chat.messages.length ? (
            <MessageList messages={chat.messages} />
          ) : (
            <div className="chat-welcome">
              <h1>Where should we begin?</h1>
              <p>Write a message or attach a file.</p>
            </div>
          )}
          <div className="composer-dock">
            <ChatComposer
              draft={chat.draft}
              setDraft={chat.setDraft}
              attachments={chat.attachments}
              onRemoveAttachment={chat.removeAttachment}
              onUpload={(file) => void chat.uploadFileWithStatus(file)}
              onSend={() => void chat.send()}
              onCancel={chat.cancel}
              processing={chat.processing}
              samples={samples.samples}
              samplesLoading={samples.loading}
              samplesError={samples.error}
              selectingSample={samples.selecting}
              onSelectSample={(sample) => void samples.select(sample)}
              onRetrySamples={() => void samples.reload()}
              error={chat.error}
              onRetry={chat.retry}
              retryAvailable={!!chat.lastRequest}
            />
            <p className="composer-note">
              Company privacy rules apply before a message is sent.
            </p>
          </div>
        </div>
      )}
    </ChatLayout>
  );
}
