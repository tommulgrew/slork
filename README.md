# Slork

Slork is a text adventure engine with optional AI enhancements. You can play in the CLI or via a basic web app. When AI is enabled, Slork interprets natural language input into game commands and adds flavor to engine output, including NPC dialog. With the OpenAI backend, it can also generate images for locations, items, and NPCs.

The underlying engine stays deterministic, providing a stable game state with persistent locations, items, and characters.

With AI:
```
**************************************************
Misty Trial
Slork v0.3.0 (c) Tom Mulgrew
  AI backend: ollama
  AI model:   gpt-oss:20b-cloud
**************************************************
> Say "Greetings Mr Gnome!"
(TALK GNOME)
You lean forward and shout cheerfully, "Greetings, Mr. Gnome!" The gnome’s soft,
moss-lined beard quivers as he turns toward you, yawning slowly. With a grumble
in his deep bass voice, he shrugs and says, "Don’t look at me, I ain’t opening
this gate for anybody."
```

Without AI:
```
**************************************************
Misty Trial
Slork v0.3.0 (c) Tom Mulgrew
**************************************************
> talk to gnome
The gnome turns towards you lazily. "Don't look at me, I aint opening this gate
for anybody."
```

## Requirements
- Python 3.11+ recommended
- `pip install -e .`
- Optional: [Ollama](https://ollama.com/) running locally if you want AI narration/command mapping with a local model
- Optional: OpenAI API key if you want AI narration + image generation with OpenAI (`OPENAI_API_KEY`)

## Quick start (CLI)
```bash
python -m slork.cli                                  # play the bundled example world
python -m slork.cli --world assets/worlds/example.yaml

# Enable AI assistance (Ollama, default backend)
python -m slork.cli --ai-model llama3                # optionally add --ollama-url http://localhost:11434

# Enable AI assistance (OpenAI)
OPENAI_API_KEY=... python -m slork.cli \
  --ai-backend openai \
  --ai-model gpt-4o-mini
```

During play:
- `look`, `inventory`, `go north`, `take brass key`, `drop lint`, `examine gate`
- Interactions: `use brass key on gate`, `give lint to gnome`
- NPC dialog: `talk hermit`, `talk gnome`
- `ai` toggles AI on/off mid-session; `quit`/`exit` ends the game.

## Quick start (web)
```bash
python -m slork.webapp --world assets/worlds/example.yaml
```
The web app runs a Flask dev server (not production-ready). Browse to `http://localhost:5000/` to play, and the page shows the latest response plus an image if one is available.

## AI backends
Slork supports multiple AI backends:
- **Ollama** (default): runs local or cloud Ollama models via `--ai-model` and optional `--ollama-url`. Does not support image generation.
- **OpenAI**: requires `OPENAI_API_KEY` and `--ai-backend openai`. Supports both chat and image generation.

If `--ai-model` is not supplied, Slork runs without AI (no input interpretation or narrative enhancement).

## AI image generation (OpenAI only)
When using the OpenAI backend, Slork can generate images for locations, items, and NPCs. Images are generated on demand and saved under `assets/images/<world>/`.

Use the optional flags to control image generation:
```bash
--ai-image-model    # defaults to gpt-image-1-mini if not provided
--ai-image-size     # optional, passed through to OpenAI
--ai-image-quality  # optional, passed through to OpenAI
```

CLI prints the image path when an image is generated. The web app renders the latest image alongside the text.

## Creating your own world
- Author YAML files that match `docs/schema/world.schema.json`. The example at `assets/worlds/example.yaml` is a good starting point.
- World files can include AI guidance:
  - `ai_guidance.text_generation` influences narration tone.
  - `ai_guidance.image_generation` influences image style.
- Items (including NPCs) can include an optional `location_description` used to append presence text when they are in their original location.
- Exits, interactions, and dialog use `criteria` (requires/blocking inventory/flags/companions).
- Interactions use `effect` for state changes, and some text fields can be conditional via resolvable text entries.
- NPCs can define `dialog` (string, conditional text, or dialog tree, optionally as a list).
- Use `--world path/to/your.yaml` to load a custom world.

For full authoring details, see `docs/yaml_world_authoring.md`.

## Project layout
- `src/slork/cli.py` - CLI entry point
- `src/slork/webapp.py` - web app entry point
- `src/slork/engine.py` - deterministic game engine
- `src/slork/commands.py` - parser/aliases for player commands
- `src/slork/world.py` - world data models and loader
- `src/slork/ai_client.py` / `src/slork/ai_engine.py` - optional AI integration
- `src/slork/images.py` - image generation and caching
- `assets/worlds/example.yaml` - sample world
- `docs/schema/world.schema.json` - schema for world authoring
