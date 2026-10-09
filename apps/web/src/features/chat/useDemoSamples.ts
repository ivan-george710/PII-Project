import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  attachment,
  demoSamplesResponse,
  type Attachment,
  type DemoSample,
} from "../../lib/schemas";
import { useAuth } from "../auth/useAuth";

export function useDemoSamples({
  setDraft,
  addAttachment,
}: {
  setDraft: (text: string) => void;
  addAttachment: (attachment: Attachment) => void;
}) {
  const { identity } = useAuth();
  const [samples, setSamples] = useState<DemoSample[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selecting, setSelecting] = useState<string | null>(null);
  const requestIds = useState(() => new Map<string, string>())[0];

  const load = useCallback(async () => {
    if (!identity) return;
    setLoading(true);
    setError("");
    try {
      const response = await api("/demo/samples", demoSamplesResponse);
      setSamples(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Test samples unavailable");
      setSamples([]);
    } finally {
      setLoading(false);
    }
  }, [identity]);

  useEffect(() => {
    void load();
  }, [load]);

  const select = useCallback(async (sample: DemoSample) => {
    if (selecting) return;
    setError("");
    if (sample.kind === "message") {
      setDraft(sample.text);
      return;
    }
    if (!identity) return;
    setSelecting(sample.id);
    try {
      let requestId = requestIds.get(sample.id);
      if (!requestId) {
        requestId = crypto.randomUUID();
        requestIds.set(sample.id, requestId);
      }
      const result = await api(
        `/demo/samples/${sample.id}/attachments`,
        attachment,
        {
          method: "POST",
          body: JSON.stringify({ client_request_id: requestId }),
        },
        identity.csrf_token,
      );
      addAttachment(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sample could not be attached");
    } finally {
      setSelecting(null);
    }
  }, [addAttachment, identity, requestIds, selecting, setDraft]);

  return { samples, loading, error, selecting, select, reload: load };
}
