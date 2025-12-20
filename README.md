# Slork

Slork is a lightweight text-adventure engine. Worlds are defined in YAML, parsed into a simple game engine with inventory, NPCs, exits, and flag-driven interactions. You can play it as a classic parser game or let a local LLM (via Ollama) act as a narrator/command mapper.

## Requirements
- Python 3.11+ recommended
- `pip install -r requirements.txt`
- Optional: [Ollama](https://ollama.com/) running locally if you want AI narration/command mapping

## Quick start
```bash
python run.py                          # play the bundled example world
python run.py --world assets/worlds/example.yaml

# Enable AI assistance (model must be available to Ollama)
python run.py --ai-model llama3        # optionally add --ollama-url http://localhost:11434
```

During play:
- `look`, `go north`, `take brass key`, `drop lint`, `examine gate`, `inventory`
- Interactions: `use brass key on gate`, `talk hermit`, `give lint to gnome`
- `ai` toggles AI narration on/off mid-session; `quit`/`exit` ends the game.

## Creating your own world
- Author YAML files that match `docs/schema/world.schema.json`; the example at `assets/worlds/example.yaml` is a good starting point.
- Key sections:
  - `world`: title, starting location, optional starting inventory/companions
  - `items`: all objects/NPCs with descriptions, aliases, and portability
  - `locations`: descriptions, items present, and exits (with optional `requires_flags`/`blocked_description`)
  - `interactions`: verb/item/target combos that set/clear flags, gate exits, consume items, or emit messages
- Use `--world path/to/your.yaml` to load a custom world.

## How AI mode works
- If `--ai-model` is supplied, Slork sends brief prompts and engine responses to Ollama.
- The AI maps player text to valid engine commands, executes them, and rewrites engine output with extra flavor.
- If Ollama fails or replies unexpectedly, the engine falls back to the non-AI output and you can toggle AI off with `ai`.

## Project layout
- `run.py` – entry point for local play
- `src/slork/engine.py` – deterministic game engine
- `src/slork/commands.py` – parser/aliases for player commands
- `src/slork/world.py` – world data models and loader
- `src/slork/ai_client.py` / `src/slork/ai_engine.py` – optional Ollama-backed narration
- `assets/worlds/example.yaml` – sample world
- `docs/schema/world.schema.json` – schema for world authoring
