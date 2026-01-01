from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal
from .engine import GameEngine
from .world import Location
from .ai_client import NormalisedAIChatMessage

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
    def __init__(self, image_generator, ai_client, game_engine: GameEngine, sub_folder_name: str):
        self.image_generator = image_generator
        self.ai_client = ai_client
        self.game_engine = game_engine
        self.folder = Path("assets/images") / Path(sub_folder_name)
        self.img_gen_prompt_common: Optional[str] = game_engine.world.ai_guidance.image_generation if game_engine.world.ai_guidance else None
        self.prompts = create_ai_prompts(self.img_gen_prompt_common)

        # Ensure images folder exists
        self.folder.mkdir(parents=True, exist_ok=True)

    def get_image(self) -> Optional[Path]:
        cmd = self.game_engine.last_command
        result = self.game_engine.last_result

        if cmd.error or result.status.value != "ok":
            return None
        
        if cmd.verb == "look" or cmd.verb == "go":
            return self.get_location_image(self.game_engine.location_id)

        if cmd.verb == "examine":
            assert(cmd.main_noun)
            world = self.game_engine.world

            # Resolve the item to get the item_id
            resolved_item = self.game_engine.resolve_item(cmd.main_noun, include_location=True, include_inventory=True)
            assert(not resolved_item.error)     # Should always succeed if the game engine command succeeded
            assert(resolved_item.item_id)

            if cmd.main_noun in world.npcs:
                return self.get_npc_image(resolved_item.item_id)
            else:
                return self.get_item_image(resolved_item.item_id)

    def get_location_image(self, loc_id: str) -> Path:
        image_path = self.get_image_path("location", loc_id)
        if not image_path.exists():
            self.generate_location_image(loc_id, image_path)
        return image_path

    def get_image_path(self, image_type: Literal["location", "npc", "item"], id: str) -> Path:
        filename = Path(f"{image_type}_{id}").with_suffix(".png")
        return self.folder / filename

    def generate_location_image(self, loc_id: str, image_path: Path):
        location = self.game_engine.world.locations[loc_id]
        prompt = self.get_image_gen_prompt(
            self.prompts.create_location_prompt,
            f"""\
LOCATION: {location.name}
DESCRIPTION: {location.description}
""")
        print(f"(Generating '{location.name}' image...)")
        self.image_generator.generate_png(prompt, image_path)
    
    def get_image_gen_prompt(self, system_prompt: str, description: str) -> str:
        
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
        world = self.game_engine.world
        item = world.items[npc_id]
        npc = world.npcs[npc_id]
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
        item = self.game_engine.world.items[item_id]

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