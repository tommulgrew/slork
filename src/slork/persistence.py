import json
from pathlib import Path
from .engine import GameEngineState

class GameStatePersister:
    def __init__(self, world_base_folder: Path):
        self.saves_folder = get_world_sub_folder_path(world_base_folder, "saves")

    def get_save_file_path(self, filename: str) -> Path:
        return get_world_file_path(self.saves_folder, filename, ".json")

    def save_game_state(self, state: GameEngineState, filename: str):
        save_file_path = self.get_save_file_path(filename)

        # Serialize game state
        state_json = json.dumps(state_to_dict(state), indent=2)

        # Write to file
        print(f"(Saving to: {save_file_path})")
        save_file_path.write_text(state_json)

    def load_game_state(self, filename: str) -> GameEngineState:
        save_file_path = self.get_save_file_path(filename)
        if not save_file_path.exists():
            raise RuntimeError(f"Save '{filename}' does not exist.")
        
        # Read from file
        print(f"(Loading from: {save_file_path})")
        state_json = save_file_path.read_text()

        # Deserialize
        state_dict = json.loads(state_json)
        state = state_from_dict(state_dict)

        # TO DO: Validate against world file?

        return state

def get_world_sub_folder_path(world_base_folder: Path, sub_folder: str) -> Path:
    path = world_base_folder / sub_folder
    path.resolve()

    path.mkdir(parents=False, exist_ok=True)

    return path

def get_world_file_path(folder_path: Path, filename: str, ext: str) -> Path:
    file_path = (folder_path / filename).with_suffix(ext)
    file_path.resolve()

    if not file_path.is_relative_to(folder_path):
        raise RuntimeError("Invalid filename")

    return file_path

def state_to_dict(state: GameEngineState) -> dict:
    return {
        "location_id": state.location_id,
        "inventory": state.inventory,
        "companions": state.companions,
        "flags": list(state.flags),
        "location_items": state.location_items,
        "completed_interactions": list(state.completed_interactions)
    }

def state_from_dict(data: dict) -> GameEngineState:
    return GameEngineState(
        location_id=data["location_id"],
        inventory=data["inventory"],
        companions=data["companions"],
        flags=set(data["flags"]),
        location_items=data["location_items"],
        completed_interactions=set(data["completed_interactions"])
    )