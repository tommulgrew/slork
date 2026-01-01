from dataclasses import dataclass
from pathlib import Path
from .engine import GameEngine
from .world import Location
from .ai_client import NormalisedAIChatMessage

@dataclass
class AIPrompts:
    create_location_prompt: str

class ImageService:
    """
    Uses AI image generation to create and return images for locations
    items, and NPCs
    """
    def __init__(self, image_generator, ai_client, game_engine: GameEngine, sub_folder_name: str):
        self.image_generator = image_generator
        self.ai_client = ai_client
        self.game_engine = game_engine
        self.folder = Path("assets/images") / Path(sub_folder_name)
        self.prompts: AIPrompts = create_ai_prompts()

        # Ensure images folder exists
        self.folder.mkdir(parents=True, exist_ok=True)

    def get_location_image(self, locId: str) -> Path:
        image_path = self.get_location_path(locId)
        if not image_path.exists():
            self.generate_location_image(locId, image_path)
        return image_path

    def get_location_path(self, locId: str) -> Path:
        return self.folder / Path(f"location_{locId}.png")

    def generate_location_image(self, locId: str, image_path: Path):
        location: Location = self.game_engine.world.locations[locId]
        prompt: str = self.get_image_gen_prompt(
            self.prompts.create_location_prompt,
            f"""\
LOCATION: {location.name}
DESCRIPTION: {location.description}
""")
        print(f"Generating {location.name} image...")
        self.image_generator.generate_png(prompt, image_path)
    
    def get_image_gen_prompt(self, system_prompt: str, description: str) -> str:
        
        # Build messages for chat api call
        ai_messages: list[NormalisedAIChatMessage] = [
            NormalisedAIChatMessage("system", system_prompt),
            NormalisedAIChatMessage("user", description)
        ]

        # Call AI chat endpoint
        ai_chat_response: NormalisedAIChatMessage = self.ai_client.chat(ai_messages)
        return ai_chat_response.content


def create_ai_prompts() -> AIPrompts:
    return AIPrompts(
        create_location_prompt=f"""\
You are an image generator prompt creator.
You create the prompts to generate supplementary images for a text adventure 
game, based on the text descriptions of locations.

Images should illustrate the content from the original text.

Images should NOT introduce any *new* content that might mislead the user into
thinking there are items that could be picked up or interacted with that are not
present in the text adventure.

The image must NOT include any characters (human or otherwise). Even characters
included in the original text must NOT be included in the image. The image 
should illustrate the LOCATION only.

Do NOT invoke tools, functions, or tool calls.
Output ONLY the prompt to send to the AI image creator.
"""            
    )