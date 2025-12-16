from .args import parse_main_args
from .world import load_world
from . import engine

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world = load_world(args.world)

    # Initial state
    state = engine.init_state(world)

    print()
    print("**************************************************")
    print("Slork v0.1 - " + world.world.title)
    print("**************************************************")

    print(engine.describe_current_location(state))

    # Main loop
    while True:
        try:
            playerCmd = input("> ").strip()
        except EOFError:
            break
        if not playerCmd:
            continue
        if playerCmd.lower() in { "quit", "exit" }:
            break

        print("Game not implemented yet :)")

if __name__ == "__main__":
    main()
