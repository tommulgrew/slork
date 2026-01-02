from pathlib import Path
from typing import Optional
import base64
from openai import OpenAI
from urllib.request import urlopen
from .ai_client import AIChatAPIError

class OpenAIImageGen:
    """
    OpenAI based image generator.
    """

    def __init__(self, client: OpenAI, *, model: Optional[str] = None, size: Optional[str] = None, quality: Optional[str] = None):
        self.client = client
        self.model = model or "gpt-image-1-mini"
        self.size = size
        self.quality = quality
    
    def generate_png(self, prompt: str, filename: Path):

        # Call service to generate image
        result = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            quality=self.quality,       # pyright: ignore
            size=self.size,             # pyright: ignore
        )

        # Retrieve result
        image_bytes: Optional[bytes] = None
        if result.data and result.data[0]:
            data = result.data[0]
            if data.b64_json:
                # Response contains image in base64 format
                image_bytes = base64.b64decode(data.b64_json)
            elif data.url:
                # Response contains a URL to fetch the image
                with urlopen(data.url) as response:
                    image_bytes = response.read()

        if not image_bytes:
            raise AIChatAPIError("Received AI generate-image response with no image.")

        # Write to file
        filename_str = str(filename)
        with open(filename_str, "wb") as f:
            f.write(image_bytes)
