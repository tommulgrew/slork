from pathlib import Path
from box import Box
import yaml

def load_world(path: Path):
    world_yaml = path.read_text()
    parsed_world = yaml.safe_load(world_yaml)
    world = Box(parsed_world)
    return world
