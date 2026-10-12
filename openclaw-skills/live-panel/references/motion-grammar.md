# Motion grammar for a live panel

Learned from an architecture-diagram clip by @thedelost (https://x.com/thedelost/status/2105398038026195279 , quoted by @slashui: https://x.com/slashui/status/2105850132365443528 ). The clip is a web page that looks like a terminal window, screen-recorded for about 30 seconds. It has no camera moves, no intro, no step-by-step build-up, no interaction, no narration. Its idea: **a diagram is the monitoring panel of a running system.** The motion is system state.

## 1. The layout never changes

- One fixed canvas. Boxes, titles, legend and explanatory text never move, appear or disappear.
- Any frame you cut out is a complete, readable diagram. Frame 0 is as good as frame 600.
- Colour is a small code: four role colours plus grey/white. The legend maps colour to role.
- Boxes are drawn like text-mode boxes: solid top and bottom, segmented sides. All type is monospace.

## 2. Three tempos run at the same time

The panel feels alive because three layers overlap and agree with each other, not because any one effect is fancy.

**Fast (changes every frame or every fraction of a second)**
- Packets: on every wire of the main flow there is always a packet - a big dot plus a small dot following it (a trail). Several wires carry packets at once. Fan-out wires carry them out, merge wires carry them in. Different offsets and periods per wire so the pattern never looks synchronised.
- Spinners (`◐◓◑◒`) on units that are working, each with its own phase.
- A fast counter (e.g. forks, events) that ticks upward; it appears in two places (inside a box and in the status bar) and the two always match.
- A blinking cursor on the prompt line.

**Medium (a change every 1 to 3 seconds)**
- Log: a fixed number of rows (4); a new row is pushed every second or so. The newest row is bright and bold; older rows are grey. The role name keeps its role colour.
- Bars/gauges re-roll their value every few seconds. Above a threshold the bar is the "good" colour and the tag is one word; below it the bar changes colour, a dotted texture shows the missing part, the value turns bold and the tag flips to the other word. A legend line in the same box swaps which of its two options is highlighted.
- Worker units flip between `running` and `done`, each on its own period, then go back to running.

**Slow (a change every 3 to 5 seconds, accumulating)**
- A side rail lists the "on call" triggers (3 is a good number). One at a time, in a fixed order, a trigger lights up: `◇` becomes `◆`, the row gets a background and bold text, the dashed arrow from it to its target turns the role colour and a packet runs along it. It stays lit about 3 s, then about 1.5 s of silence, then the next one.
- While lit, the "last advice" lines are cleared and typed out character by character.
- Totals accumulate once per trigger: call count +1, tokens/cost grows.

## 3. Everything says the same thing

Check the panel as a story with one set of facts:
- The `p=0.87` in a log row is the value that was on the bar at that moment.
- The log row "error repeats - spawned, reading diff" appears when the `error repeats` trigger lights up; the status bar shows `[advising]` at the same time.
- A worker finishing produces its `done` state and a log row.

In this engine the log has no text of its own for these events: each state machine (gauge, trigger, lane, cycle) emits its own log lines with the values it has at that time. That is how consistency is guaranteed. Do not hand-write log lines for things that are on screen elsewhere.

## 4. No data? Say so.

A diagram with no live data is a simulation. Rules:
- Fixed facts (a figure from a report, a model name) are static text, with the source named somewhere readable (`credit` line, or in your post).
- Anything that moves because the animation moves (packet counts, `calls`, forks) is the animation's own state. Label it `(illustrative)` / `simulated` on screen.
- Never make up a measurement and let it look real. When recreating someone else's diagram, mark it as a recreation.

## 5. Timing recipe (starting values that work at 30 s, 30 fps)

| thing | value |
| --- | --- |
| packet period per wire | 1.5 - 3 s, 1-2 packets per wire at different offsets, trail 15 px |
| spinner step | 0.3 s |
| log | 1-1.5 new rows per second overall (sum of all emitters) |
| gauge re-roll | 3 - 5 s per gauge, different period for each |
| trigger | period 4.5 s, lit 3 s |
| typing speed | about 9-10 characters per second after a 0.35 s delay |
| worker cycle | 7 - 10 s, running for 60-75% of it |
| pre-roll | `canvas.preroll` seconds so packet counters do not start at zero |
| loop | durations need not divide the clip length; the clip is not meant to loop seamlessly unless you choose periods that do |

## 6. Determinism

Time is the only input. `state = f(t)`; "random" is `hash(seed, index)`. Never read the clock, never `Math.random()`, never CSS animation. That makes frames reproducible and lets a checker jump to any `t`.

## 7. The same grammar on a light infographic

For a soft, light-coloured diagram (white background, pastel boxes) keep every rule above and change the expression, not the principle. Worked example: `examples/agent-architecture/`.

- **Colours and structure are the original's.** Do not turn a pastel infographic into a dark terminal. Boxes keep their fill and border; "active" is a thicker border plus a soft glow, not a new fill.
- **One master timeline.** A single `cycle` machine (`seq`, 8 segments of 3.5 s = 28 s, loops) says what the system is doing: Step 1..5, then reflect, output, context. Everything lit on screen is derived from it, so all places tell the same story: Step 3 lit in the plan list -> tool "data analysis" and MCP "database" lit -> the arrows to them carry packets.
- **Three tempos, gentler.** Fast: small packets drift along every arrow; the core-loop arc carries two packets lapping every 1.2 s. Medium: the inner loop (Thinking -> Action -> Action Input) rotates every 1.2 s, only while a step is running. Slow: the plan steps and the matching tool/MCP rows advance every 3.5 s; the two memory loops (update memory, provide context) light once each per cycle, after the reflection.
- **Arrows that mean something** turn the accent colour, thicken and carry two packets only while the state says they are in use. Arrows that are just structure stay grey with a faint packet.
- **Do not add modules.** Re-animating someone's infographic means their modules, wording and colours; no extra captions or counters. Credit them on screen.
