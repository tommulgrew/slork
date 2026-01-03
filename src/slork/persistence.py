import json
from pathlib import Path
from dataclasses import asdict
from dacite import from_dict
from .engine import GameEngineState

class GameStatePersister:
    def __init__(self, world_id: str):
        self.world_id = world_id

    @property
    def saves_folder(self) -> Path:
        return get_world_folder_path("saves", self.world_id)

    def get_save_file_path(self, filename: str) -> Path:
        return get_world_file_path(self.saves_folder, filename, ".json")

    def save_game_state(self, state: GameEngineState, filename: str):
        save_file_path = self.get_save_file_path(filename)

        # Serialize game state
        state_json = json.dumps(asdict(state), indent=2)

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
        state = from_dict(GameEngineState, state_dict)

        # TO DO: Validate against world file?

        return state

def get_world_folder_path(subfolder: str, world_id: str) -> Path:
    path = Path("assets") / subfolder / world_id
    path.resolve()

    path.mkdir(parents=True, exist_ok=True)

    return path

def get_world_file_path(folder_path: Path, filename: str, ext: str) -> Path:
    file_path = (folder_path / filename).with_suffix(ext)
    file_path.resolve()

    if not file_path.is_relative_to(folder_path):
        raise RuntimeError("Invalid filename")

    return file_path
