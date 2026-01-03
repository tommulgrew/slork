from typing import Literal
from .app import App
from .args import parse_main_args
from .engine import ActionResult
from .ai_client import AIChatAPIError
from .ai_engine import AIResponseFormatError
from .util import strip_quotes

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Create application
    app = App(args)

    # Initial location
    try:
        engine_response = app.engine.describe_current_location()
        image_path = app.get_image(engine_response.image_ref)
        if image_path:
            print(f"(Image: {image_path})")
        print(engine_response.message)
    except (AIChatAPIError, AIResponseFormatError) as exc:
        print(app.base_engine.describe_current_location().message)
        print(f"{exc}\n(Enter 'AI' to toggle AI off.)")

    # Main loop
    while True:
        try:
            try:
                player_cmd_str = input("> ").strip()
            except EOFError:
                break
            if not player_cmd_str:
                continue
            elif player_cmd_str.lower() in { "quit", "exit" }:
                break
            else:
                syscmd_result = app.handle_system_command(player_cmd_str)
                if syscmd_result == "state_updated":
                    player_cmd_str = "look"
                elif syscmd_result == "handled":
                    continue

            engine_response: ActionResult = app.engine.handle_raw_command(player_cmd_str)
            image_path = app.get_image(engine_response.image_ref)
            if image_path:
                print(f"(Image: {image_path})")
            print(engine_response.message)

        except (AIChatAPIError, AIResponseFormatError) as exc:
            print(f"{exc}\n(Enter 'AI' to toggle AI off.)")

if __name__ == "__main__":
    main()
