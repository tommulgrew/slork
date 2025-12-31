from typing import Literal, cast, Optional
import base64
from openai import OpenAI
from .ai_client import AIChatAPIError

class OpenAIImageGen:
    """
    OpenAI based image generator.
    """

    def __init__(self, client: OpenAI, *, model: Optional[str] = None, size: Optional[str] = None):
        self.client = client
        self.model = model or "gpt-image-1"
    
    def generatePng(self, prompt: str, filename: str):

        # Call service to generate image
        result = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size="auto"
        )

        # Result is base64 encoded png
        # Extract bytes
        if not result.data or not result.data[0] or not result.data[0].b64_json:
            raise AIChatAPIError("Received AI generate-image response with no image.")
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # Write to file
        with open(filename, "wb") as f:
            f.write(image_bytes)
