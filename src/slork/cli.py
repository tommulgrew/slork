from .args import parse_main_args
from .world import load_world

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world = load_world(args.world)

    print()
    print("**************************************************")
    print("Slork v0.1 - " + world.world.title)
    print("**************************************************")

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
