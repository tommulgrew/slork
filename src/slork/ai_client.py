from dataclasses import dataclass, asdict, field
from dacite import from_dict
from urllib import request
from urllib.error import HTTPError, URLError
from typing import Any, Optional
import json
import socket

@dataclass
class OllamaToolFunction:
    index: int
    name: str
    arguments: dict[str, Any]

@dataclass
class OllamaToolCall:
    id: str
    function: OllamaToolFunction

@dataclass
class OllamaMessage:
    role: str       # system | user | assistant
    content: Optional[str] = None
    tool_calls: list[OllamaToolCall] = field(default_factory=list)

@dataclass
class OllamaNormalisedMessage:
    role: str
    content: str

@dataclass
class OllamaChatRequest:
    model: str
    messages: list[OllamaNormalisedMessage]
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

    def chat(self, messages: list[OllamaNormalisedMessage]) -> OllamaNormalisedMessage:
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

        # Decode response JSON
        print(f"AI RESPONSE: {body}")
        response_dict = json.loads(body)
        response_message: OllamaMessage = from_dict(OllamaChatResponse, response_dict).message

        # Normalise chat message response
        if response_message.content:
            return OllamaNormalisedMessage(
                role=response_message.role, 
                content=response_message.content
            )

        if response_message.tool_calls:
            return OllamaNormalisedMessage(
                role=response_message.role,
                content=json.dumps(response_message.tool_calls[0].function.arguments)
            )

        raise OllamaApiError("Ollama response contained no content or tool call")
