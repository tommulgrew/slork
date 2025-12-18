from dataclasses import dataclass, asdict
from dacite import from_dict
from urllib import request
from urllib.error import HTTPError, URLError
import json

@dataclass
class OllamaMessage:
    role: str       # system | user | assistant
    content: str

@dataclass
class OllamaChatRequest:
    model: str
    messages: list[OllamaMessage]
    stream: bool = False

@dataclass
class OllamaChatResponse:
    model: str
    created_at: str
    message: OllamaMessage
    done: bool

@dataclass
class OllamaClientSettings:
    model: str
    base_url: str

class OllamaClient:
    def __init__(self, settings: OllamaClientSettings):
        self.settings = settings

    def chat(self, messages: list[OllamaMessage]) -> OllamaMessage:
        chat_request = OllamaChatRequest(
            model=self.settings.model,
            messages=messages
        )
        chat_request_json=json.dumps(asdict(chat_request)).encode("utf-8")
        req = request.Request(
            url=f"{self.settings.base_url}/api/chat",
            data=chat_request_json,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except (URLError, HTTPError) as exc:  # noqa: PERF203
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        response_dict=json.loads(body)
        return from_dict(OllamaChatResponse, response_dict).message        
