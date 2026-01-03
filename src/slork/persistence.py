import json
from pathlib import Path
from dataclasses import asdict
from dacite import from_dict
from .engine import GameEngineState

class GameStatePersister:
    def __init__(self, subfolder: str):
        self.save_dir = Path("assets/saves") / subfolder
        self.save_dir.resolve()

        # Ensure save folder exists
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def get_save_file_path(self, filename: str) -> Path:

        # Get full file path and validate it
        save_file_path = (self.save_dir / filename).with_suffix(".json")
        save_file_path.resolve()

        if not save_file_path.is_relative_to(self.save_dir):
            raise RuntimeError("Invalid filename")

        return save_file_path

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