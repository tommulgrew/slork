from dataclasses import dataclass, asdict
from dacite import from_dict
from urllib import request
from urllib.error import HTTPError, URLError
import json
import socket

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

class OllamaApiError(Exception):
    """Raised when the OllamaApi call fails/times out"""

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
        except socket.timeout as exc:
            raise OllamaApiError("Ollama timed out (try a quicker model?)") from exc
        except HTTPError as exc:
            raise OllamaApiError(f"Ollama HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise OllamaApiError("Ollama is unreachable (is it running?)") from exc

        response_dict=json.loads(body)
        return from_dict(OllamaChatResponse, response_dict).message        
