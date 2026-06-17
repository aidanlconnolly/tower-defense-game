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

All mutable game state lives in a single `state` object returned by `createState()`. Restarting or switching maps calls `createState()` again — no partial resets. Key fields: `towers`, `enemies`, `projectiles`, `particles`, `gold`, `lives`, `wave`, `waveActive`, `speed`, `paused`, `autoStart`, `selectedTower` (the tower *type* armed for placement), `selectedPlacedTower` (a placed tower the player tapped, for upgrade/sell), `hoveredTower`, `hoverCell`, `abilityCd` (per-ability cooldown timers), `screenFlash` (airstrike flash alpha). Best wave survived persists outside `state` in the `bestWave` module variable (`localStorage` key `td_best`).

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

`'beam'`/`'aoe'` bypass the cooldown system (handled at the top of the tower loop with `continue`); `'rate'` runs after the `t.cooldown` decrement. Adding/retuning a tier is one entry in the constant + `UPGRADE_TREE` — the firing loop, upgrade/sell click handling, and hover text are all generic. Towers track `invested` (base cost + tier upgrades only) so selling refunds 70%.

**Black Hole** is the premium base tower (`blackhole`, $15k) — fires like Tesla/God (zap-all-in-range on cooldown) but also `applySlow`s everything caught (gravity well), then upgrades via `quasar` → `singularity` (both `'aoe'` mode). Its base firing is special-cased alongside `tesla`/`god` in `update()`.

**Ascension — the infinite gold sink.** Every placed tower carries `ascend` (level count). `towerDmgMult(t)` = `1 + 0.30·ascend` multiplies *all* damage that tower deals (applied at every damage site / projectile creation in `update()`). `ascendCost(t)` = `max(800, invested·0.4)·1.6^ascend` — exponential, so even billions get consumed. Ascension spend is **sunk** (never added to `invested`), so it neither refunds on sell nor inflates the next ascension cost. `nextPurchase(t)` returns the next tier upgrade if one exists, else the next ascension level; `buyTowerUpgrade(t)` spends gold on it. Ascended towers draw a gold aura + a level badge (a second pass at the end of `drawTowers()`).

**Spendable abilities** (active gold sinks, panel buttons below the tower cards): `airstrike` (40% max-HP to all + screen flash), `freeze` (4 s hard slow on all), `repair` (+5 lives — the one genuinely scarce resource). `abilityButtons()` is the single source of truth for their rects (draw + input); `ABILITY_CD` sets cooldowns (ticked on game time in `update()`); `abilityCost(key)` scales with wave; `useAbility(key)` executes. Costs/cooldowns shown live with a cooldown-wipe overlay in `drawAbilities()`.

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

The right panel and top bar are pure canvas (no HTML UI). `topBarButtons()` and `abilityButtons()` are the single sources of truth for their hit regions — both the matching `draw*()` and `handleTap()` read them via `inRect()`, so rendered rects and click targets can't drift.

**Upgrade-by-tapping-the-tower:** tapping an unselected placed tower sets `state.selectedPlacedTower` (shows range circle + a "▲ TAP TOWER → …" prompt naming the next purchase). Tapping that *same* tower again calls `buyTowerUpgrade()` (next tier, then ascension levels) — the player never has to reach for a button to upgrade. `towerActions()`/`drawTowerActions()` now lay out **only** a Sell button (positioned below/above the tower).

### Adding a new tower type

1. Add an entry to `TOWER_TYPES`.
2. Handle its firing behavior in `update()` (splash projectile, single target, or continuous AoE). Remember to multiply damage by `towerDmgMult(t)` so ascension applies.
3. Add a visual in `drawTowers()` — add a special-case block with `continue` for unique appearance, or let it fall through to the default barrel draw.
4. Add a mini-tower icon in `drawMiniTower()`.
5. If it should be upgradeable, add a chain in `UPGRADE_TREE`.
6. Note the panel renders one card per `TOWER_TYPES` entry and the abilities block sits below them via `abilityButtons()` (which derives its Y from the tower count) — adding a tower auto-reflows both, but keep the total within the panel height (`TOP_H + ROWS*CELL`).

### Adding a new upgrade

1. Define a top-level constant with `mode` (`'beam'`/`'aoe'`/`'rate'`) + stats, register it in `UPGRADE_DEFS`, and append its key to the right `UPGRADE_TREE` chain. Firing, upgrade/sell clicks, hover text, and range circles are then handled generically — no `update()`/`handleTap()`/`drawRangeCircle()` changes needed.
2. Add a bespoke visual in `drawTowers()` (a `t.upgrade === '…'` block with `continue`) if you want a unique look.
