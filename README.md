# Slork

Slork is a experiment in wrapping a Large Language Model around a text adventure engine.

The LLM interprets players' input and translates them to the text adventure command syntax, allowing the player to interact with the game world using natural language. It also adds "flavor" to the text adventure's output, and can improvise dialog for non-player characters, or respond to general questions.

The underlying text adventure engine provides a stable game-state with persistent locations, items and characters.

```
**************************************************
Misty Trial
Slork v0.2 (c) Tom Mulgrew
Using AI model: gpt-oss:20b-cloud
**************************************************
You find yourself at a mist‑shrouded crossroad where two paths stand beneath old, leaning pines. A thin veil of fog clings to the mossy ground, giving the scene a hushed, almost otherworldly hush. Lenny the Leprechaun, his green cap tipped jaunty, hovers beside you, his pouch jingling softly with tiny coins. He gives you a mischievous grin and whispers, "The north wind leads to a snug overlook, while the east beckons with the promise of forgotten ruins. Where shall we go?" The northern trail curls into a narrow, canopy‑lined walk, promising concealment and quiet. To the east, rugged stones mark the remnants of old ruins, their ancient outlines only hinted by the fading carvings in the fading light.
> head towards the ruins
(GO EAST)
The stone gate clearing unfolds before you. A modest low wall, its stone weathered and worn, frames a sealed gate whose hinges groan softly under the weight of years. The air here is cooler, the scent of damp earth mingling with the faint aroma of something like old wood turned to stone. A small, hunched‑back gnome, a humble figure crowned with mossy hair, reclines upon a large, moss‑covered rock, his gaze drifting toward the interrupted eastern gate with a quiet, almost reverent calm. Lenny the Leprechaun tugs at his cap, chuckles at the gnome’s stoic stillness, and says, "Seems we’ve hit a quick stop, eh? The way back west leads back to the crossroads, but the gate north remains shut tight."
> Say "Greetings Mr Gnome!"
(TALK GNOME)
You lean forward and shout cheerfully, "Greetings, Mr. Gnome!" The gnome’s soft, moss‑lined beard quivers as he turns toward you, yawning slowly. With a grumble in his deep bass voice, he shrugs and says, "Don’t look at me, I ain’t opening this gate for anybody." Lenny the Leprechaun snorts, pointing his bright green finger at the low wall and the sealed gate to the north, while a single exit, westward, still leads back to the crossroads.
```

Slork uses Ollama for running local or cloud based LLMs.

gpt-oss:20b seems generally good enough - barring the occasional weird description (like "casually leaning against a stream"). Stronger LLMs might give you smarter NPC dialog, if you need Lenny the Leprechaun to help debug your Linux distribution or something, but otherwise you don't need a super powerful LLM as long as it is strong enough.

AI generated readme content follows:

---

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
