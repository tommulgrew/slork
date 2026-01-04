from typing import Literal
from .app import App
from .args import parse_main_args
from .engine import ActionResult
from .ai_client import AIChatAPIError
from .ai_engine import AIResponseFormatError
from .util import strip_quotes

try:
    import readline
except ImportError:
    pass

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Create application
    app = App(args)

    # Initial location
    try:
        engine_response = app.engine.get_intro()
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

            result = app.handle_raw_command(player_cmd_str)
            image_path = app.get_image(result.image_ref)
            if image_path:
                print(f"(Image: {image_path})")
            print(result.message)

        except (AIChatAPIError, AIResponseFormatError) as exc:
            print(f"{exc}\n(Enter '/AI' to toggle AI off.)")

        except (RuntimeError, ValueError) as exc:
            print(exc)

if __name__ == "__main__":
    main()
