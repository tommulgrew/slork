import argparse
from pathlib import Path

def parse_main_args():
    parser = argparse.ArgumentParser(description="Slork - Text adventure")
    parser.add_argument(
        "--world",
        type=Path,
        default=Path("assets/worlds/example.yaml"),
        help="Path to a world YAML file"
    )
    parser.add_argument(
        "--ai-model",
        type=str,
        required=False,
        help="Ollama model name"
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama base URL.",
    )
    parser.add_argument(
        "--ai-backend",
        type=str,
        default="ollama",
        choices=["ollama", "openai"]
    )
    return parser.parse_args()

