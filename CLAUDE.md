# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running locally

Open `index.html` directly in a browser — no build step required. For a proper server (needed for some browser security contexts):

```bash
python3 server.py          # serves on http://127.0.0.1:5200
# or
npx serve -p 5200 .
```

The `.claude/launch.json` is configured for the Claude Code preview panel on port 5200.

## Architecture

The entire game is a single self-contained file: `index.html` with inline `<style>` and `<script>`. There is no build system, no dependencies, and no external files.

### Game loop

```
requestAnimationFrame(loop) → update(dt) + draw()
```

`dt` is capped at 50 ms and multiplied by `state.speed` (1×/2×/4×) before being passed to `update`. All time-dependent logic (movement, cooldowns, status timers, continuous damage) uses `dt` directly.

### State

All mutable game state lives in a single `state` object returned by `createState()`. Restarting or switching maps calls `createState()` again — no partial resets. Key fields: `towers`, `enemies`, `projectiles`, `particles`, `gold`, `lives`, `wave`, `waveActive`, `speed`, `selectedTower`, `hoveredTower`, `hoverCell`.

### Tower system

**Base towers** are defined in `TOWER_TYPES` (keyed by type string). Each entry has: `name`, `color`, `cost`, `dmg`, `range` (in cells), `rate` (shots/sec), `splash` (radius in cells), `burnDps`, `burnDur`, `slowMult`, `slowDur`, `desc`.

**Upgrade constants** are separate top-level objects. Each tower type supports upgrades applied via `t.upgrade` (a string flag on the tower object):

| Tower | Upgrade 1 | Upgrade 2 |
|---|---|---|
| Nuke | `'sungod'` (SUNGOD) | `'supernova'` (SUPERNOVA) |
| Tesla | `'deathray'` (DEATHRAY) | `'omegaray'` (OMEGARAY) |
| Cryo | `'permafrost'` (PERMAFROST) | `'absolutezero'` (ABSOLUTEZERO) |
| Sniper | `'railgun'` (RAILGUN) | — |
| Fire | `'inferno'` (INFERNO) | — |

Continuous-damage upgrades (`deathray`, `omegaray`, `railgun`, `inferno`, `absolutezero`, `permafrost`) bypass the cooldown system entirely — they run at the top of the tower loop with `continue`. Rate-based AoE upgrades (`sungod`, `supernova`) use the normal cooldown path.

### Update order (per frame)

1. Spawn enemies (timer-based)
2. Move enemies + apply burn/slow status
3. Tower firing (continuous upgrades first → rate-based upgrades → tesla → regular targeting → projectile creation)
4. Move projectiles + apply on-hit effects
5. Decay particles
6. Clean up dead/reached enemies, spent projectiles, expired particles
7. Check wave-complete condition

### Rendering

`draw()` calls sub-functions in painter's order: background → path → grid → towers → enemies → projectiles → particles → top bar → panel → range circle overlay → placement preview → game over screen.

The panel on the right (`PANEL_W = 240`) is drawn entirely in canvas — there is no HTML UI. Tower cards are `CARD_H = 68` px tall with `CARD_GAP = 3` px between them.

### Maps

Two hardcoded paths in the `PATHS` array (index 0 = Classic, index 1 = Winding). `setMap(idx)` rebuilds `ACTIVE_PATH`, `PATH_SET` (Set of `"col,row"` strings for O(1) placement checks), and `WAYPOINTS` (pixel-center coordinates).

### Adding a new tower type

1. Add an entry to `TOWER_TYPES`.
2. Handle its firing behavior in `update()` (splash projectile, single target, or continuous AoE).
3. Add a visual in `drawTowers()` — add a special-case block with `continue` for unique appearance, or let it fall through to the default barrel draw.
4. Add a mini-tower icon in `drawMiniTower()`.

### Adding a new upgrade

1. Define a top-level constant object with stats.
2. Add the upgrade check in `update()` — place it before the `t.cooldown` decrement line if continuous, or after `sungod`/`supernova` if rate-based.
3. Add the visual in `drawTowers()` after the existing upgrade blocks, with `continue`.
4. Add the click path in the click handler's `if (existing)` block.
5. Add hover text in `drawRangeCircle()`.
6. Update the panel callout box in `drawPanel()`.
