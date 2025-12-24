# YAML World Authoring Guide

This document explains how to create playable world definition files for the text adventure engine, using `saltwind_station.yaml` as a reference.

The engine is deliberately simple and explicit. Most problems are avoided by following a few clear rules.

---

## Overall Structure

A world file consists of these top-level sections:

```yaml
world:
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

## Items

Items define *everything* the player can interact with: objects, scenery, and NPCs.

```yaml
items:
  journal:
    name: Weathered Journal
    description: A leather-bound journal swollen with seawater.
    aliases: [journal, book, diary]
    portable: true
```

### Required fields

* **name** – Display name (used in output)
* **description** – Used by the `EXAMINE` command
* **aliases** – Words the player can type to refer to the item

> ⚠️ Important:
> The engine does **not** treat the item ID as an alias.
> If the player should be able to type `journal`, it *must* appear in `aliases`.

### Portable vs non-portable items

#### Portable items

* Must have `portable: true`
* Appear in the location’s **“You see:”** list
* Can be picked up automatically (no `get` interaction required)

Examples:

* Journal
* Keys
* Fuel can
* Whistle

#### Non-portable items

* `portable: false` (or omitted)
* Do **not** appear in “You see:”
* Should be described directly in the **location description**
* Can still be targets for interactions (`use key on door`)

Examples:

* Doors
* Generators
* Radios
* Large machinery

---

## NPCs

NPCs are implemented as **items with extra metadata**.

### Item definition

```yaml
researcher:
  name: Elias the Researcher
  description: A tired man in a faded field jacket.
  aliases: [elias, researcher]
```

### NPC metadata

```yaml
npcs:
  researcher:
    description: Elias, a man in a faded field jacket, stands nearby...
    persona: Analytical, guarded, quietly regretful.
    sample_lines:
      - "We were meant to observe, not interfere."
```

### Important distinction

| Field              | Purpose                                  |
| ------------------ | ---------------------------------------- |
| `item.description` | Used for `EXAMINE npc`                   |
| `npc.description`  | Appended to the **location description** |

### Naming rule (important!)

NPC descriptions **must include the NPC’s name or alias**, so the player knows what noun to use:

✅ Good:

```
Elias, a man in a faded field jacket, stands nearby...
```

❌ Bad:

```
A man in a faded field jacket stands nearby...
```

Otherwise the player won’t know what to type.

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
| Non-portable scenery | Location `description` |

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

* **verb** – Command verb (`use`, `talk`, `examine`)
* **item** – Item being acted on
* **target** – Optional second item (`use X on Y`)
* **message** – Text shown when triggered

### Control fields

* **requires_flags** – Must be set
* **blocking_flags** – Must *not* be set
* **set_flags** – Flags to enable
* **clear_flags** – Flags to remove
* **consumes** – Removes the item after use

### Notes

* `EXAMINE` usually doesn’t need a custom interaction unless special text is desired
* Portable items don’t need explicit `get` interactions unless you want custom messaging

---

## YAML Tips

* Use **standard ASCII quotes** (`'` and `"`)
* Avoid smart quotes or em dashes unless your parser explicitly allows UTF-8
* Keep IDs lowercase with underscores
* Treat IDs as internal — the player only sees names and aliases

---

## Design Philosophy

The engine favors:

* Explicit author intent
* Simple parsing
* Predictable player grammar
* Narrative over mechanical complexity

If something feels awkward to author, it’s usually a sign the world data needs to be clearer — not that the player needs to guess more.
