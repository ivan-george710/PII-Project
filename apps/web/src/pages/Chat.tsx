import { useCallback } from "react";
import { useChat } from "../features/chat/useChat";
import { useDemoSamples } from "../features/chat/useDemoSamples";
import { ChatComposer } from "../features/chat/ChatComposer";
import { MessageList } from "../features/chat/MessageList";
import { ChatLayout } from "../layouts/ChatLayout";

export default function Chat() {
  const chat = useChat();
  const samples = useDemoSamples({
    setDraft: chat.setDraft,
    addAttachment: chat.addAttachment,
  });

  if (chat.loading) return <p role="status">Loading conversation…</p>;
  return (
    <ChatLayout
      conversations={chat.conversations}
      activeConversation={chat.activeConversation}
      onSelect={(id) => void chat.selectConversation(id)}
      onNew={() => void chat.newConversation()}
    >
      <MessageList messages={chat.messages} />
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
    </ChatLayout>
  );
}
