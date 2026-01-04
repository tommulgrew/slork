from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

from slork.persistence import get_world_sub_folder_path
from .engine import ImageReference
from .world import World
from .ai_client import NormalisedAIChatMessage, AIChatClient, AIImageGen

@dataclass
class AIPrompts:
    create_location_prompt: str
    create_item_prompt: str
    create_npc_prompt: str

class ImageService:
    """
    Uses AI image generation to create and return images for locations,
    items, and NPCs
    """
    def __init__(self, image_generator: Optional[AIImageGen], ai_client: Optional[AIChatClient], world: World, world_base_folder: Path):
        self.image_generator = image_generator
        self.ai_client = ai_client
        self.world = world
        self.folder = get_world_sub_folder_path(world_base_folder, "images")
        self.img_gen_prompt_common: Optional[str] = world.ai_guidance.image_generation if world.ai_guidance else None
        self.prompts = create_ai_prompts(self.img_gen_prompt_common)

    def get_image(self, image_ref: ImageReference) -> Optional[Path]:
        if image_ref.type == "location":
            return self.get_location_image(image_ref.id)
        elif image_ref.type == "item":
            return self.get_item_image(image_ref.id)
        elif image_ref.type == "npc":
            return self.get_npc_image(image_ref.id)
        else:
            raise ValueError(f"Unknown image reference type: {image_ref.type}")

    def get_location_image(self, loc_id: str) -> Path:
        image_path = self.get_image_path("location", loc_id)
        if not image_path.exists():
            self.generate_location_image(loc_id, image_path)
        return image_path

    def get_image_path(self, image_type: Literal["location", "npc", "item"], id: str) -> Path:
        filename = Path(f"{image_type}_{id}").with_suffix(".png")
        return self.folder / filename

    def generate_location_image(self, loc_id: str, image_path: Path):
        if not self.image_generator or not self.ai_client:
            return

        location = self.world.locations[loc_id]
        description = f"""\
LOCATION: {location.name}
DESCRIPTION: {location.description}
"""
        if location.exits:
            description += f"EXITS: {', '.join([f'{dir} - {exit.description}' for dir, exit in location.exits.items()])}"

        prompt = self.get_image_gen_prompt(
            self.prompts.create_location_prompt,
            description
        )
        print(f"(Generating '{location.name}' image...)")
        self.image_generator.generate_png(prompt, image_path)
    
    def get_image_gen_prompt(self, system_prompt: str, description: str) -> str:
        assert(self.ai_client is not None)
        
        # Build messages for chat api call
        ai_messages: list[NormalisedAIChatMessage] = [
            NormalisedAIChatMessage("system", system_prompt),
            NormalisedAIChatMessage("user", description)
        ]

        # Call AI chat endpoint
        ai_chat_response = self.ai_client.chat(ai_messages)
        image_gen_prompt = ai_chat_response.content
        if self.img_gen_prompt_common:
            image_gen_prompt += f". {self.img_gen_prompt_common}"
        return image_gen_prompt

    def get_npc_image(self, npc_id: str) -> Path:
        image_path = self.get_image_path("npc", npc_id)
        if not image_path.exists():
            self.generate_npc_image(npc_id, image_path)
        return image_path

    def generate_npc_image(self, npc_id: str, image_path: Path):
        if not self.image_generator or not self.ai_client:
            return

        item = self.world.items[npc_id]
        npc = self.world.npcs[npc_id]
        prompt = self.get_image_gen_prompt(
            self.prompts.create_npc_prompt,
            f"""\
CHARACTER: {item.name}
DESCRIPTION: {item.description}
PERSONA: {npc.persona}
""")
        print(f"(Generating '{item.name}' image...)")
        self.image_generator.generate_png(prompt, image_path)        

    def get_item_image(self, item_id: str) -> Path:
        image_path = self.get_image_path("item", item_id)
        if not image_path.exists():
            self.generate_item_image(item_id, image_path)
        return image_path

    def generate_item_image(self, item_id: str, image_path: Path) -> Optional[Path]:
        if not self.image_generator or not self.ai_client:
            return

        item = self.world.items[item_id]

        # Non-portable items are included in the location description, and 
        # generally shown in the location image. Therefore we don't generate a 
        # second image specifically for the item to avoid inconsistencies.
        if not item.portable:
            return None

        prompt = self.get_image_gen_prompt(
            self.prompts.create_item_prompt,
            f"""\
ITEM: {item.name}
DESCRIPTION: {item.description}
""")
        print(f"(Generating '{item.name}' image...)")
        self.image_generator.generate_png(prompt, image_path)
        return image_path

def create_ai_prompts(prompt_common: Optional[str]) -> AIPrompts:

    prompt_common_guidance = f"""
The following common text will be appended to ALL image prompts:
'{prompt_common}'
Do NOT include this text - it will automatically be appended to your output.
Avoid any terms that would conflict or override terms in the common text.
""" if prompt_common else ""

    return AIPrompts(
        create_location_prompt=f"""\
You are an image generator prompt creator.
You create the prompts to generate supplementary images for a text adventure 
game, based on the text descriptions of locations.
{prompt_common_guidance}
Images should illustrate the content from the original text.

Images should NOT introduce any *new* content that might mislead the user into
thinking there are items that could be picked up or interacted with that are not
present in the text adventure.

The image must NOT include any characters (human or otherwise). Even characters
included in the original text must NOT be included in the image. The image 
should illustrate the LOCATION only.

Do NOT invoke tools, functions, or tool calls.
Output ONLY the prompt to send to the AI image creator.
""",
        create_item_prompt=f"""\
You are an image generator prompt creator.
You create the prompts to generate supplementary images for a text adventure 
game, based on the text descriptions of items (things the player can pick up 
and/or interact with).
{prompt_common_guidance}
Images should illustrate the content from the original text.

Do NOT invoke tools, functions, or tool calls.
Output ONLY the prompt to send to the AI image creator.
""",
        create_npc_prompt=f"""\
You are an image generator prompt creator.
You create the prompts to generate supplementary images for a text adventure 
game, based on the text descriptions of characters (humans, animals, etc).
{prompt_common_guidance}
Images should illustrate the content from the original text.

Do NOT invoke tools, functions, or tool calls.
Output ONLY the prompt to send to the AI image creator.
"""
    )