# YAML World Authoring Guide

This document explains how to create playable world definition files for the text adventure engine, using `saltwind_station.yaml` as a reference.

The engine is deliberately simple and explicit. Most problems are avoided by following a few clear rules.

---

## Overall Structure

A world file consists of these top-level sections:

```yaml
world:
ai_guidance:
flags:
items:
npcs:
locations:
interactions:
```

Only `world`, `items`, and `locations` are strictly required, but most worlds will use all of them.

---

## `world`

```yaml
world:
  title: "The Saltwind Station"
  start: beach
  initial_inventory: []
  initial_companions: []
```

* **title** – Displayed at game start
* **start** – Location ID where the player begins
* **initial_inventory** – Item IDs the player starts with
* **initial_companions** – NPC item IDs that start as companions

IDs here must match keys used elsewhere in the file.

---

## `ai_guidance` (optional)

AI guidance configures prompts used for AI narration and image generation.

```yaml
ai_guidance:
  text_generation: The tone should be quirky, non-serious and off-beat.
  image_generation: vibrant, warm tones, fantasy storybook style.
```

* **text_generation** - Extra text appended to AI narration prompts
* **image_generation** - Extra text appended to AI image prompts

These fields are only used when running with an AI backend.

---

## Items

Items define *everything* the player can interact with: objects, scenery, and NPCs.

```yaml
items:
  journal:
    name: Weathered Journal
    description: A leather-bound journal swollen with seawater.
    location_description: A weathered journal lies half-buried in the shingle.
    aliases: [journal, book, diary]
    portable: true
```

### Required fields

* **name** – Display name (used in output)
* **description** – Used by the `EXAMINE` command
* **location_description** – Optional text appended to the location description when the item is in its original location
* **aliases** – Optional extra words the player can type to refer to the item

> ⚠️ Important:
> The engine does **not** treat the item ID as an alias.
> If the player should be able to type `journal`, it *must* appear in `aliases`.

### Portable vs non-portable items

#### Portable items

* Must have `portable: true`
* Appear in the location’s **“You see:”** list
* Can be picked up automatically (no `take` interaction required)
* If `location_description` is omitted (or the item is not in its original location), the engine will add: `There is a [item] here.`

Examples:

* Journal
* Keys
* Fuel can
* Whistle

#### Non-portable items

* `portable: false` (or omitted)
* Do **not** appear in “You see:”
* If `location_description` is provided, it will be appended to the location description when the item is in its original location
* If `location_description` is omitted, the engine will append nothing (assumes the location description already mentions it)
* Can still be targets for interactions (`use key on door`)

Examples:

* Doors
* Generators
* Radios
* Large machinery

---

## NPCs

NPCs are implemented as **items with extra metadata**.
The NPC metadata does not include a description; use the item's
`location_description` for how they appear in a location.

### Item definition

```yaml
researcher:
  name: Elias the Researcher
  description: A tired man in a faded field jacket.
  location_description: Elias, a tired man in a faded field jacket, stands nearby.
  aliases: [elias, researcher]
```

### NPC metadata

```yaml
npcs:
  researcher:
    persona: Analytical, guarded, quietly regretful.
    sample_lines:
      - "We were meant to observe, not interfere."
    quest_hook: Knows more than he admits about the missing crew.
```

### Naming rule (important!)

Any `location_description` text **must include the item or NPC’s name or alias**,
so the player knows what noun to use:

✅ Good:

```
A weathered journal lies half-buried in the shingle.
```

❌ Bad:

```
A man in a faded field jacket stands nearby...
```

Otherwise the player won’t know what to type.

If no `location_description` is provided (or the NPC is not in its original location), the engine will append: `[npc] is here.`

---

## Locations

```yaml
locations:
  beach:
    name: Shingle Beach
    description: Waves roll in under a grey sky.
    items: [journal]
    exits:
      north:
        to: station_yard
        description: A gravel path leading up the hill.
```

### Fields

* **name** – Displayed as the location title
* **description** – Environmental text
* **items** – Portable items and NPCs present
* **exits** – Movement options

### Item placement rules

| Item type            | Where it goes          |
| -------------------- | ---------------------- |
| Portable items       | `items:` list          |
| NPCs                 | `items:` list          |
| Non-portable scenery | `location_description` or location `description` |

---

## Exits

```yaml
exits:
  up:
    to: lighthouse_top
    description: A spiral staircase inside the lighthouse.
    requires_flags: [lighthouse_open]
    blocked_description: The door is firmly shut.
```

* **to** – Target location ID
* **description** – Shown in the exits list
* **requires_flags** – Flags required to use the exit
* **blocked_description** – Message if blocked

---

## Flags

Flags are simple strings used to track world state.

```yaml
flags: []
```

They are:

* Set or cleared by interactions
* Checked by exits or interactions
* Global to the world

Companions are tracked via flags with the format `companion:<npc_id>`. These
flags are set for any NPCs listed in `world.initial_companions` and move with
the player. You can use `requires_flags` or `blocking_flags` in interactions
and exits to gate behavior based on the companion list.

Examples:

* `power_restored`
* `lighthouse_open`

---

## Interactions

Interactions define custom verb logic.

```yaml
- verb: use
  item: station_key
  target: lighthouse_door
  requires_flags: [power_restored]
  message: The key turns with a metallic groan.
  set_flags: [lighthouse_open]
```

### Common fields

* **verb** – Command verb (`use`, `open`, `close`, `talk`, `give`)
* **item** – Item being acted on
* **target** – Optional second item (`use X on Y`, `give X to Y`)
* **message** – Text shown when triggered

### Control fields

* **requires_flags** – Must be set
* **blocking_flags** – Must *not* be set
* **set_flags** – Flags to enable
* **clear_flags** – Flags to remove
* **consumes** – Removes the item after use
* **repeatable** – If false, the interaction can only be performed once

### Notes

* Interactions are used for `use`, `open`, `close`, `talk`, and `give`.
* `EXAMINE` does not use interactions; it always shows the item's description.
* Portable items don’t need explicit `take` interactions unless you want custom messaging.

---

## YAML Tips

* Use **standard ASCII quotes** (`'` and `"`)
* Avoid smart quotes or em dashes unless your parser explicitly allows UTF-8
* Keep IDs lowercase with underscores
* Treat IDs as internal — the player only sees names and aliases

---

## Images and non-portable items

When AI image generation is enabled, location images are generated from the
location description only (item `location_description` text is not included).
Non-portable items should be described directly in the location description if
they need to appear in the location image. To avoid conflicting visuals, Slork
does not generate separate item images for non-portable items.

---

## Design Philosophy

The engine favors:

* Explicit author intent
* Simple parsing
* Predictable player grammar
* Narrative over mechanical complexity

If something feels awkward to author, it’s usually a sign the world data needs to be clearer — not that the player needs to guess more.
