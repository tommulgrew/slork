import sys
from pathlib import Path

# Ensure src/ is on the path for local execution without installation.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from slork.cli import main


if __name__ == "__main__":
    main()
