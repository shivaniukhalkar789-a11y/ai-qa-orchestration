"""Response providers: a fixed MOCK provider and a live OpenAI adapter.

Providers return raw text. They never validate it and never fall back to
each other: a live failure is reported as a ProviderError, not hidden by a
mock answer.
"""

import json
import os
from dataclasses import dataclass, field

from day3_lab.contract import openai_json_schema

LIVE_TIMEOUT_SECONDS = 30.0
LIVE_MAX_RETRIES = 2


class ProviderError(Exception):
    """A provider could not produce a response. `kind` names the failure."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass
class ProviderResult:
    raw_text: str
    model: str = None
    token_usage: dict = None  # only filled from real provider data
    extra: dict = field(default_factory=dict)


class MockProvider:
    """Returns fixed, reviewed response objects keyed by record_id.

    The prompt is accepted but ignored, so editing the prompt cannot change
    a mock response. Mock success only proves the workflow runs.
    """

    name = "mock"
    model = None

    def __init__(self, responses: dict):
        self._responses = responses

    def generate(self, item: dict, prompt_text: str) -> ProviderResult:
        record_id = item["record_id"]
        if record_id not in self._responses:
            raise ProviderError("missing_fixture", f"no mock fixture for {record_id}")
        value = self._responses[record_id]
        raw = value if isinstance(value, str) else json.dumps(value, indent=2)
        return ProviderResult(raw_text=raw)


class LiveProvider:
    """OpenAI Responses API adapter using strict structured outputs.

    Reads OPENAI_API_KEY and OPENAI_MODEL from the environment. A client can
    be injected so tests never touch the network.
    """

    name = "live"

    def __init__(self, model: str, client):
        self.model = model
        self._client = client

    @classmethod
    def from_env(cls, environ=None, client_factory=None):
        environ = os.environ if environ is None else environ
        missing = [n for n in ("OPENAI_API_KEY", "OPENAI_MODEL") if not environ.get(n)]
        if missing:
            raise ProviderError(
                "config_missing",
                "live mode unavailable: set " + " and ".join(missing) + " (no mock fallback)",
            )
        if client_factory is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ProviderError(
                    "sdk_missing",
                    'live mode unavailable: install with pip install -e ".[live]"',
                ) from exc
            client_factory = OpenAI
        client = client_factory(
            api_key=environ["OPENAI_API_KEY"],
            timeout=LIVE_TIMEOUT_SECONDS,
            max_retries=LIVE_MAX_RETRIES,
        )
        return cls(environ["OPENAI_MODEL"], client)

    def generate(self, item: dict, prompt_text: str) -> ProviderResult:
        case = item["case"]
        user_input = json.dumps(
            {"question": case["question"], "approved_context": case["approved_context"]},
            indent=2,
        )
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=prompt_text,
                input=user_input,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "service_desk_response",
                        "schema": openai_json_schema(),
                        "strict": True,
                    }
                },
            )
        except Exception as exc:  # classified, never swallowed
            name = type(exc).__name__
            kind = "timeout" if "Timeout" in name else "provider_error"
            raise ProviderError(kind, f"{name}: {exc}") from exc

        status = getattr(response, "status", None)
        if status not in (None, "completed"):
            details = getattr(response, "incomplete_details", None)
            raise ProviderError("incomplete", f"response status {status}: {details}")
        for output in getattr(response, "output", None) or []:
            if getattr(output, "type", None) != "message":
                continue
            for part in getattr(output, "content", None) or []:
                if getattr(part, "type", None) == "refusal":
                    raise ProviderError("refusal", str(getattr(part, "refusal", "")))
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text:
            raise ProviderError("empty_output", "provider returned no text output")
        return ProviderResult(
            raw_text=text, model=self.model, token_usage=_token_usage(response)
        )


def _token_usage(response):
    """Copy usage only if the provider actually reported it."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    result = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if isinstance(value, int):
            result[key] = value
    return result or None
