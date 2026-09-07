# `/nexus playable` — All-in-One Game Production

**Purpose:** Concept → playable, shippable game in one orchestrated run, composing the game cluster (Quest design · Glance UI/UX · Tick implementation · Dot assets) under a **vertical-slice-first** gate. The game-domain specialization of `apex`.

**Read when:** Running or designing the `playable` recipe (`/nexus playable "<game concept>"`).

---

## 1. What it is

`playable` produces a working game from a concept by routing the full game-production lifecycle through the specialist cluster, not a generic build chain. It is to games what `apex` is to general features — discovery → ship one-shot — but it:
- routes design to **Quest**, UI/UX to **Glance**, implementation to **Tick**, assets to **Dot** (never generic Builder for game systems),
- enforces the defining game-production discipline: **prove the core loop is fun in a vertical slice before producing breadth**,
- verifies against **game** acceptance criteria: core-loop fun (playtest), determinism where required, accessibility baseline, frame budget — not just "tests pass".

`<concept>` is the game idea (e.g. `"roguelike deckbuilder"`); `platform=` / `genre=` / `scope=slice|full` / `a11y=baseline|broad` pre-supply framing.

## 2. Phase contract

`CONCEPT → DESIGN → SLICE → PRODUCE → INTEGRATE → VERIFY → SHIP`

| Phase | Agents | Output |
|-------|--------|--------|
| `CONCEPT` | Quest[frame] (+Flux?/Magi? for divergence/arbitration) | Game charter: genre, platform/input, 2-4 pillars, scope, monetization, target player |
| `DESIGN` | Quest[gdd]+Quest[balance]+Quest[economy] → Glance[hud/menu/nav/a11y] ‖ Weave?[gameplay FSM] | Design package: GDD + balance/economy tables + UI/UX spec (wireframes, focus graph, a11y checklist) |
| `SLICE` | Forge[fullstack vertical slice] → Echo[playtest]/Plea? | Playable vertical slice of the **core loop** + **fun verdict** → vertical-slice gate (§3) |
| `PRODUCE` | ⟨ Tick[loop/ecs/state/physics/netcode/save] ‖ Dot[sprite/canvas assets] ⟩ | Production game architecture + asset set — parallel branches, hub-spoke ownership (Tick=code, Dot=assets; disjoint files) |
| `INTEGRATE` | Tick (wire Glance UI spec + Dot assets) +Builder?[non-game backend] +Flow?[UI motion] | Integrated build: systems + UI + assets connected |
| `VERIFY` | Radar[sim/determinism/system tests] + Echo[UX/playtest] + Glance[a11y/glanceability check] + Bolt?[frame budget] | Game-acceptance result; fix→reverify loop (§1 termination) |
| `SHIP` | Guardian[PR] → Launch?[release] | Playable build delivered + **Playable Report** (§5) |

Parallelism: `DESIGN` Glance depends on Quest's systems (sequential within phase); `PRODUCE` runs Tick ‖ Dot concurrently under disjoint file ownership (`_common/PARALLEL.md`). Hierarchical decomposition (Core Rule #9) if the build exceeds 6 concurrent specialists.

## 3. Termination bound & gates

**Loop ≤ 3 cycles (default N=3)** at two points, each with the canonical exit vocabulary (`ACCEPT`/`diminishing-returns (Δ<ε)`/`cap-reached`/`BLOCK`):
- **SLICE fun-loop**: iterate the vertical slice until the core loop meets the fun bar (Echo/playtest PASS) or `diminishing-returns` / `cap-reached`. On non-`ACCEPT` exit → report best-so-far slice + residual gap and **escalate before producing breadth** (never auto-produce on an unfun loop).
- **VERIFY fix-loop**: fix→reverify until game acceptance passes or `cap-reached`/`BLOCK`.

**Vertical-slice gate** (the recipe's signature): proceed `SLICE → PRODUCE` only when the core loop passes the fun bar.
- **AUTORUN**: proceed on Echo/playtest PASS; on FAIL, iterate ≤3 then escalate (do not silently build full production on an unfun core).
- **GUIDED/INTERACTIVE**: contract-level checkpoint; AUTORUN cannot skip the gate's existence, only auto-resolve it on PASS.

**Confirm / safety:**
- **Confirm uncovered scope or budget before launch** — `playable` spawns 8-22 agents (high cost). Resolve scope and budget authorization before the run starts; reuse approval of the same envelope (same tier as `apex`).
- **Ask First** — `SHIP` release/deploy, destructive data, 10+ file commits, any L4.

## 4. Resume

**Checkpoint-resume**: `playable` has ≥4 phases, so phase outputs persist at each boundary; an interrupted run resumes from the last checkpoint. `playable resume [<slug>]` restarts at the last completed phase (design package, slice, production branches, and verify results are each checkpointed).

## 5. Output report

`NEXUS_COMPLETE` with the base `## Nexus Execution Report` **plus a named `## Playable Report`**:
- **Concept & pillars** — genre, platform/input, the 2-4 design pillars
- **Design package** — core loop, balance/economy model summary, UI/UX (HUD + nav model + a11y tier)
- **Vertical-slice verdict** — fun-bar result + cycles spent + exit reason
- **Production** — Tick architecture (loop type, ECS/OOP, netcode, determinism status) + Dot asset inventory
- **Game acceptance** — core-loop fun (playtest) · determinism (if required) · accessibility baseline · frame budget — each PASS/FAIL with evidence
- **Residual gaps** — explicitly name uncovered surfaces (e.g. **audio**: no audio specialist in the current roster → manual/external; music/SFX is out of scope) and any deferred a11y items
- **Ship status** — build artifact, PR/release state

## 6. Failure Modes Prevented

- **Breadth before fun** — the vertical-slice gate forces a proven core loop before full production (the #1 game-production failure).
- **Frame-rate-coupled game** — `PRODUCE` routes to Tick, whose contract mandates fixed-timestep / sim-render separation; generic Builder would not.
- **Inaccessible UI** — Glance designs a11y in at `DESIGN`; VERIFY gates on the accessibility baseline.
- **Design re-decided at implementation time** — Quest's GDD/balance tables are authoritative; Tick implements, never re-tunes.
- **Asset/code merge conflict** — Tick ‖ Dot run under disjoint hub-spoke file ownership.
- **Scope creep** — pillars are the cut-line; features serving no pillar are dropped at DESIGN.
- **Silent un-fun ship** — a non-`ACCEPT` slice loop escalates rather than proceeding.

## 7. Scale & cost

8-22 agents × ≤3 cycles on the SLICE and VERIFY loops. Cost comparable to `apex` (high). Confirm before launch. For very large productions (full content build, multi-platform), this recipe designs and proves the slice + core systems; hand sustained content production to `enact` (run a Charter) or `rally` (parallel sessions).

## 8. Boundaries / vs neighbors

| vs | Difference |
|----|------------|
| `apex` | apex = **general** discovery→ship one-shot. `playable` = **game-specialized**: routes Quest/Glance/Tick/Dot, adds the vertical-slice-first gate and game acceptance (fun/determinism/a11y/frame-budget). Use apex for non-game features. |
| `feature` | feature = one feature build. `playable` = a whole game (design + UI/UX + systems + assets). |
| `GAME` task-type (`agent-chains.md`) | GAME variants (prototype/ui/balance/multiplayer/full) are **sub-chains**. `playable` is the orchestrating all-in-one that composes them with the slice gate, the fix-loop, and game acceptance. |
| `charter`→`enact` | charter = team-design document (stops at a doc). `playable` = executes a game build directly. For a long, multi-package game program, `charter`→`enact` may wrap `playable` as a package. |
| `clone` | clone = reproduce an *existing* game faithfully (differential parity). `playable` = build a *new* game from concept. |

Decision: "make/build a game from scratch, end to end" → `playable`. "design only (no code)" → `quest` (or `spec`). "just the UI" → `glance`. "just the engine systems" → `tick`. "copy an existing game" → `clone`.

## 9. Shared-protocol refs

- `reference/evaluator-loop-protocol.md` — the SLICE fun-loop and VERIFY fix-loop (Generator-Evaluator separation, single termination oracle); `playable` does not re-specify loop machinery.
- `_common/PARALLEL.md` — Tick ‖ Dot branch ownership, merge, rollback.
- Game cluster contracts: `quest/SKILL.md` (+ `reference/game-design-document.md`, `balance-and-economy.md`), `glance/SKILL.md` (+ `reference/hud-and-diegetic.md`, `game-accessibility.md`), `tick/SKILL.md` (+ `reference/game-loop-and-time.md`). Cite these for phase-internal discipline rather than re-deriving design/UX/engine rules here.
