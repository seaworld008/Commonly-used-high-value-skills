# Config schema

One JSON object. All coordinates are canvas pixels (default 1200x1500, y grows downward). Colour names refer to `theme.colors`. Text is monospace; Latin glyphs are 0.6 em wide, CJK glyphs two cells.

## Top level

| key | meaning |
| --- | --- |
| `meta` | `{title, lang}` page title and language |
| `canvas` | `{preset:"4:5"|"3:4"|"1:1", width, height, duration, fps, preroll}` (explicit width/height win over the preset); `preroll` (s) is added to packet phases so delivery counters start above zero |
| `theme` | `{preset:"terminal-dark"|"light-pastel", font, fontSize, lineHeight, boxMode:"segmented"|"solid", radius, borderWidth, wireWidth, packetSize, glow, colors:{name:"#rrggbb"}}`. A preset supplies every field; your values override it, `colors` are merged name by name. Colour names used by the engine: `bg bar line dim fg wh` (+ `line2` log frame, `dots` bar track); add any others |
| `clock` | `{start:"HH:MM:SS", rate}`: log time at t=0 and how many log-seconds pass per second |
| `titlebar` | `{text, height?, size?}` terminal title bar with three dots |
| `credit` | text element for the source/credit line: `{text, y, size?, c?}` (default 12 px, centred, dim) |
| `machines` | named state machines, see below |
| `elements` | drawn in order (later = on top) |

## Elements

- `text` `{x, y, w?, align, runs | t | text, size?, lh?, c?, b?, ls?, font?, inside?}`; `y` is the vertical centre of the line. `inside:true` = intentionally drawn on top of a box (icons).
- `box` `{x, y, w, h, color (border), fill?, radius?, border? (px), dash?, container?, pad:[top,left,right?], align, sides:"solid"?, lines:[...], when?, then?:{fill,color,border,glow}}`. Lines flow at `lineHeight`. `container:true` marks a box that holds other boxes (skipped by the overlap check). `when/then` restyle the whole box while a condition holds (`glow` = colour name).
- `path` `{points:[[x,y],...], color, width?, r? (corner radius), dash?, arrow?:false, head?, opacity?, when?, then?:{color,width,opacity}, flow?:{period, offsets, color, tail, when}}` SVG polyline with arrow head; `flow` adds packets along it.
- `line` `{from:[x,y], to:[x,y], dash?, color?, width?}` axis-aligned wire.
- `glyph` `{x, y, ch, c, size}` e.g. an arrow head.
- `rule` `{x, y, w}` double rule.
- `flow` `{path:[[x,y],...], period, offsets:[...], color, gap?:[y0,y1], tail?, when?}` packets looping along a polyline. Delivery count of all flows is `{packets}`.
- `tarrow` `{machine, i, from:[x,y], to:[x,y]}` dashed arrow for trigger `i` of a `triggers` machine; coloured and carrying a packet while that trigger is lit.
- `log` `{x, y, w, rows, padTop, padBottom, padLeft, title, titleX, titleW, cols:[{key:"time|who|m|g", x}]}`.

### Lines inside a box

A line is a string, or an object:
`{runs | t, c, b, align, indent, size, h, items, when, then, trigger}`
- `runs`: list of strings or run objects `{t | v | sw | cursor, c, b, size, when, then}`. `t` is text (may contain `{var}`), `v` a variable name, `sw` a colour swatch, `cursor` a blinking block. A run `v` that returns a coloured value uses its colour unless `c` is set.
- `items`: flex row `[{w?, grow?, ml?, align?, runs | bar}]`. `bar` is `{w, h, gauge: id}` (bound to a gauge machine) or `{w, h, segments:[{from,to,c}], mark?}` (fractions 0-1).
- `when` / `then`: condition `{var, eq|ne|in:[...]}` (a list of conditions = AND) and override `{c, b, bg}`. On a line the override applies to the whole row (e.g. highlight background); on a run it changes colour/weight.
- `trigger: [machineId, index]`: shortcut for a side-rail row bound to a triggers machine (`◇`/`◆` label, highlight).

## Machines (all pure functions of t)

| type | fields | variables |
| --- | --- | --- |
| `counter` | `start, rate, format:"comma"?, prefix?, suffix?` | `id` |
| `cycle` | `values:[string \| {t,m,g,...}], period, t0, order?, log?:{who,c}` | `id`, `id.i` (index), `id.<field>` |
| `gauge` | `values:[numbers], period, t0, seed, threshold, decimals?, high:{label,dest}, low:{label,dest}, log?:{who,c,msgs:[...],tail:"p={value} {label}"}` | `id`, `id.num`, `id.low` ("1"), `id.label`, `id.dest` |
| `any_low` | `of:[gaugeIds]` | `id` = "low" / "high" |
| `lane` | `period, run, off, busy, done:[...], phase?, spin?, log?:{who,c,msgs:[[text,tag]]}` | `id` (spinner + text, coloured), `id.state` |
| `triggers` | `period, on, t0, items:[{name, adv:[l1,l2], to?}], color, callsStart?, tokens?:{start,step,unit}, cps?, onText, offText, log?:{who,c,start:{m,g},end:{m,g}}` | `id.active` (index or -1), `id.label<i>`, `id.adv0`, `id.adv1` (typed), `id.calls`, `id.tokens`, `id.status`, `id.<item field>` |

Built-in variables: `{packets}` (deliveries so far), `{clock}`. Log templates may use item/gauge fields, e.g. `{name}`, `{value}`, `{label}`, `{dest}`.

## Replay hook

`window.seek(t)` draws the frame at second `t`. `window.__ready` becomes true when the config is loaded and fonts are ready; `window.__check()` returns a list of layout problems (used by `check_frames.py`). `?manual` in the URL disables the live loop.
