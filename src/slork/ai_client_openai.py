from dataclasses import dataclass
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
from .ai_client import NormalisedAIChatMessage, AIChatAPIError

@dataclass
class OpenAIClientSettings:
    model: str
    api_key: str

class OpenAIClient:
    """
    A basic client for accessing the OpenAI chat API to invoke LLM functions.
    """

    def __init__(self, settings: OpenAIClientSettings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.api_key)

    def chat(self, messages: list[NormalisedAIChatMessage]) -> NormalisedAIChatMessage:
        response = self.client.chat.completions.create(
            model=self.settings.model,
            messages=[ makeChatCompletionMessage(m) for m in messages ]
        )

        msg = response.choices[0].message
        if not msg.content:
            raise AIChatAPIError("Received AI chat response message with no content.")

        return NormalisedAIChatMessage(role=msg.role, content=msg.content)


def makeChatCompletionMessage(m: NormalisedAIChatMessage) -> ChatCompletionMessageParam:
    assert(m.role in ["system", "user", "assistant"])
    if m.role == "system":
        return ChatCompletionSystemMessageParam(
            role="system", 
            content=m.content)
    elif m.role == "user":
        return ChatCompletionUserMessageParam(
            role="user",
            content=m.content
        )
    elif m.role == "assistant":
        return ChatCompletionAssistantMessageParam(
            role="assistant",
            content=m.content
        )

    raise AIChatAPIError(f"Unknown role '{m.role}' in normalised AI chat message.")