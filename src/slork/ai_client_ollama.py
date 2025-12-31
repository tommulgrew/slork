from dataclasses import dataclass, asdict, field
from dacite import from_dict
from urllib import request
from urllib.error import HTTPError, URLError
from typing import Any, Optional
import json
import socket
from .ai_client import NormalisedAIChatMessage, AIChatAPIError

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
class OllamaChatRequest:
    model: str
    messages: list[NormalisedAIChatMessage]
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
    """
    A basic client for accessing the Ollama chat API to invoke LLM functions.
    """
    def __init__(self, settings: OllamaClientSettings):
        self.settings = settings

    def chat(self, messages: list[NormalisedAIChatMessage]) -> NormalisedAIChatMessage:
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
            raise AIChatAPIError("Ollama timed out (try a quicker model?)") from exc
        except HTTPError as exc:
            raise AIChatAPIError(f"Ollama HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise AIChatAPIError("Ollama is unreachable (is it running?)") from exc

        # Decode response JSON
        # print(f"AI RESPONSE: {body}")
        response_dict = json.loads(body)
        response_message: OllamaMessage = from_dict(OllamaChatResponse, response_dict).message

        # Normalise chat message response
        if response_message.content:
            return NormalisedAIChatMessage(
                role=response_message.role, 
                content=response_message.content
            )

        if response_message.tool_calls:
            return NormalisedAIChatMessage(
                role=response_message.role,
                content=json.dumps(response_message.tool_calls[0].function.arguments)
            )

        raise AIChatAPIError("Ollama response contained no content or tool call")

    def getImageGenerator(self):
        return None         # Not supported in Ollama client
