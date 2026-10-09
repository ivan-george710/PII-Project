import asyncio
import json
import os
import urllib.error
import urllib.request
from collections.abc import AsyncIterator

from app.llm.client import ProviderDelta, ProviderRequest
from app.schemas.common import ApiError


class OpenAIProvider:
    """OpenAI-compatible chat completions adapter for already-sanitized payloads."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderDelta]:
        request = ProviderRequest.model_validate(request.model_dump())
        if not self._api_key:
            raise ApiError(503, "PROVIDER_UNAVAILABLE", "LLM provider is unavailable")
        messages: list[dict] = []
        for message in request.messages:
            messages.append({"role": message.role, "content": message.sanitized_text})
        if request.artifacts:
            content: list[dict] = [
                {"type": "text", "text": messages[-1]["content"]}
            ]
            for artifact in request.artifacts:
                if artifact.sanitized_text is not None:
                    content.append(
                        {
                            "type": "text",
                            "text": f"[Sanitized attachment: {artifact.filename}]\n"
                            + artifact.sanitized_text,
                        }
                    )
                elif artifact.sanitized_image_base64 is not None:
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{artifact.mime_type};base64,"
                                f"{artifact.sanitized_image_base64}"
                            },
                        }
                    )
                else:
                    raise ApiError(
                        503, "SANITIZED_ARTIFACT_REQUIRED", "Sanitized file unavailable"
                    )
            messages[-1]["content"] = content
        body = json.dumps(
            {"model": self._model, "messages": messages, "stream": True}
        ).encode("utf-8")
        req = urllib.request.Request(
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )

        def open_response():
            return urllib.request.urlopen(req, timeout=60)

        try:
            response = await asyncio.to_thread(open_response)
        except (urllib.error.URLError, TimeoutError):
            raise ApiError(502, "PROVIDER_ERROR", "LLM response could not be completed") from None

        try:
            while True:
                line = await asyncio.to_thread(response.readline)
                if not line:
                    break
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip()
                if payload == b"[DONE]":
                    break
                try:
                    frame = json.loads(payload)
                    content = frame["choices"][0]["delta"].get("content")
                    if content is not None:
                        yield ProviderDelta.model_validate({"text": content})
                except (ValueError, KeyError, TypeError, IndexError):
                    raise ApiError(
                        502, "PROVIDER_ERROR", "LLM response could not be completed"
                    ) from None
        except ApiError:
            raise
        except Exception:
            raise ApiError(502, "PROVIDER_ERROR", "LLM response could not be completed") from None
        finally:
            response.close()
