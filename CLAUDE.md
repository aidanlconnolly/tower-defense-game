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

All mutable game state lives in a single `state` object returned by `createState()`. Restarting or switching maps calls `createState()` again — no partial resets. Key fields: `towers`, `enemies`, `projectiles`, `particles`, `gold`, `lives`, `wave`, `waveActive`, `speed`, `paused`, `autoStart`, `selectedTower` (the tower *type* armed for placement), `selectedPlacedTower` (a placed tower the player tapped, for upgrade/sell), `hoveredTower`, `hoverCell`. Best wave survived persists outside `state` in the `bestWave` module variable (`localStorage` key `td_best`).

### Tower system

**Base towers** are defined in `TOWER_TYPES` (keyed by type string). Each entry has: `name`, `color`, `cost`, `dmg`, `range` (in cells), `rate` (shots/sec), `splash` (radius in cells), `burnDps`, `burnDur`, `slowMult`, `slowDur`, `desc`.

**Upgrades are table-driven.** Each upgrade is a top-level constant (e.g. `SUNGOD`, `DEATHRAY`) carrying a `mode` plus stats. Two lookup tables drive all upgrade logic:

- `UPGRADE_DEFS` — maps upgrade key (`'sungod'`, …) → its constant object.
- `UPGRADE_TREE` — maps base tower type → ordered list of upgrade keys (its tiers), e.g. `tesla: ['deathray','omegaray']`.

An applied upgrade is just the string `t.upgrade`. The `mode` field selects firing behaviour in `update()`:

| `mode` | Behaviour | Examples |
|---|---|---|
| `'beam'` | Continuous single-target (furthest enemy), `dps` | deathray, omegaray, railgun, godshot |
| `'aoe'` | Continuous all-in-range, `dps`; optional `slowMult`/`burn` | permafrost, absolutezero, inferno, godray, divinity, cannonade, broadside |
| `'rate'` | AoE on a cooldown, `dmg`+`rate` | sungod, supernova |

`'beam'`/`'aoe'` bypass the cooldown system (handled at the top of the tower loop with `continue`); `'rate'` runs after the `t.cooldown` decrement. Adding/retuning a tier is one entry in the constant + `UPGRADE_TREE` — the firing loop, upgrade/sell click handling, and hover text are all generic. Towers track `invested` (base cost + upgrades) so selling refunds 70%.

### Enemies

`spawnEnemy(kind)` builds enemies; `kind` is `'normal'`/`'fast'`/`'tank'` (stats from the `ENEMY_TYPES` table: `hpMul`, `speedMul`, `r`, `color`, `stroke`) or `'boss'` (special, 14× HP, every 5th wave). Per-wave base HP is `waveHp(wave)` (gentle `50 · 1.20^(wave-1)`); `pickEnemyKind()` weights the archetype mix by wave. Gold per kill is `ceil(hp/10)`.

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

The panel on the right (`PANEL_W = 240`) is drawn entirely in canvas — there is no HTML UI. Tower cards are `CARD_H = 60` px tall with `CARD_GAP = 2` px between them.

### Maps

Hardcoded paths in the `PATHS` array (Classic, Winding, Lake, Serpentine — see `MAP_NAMES`). `setMap(idx)` rebuilds `ACTIVE_PATH`, `PATH_SET` (Set of `"col,row"` strings for O(1) placement checks), `WAYPOINTS` (pixel-center coordinates), and `LAKE_SET` (water cells from `LAKES[idx]` — Warship-only placement).

### UI / input

The right panel and top bar are pure canvas (no HTML UI). `topBarButtons()` is the single source of truth for top-bar button hit regions (map, start, pause, auto, speed) — both `drawTopBar()` and `handleTap()` read it via `inRect()`, so rendered rects and click targets can't drift. Tapping a placed tower sets `state.selectedPlacedTower`, which renders its range circle plus an action panel (`towerActions()` lays out the upgrade + sell button rects, shared by `drawTowerActions()` and `handleTap()`).

### Adding a new tower type

1. Add an entry to `TOWER_TYPES`.
2. Handle its firing behavior in `update()` (splash projectile, single target, or continuous AoE).
3. Add a visual in `drawTowers()` — add a special-case block with `continue` for unique appearance, or let it fall through to the default barrel draw.
4. Add a mini-tower icon in `drawMiniTower()`.
5. If it should be upgradeable, add a chain in `UPGRADE_TREE`.

### Adding a new upgrade

1. Define a top-level constant with `mode` (`'beam'`/`'aoe'`/`'rate'`) + stats, register it in `UPGRADE_DEFS`, and append its key to the right `UPGRADE_TREE` chain. Firing, upgrade/sell clicks, hover text, and range circles are then handled generically — no `update()`/`handleTap()`/`drawRangeCircle()` changes needed.
2. Add a bespoke visual in `drawTowers()` (a `t.upgrade === '…'` block with `continue`) if you want a unique look.
3. Optionally update the panel "UPGRADE CHAINS" callout list in `drawPanel()`.
