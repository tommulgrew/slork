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
        help="AI model name"
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
    parser.add_argument(
        "--ai-image-model",
        type=str,
        required=False,
        help="AI image generation tool model name"
    )
    parser.add_argument(
        "--ai-image-size",
        type=str,
        required=False,
        help="Size parameter to pass to the image generator. E.g. '512x512'. Valid values depend on the generator used."
    )
    parser.add_argument(
        "--ai-image-quality",
        type=str,
        required=False,
        help="Quality parameter to pass to the image generator. E.g. 'low'. Valid values depend on the generator used."
    )
    parser.add_argument(
        "--dev",
        type=bool,
        default=False,
        help="Enable developer mode (cheat) commands"
    )
    return parser.parse_args()

