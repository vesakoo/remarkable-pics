---
name: remarkable-native
description: Use when creating or converting anything into native, editable reMarkable (Paper Pro) notebooks or .rm/.rmdoc files made of pen strokes - drawings from a verbal description ("draw a fox", "a smiling face", "a tree"), SVG or image conversion, icon sheets, stroke-font labels, pushing notebooks to the tablet, or learning new facts about the .rm v6 format from device examples.
---

# reMarkable native notebooks (rmdraw)

This project (`/Users/vesakankkunen/remarkable-pics`) writes notebooks for the user's
**reMarkable Paper Pro** that consist only of real pen strokes in the v6 `.rm` format.

**"Native" means:** every line is a stroke the user could have drawn. They can erase,
lasso, copy, move and scale it on the tablet. **No PDF, no embedded image, no template
background, no typed-text block.** If an approach would put a picture or PDF layer on
the page, it is wrong even if it "works".

Tooling: Python package `rmdraw/` plus the `rmdraw` CLI. Always use the project venv:
`.venv/bin/rmdraw ...` and `.venv/bin/python` / `.venv/bin/pytest`. Outputs go in
`out/` (git-ignored).

## Quick recipes

**Drawing from a description** ("a fox", "a house with a tree"):
1. Write a shapes JSON file, e.g. `out/fox.json` (format below).
2. `.venv/bin/rmdraw build out/fox.json -o out/fox.rmdoc`
3. `.venv/bin/rmdraw preview out/fox.rmdoc -o out/fox.svg` (add `--page N` for page N, from 1)
4. Render a PNG and **look at it** (see Verify). Fix the JSON and repeat until it reads well.
5. Getting it onto the tablet (only when the user wants it there):
   - **Default, works for everyone:** give the user `out/fox.rmdoc` to drag into the
     reMarkable desktop app, which syncs it to the tablet.
   - **Optional, needs SSH (developer mode):** `.venv/bin/rmdraw push out/fox.rmdoc --thumbs out/fox-thumbs`.
     This user has SSH. See "The device".

**SVG file:**
`.venv/bin/rmdraw svg art.svg -o out/art.rmdoc [--box x,y,w,h] [--fill shader|marker|hatch|none] [--name "Title"] [--budget N]`.
The whole SVG is one object with a 150-stroke budget. `--budget N` raises it and prints a warning when N > 150.
The default box is the page minus 10 mm margins. The SVG is scaled to fit and centred.
Inside a shapes JSON, use an `svg` item to place SVGs next to other shapes.

**Raster images (PNG/JPG/photos): not supported yet.** Planned approach: vectorise
first (`potrace` for black and white, `autotrace` or a colour quantise + per-colour
potrace for colour; neither tool is installed yet), then take the svg route. Never
embed the raster.

**Icon sheets / many items:** see `examples/aws_icons.py` (grid layout from
`rmdraw.layout.grid_layout`, an SVG per cell, a stroke-font title under each icon).

**Inspect a page:** `.venv/bin/rmdraw dump page.rm` prints one line per stroke
(tool, colour, rgba, thickness scale, point count, bbox in device units).

## The shapes JSON format

```json
{"name": "Notebook title", "pages": [[item, item, ...], [page 2 items ...]]}
```

Coordinates are **mm, origin at the page's top-left, y down.** The library converts to
device units. Item types:

| type | fields | notes |
|---|---|---|
| `polyline` | `points: [[x,y],...]`, `closed?` | ≥ 2 points; 2 points is a straight line |
| `circle` | `cx, cy, r` | |
| `ellipse` | `cx, cy, rx, ry, rotation_deg?` | rotation is clockwise on screen |
| `rect` | `x, y, w, h, rx?` | `rx` = corner radius |
| `arc` | `cx, cy, r, start_deg, end_deg` | **clockwise from 3 o'clock** (y is down): 90 = 6 o'clock, 270 = 12 o'clock; needs start < end ≤ start + 360. A smile is 25 → 155 |
| `bezier` | `points: [p0, c1, c2, p3, c, c, p, ...]`, `closed?` | cubic chain, 1 + 3k points |
| `text` | `text, x, y, height, align?, max_width?` | single-stroke Hershey font. `x` is the centre (`align: "center"`, default) or the left edge (`"left"`). `y` is the **cap top**; `height` is the cap height. `max_width` wraps to two lines, then shrinks |
| `svg` | `path, box: [x,y,w,h]` | path relative to the JSON file; `fill: {method?: shader\|marker\|hatch\|none, spacing_mm?}` |

Common optional fields: `pen` (default `fineliner`), `color` (default `black`),
`width_mm` (default 0.4), `fill: {color, method?, spacing_mm?}`. `fill.color` is a
palette name or `"#rrggbb"`; `method` defaults to `shader`. Only closed shapes take a
fill (circle, ellipse, rect, or polyline/bezier with `closed: true`). Curves are
flattened to 0.15 mm.

Errors name the item, e.g. `pages[0][3] (circle): field 'r' must be > 0`. Unknown
types, fields, pens and colours are rejected, and so is any point off the page.

**Paint order = list order.** A filled item **hides** everything listed before it
where they overlap (fills and lines are clipped). So list the background first and the
details last. A `white` fill draws nothing, but it still hides what lies below: that's
how to cut a gap (e.g. the white of an eye) into a coloured area.

## Composing a drawing from a description

**Page:** 179.7 × 239.6 mm (portrait). **Safe area:** keep content inside x 10–170,
y 10–230 mm. The centre is (90, 120). A single subject reads best at about 100–140 mm
wide, a bit above the centre, with an optional caption below.

**Pen colours** (`color`, the fixed palette; pens ignore anything else):
`black gray white blue red green yellow cyan magenta`. Highlighter colours:
`hl_yellow hl_blue hl_pink hl_orange hl_green hl_gray` (use them with `pen: "highlighter"`).
`pink` exists too, but it's a highlighter enum and untested on pens. **[device]** for the
first nine and the six highlighter colours.

**Fill colours** (`fill.color`): any `"#rrggbb"` (the shader honours exact RGB, so
brown, orange, skin tones and pastels all work), or the names
`black gray blue red green yellow cyan magenta white`.

**Pens, by job:**
- `fineliner`: outlines, details and text. Uniform width. Default 0.4 mm; 0.6–1.2 mm
  for bold contours, 0.25 mm for fine detail.
- `shader`: coloured areas. It's translucent, and the only tool that takes arbitrary
  RGB. As a line pen, give `color` as a name or hex.
- `marker`: bold, flat lines. Palette colours only.
- `highlighter`: wide translucent band with square ends.
- `pencil` / `mechanical_pencil` / `ballpoint` / `calligraphy` / `paintbrush`:
  textured lines. Pick them for sketchy styles.

**Fill methods:** `shader` (default; solid-looking, exact colour, bands 1.2 mm apart),
`marker` (palette colour, wider bands), `hatch` (thin 45° fineliner lines; a pen-drawn
look). The outline is drawn separately in the item's own pen, colour and width. A
yellow face with a black outline is `color: "black"` plus `fill: {color: "yellow"}`.
Fill only what needs colour. Outlines alone are often the clearest.

**Budgets (enforced):** every item that has a fill or comes from an svg is one object,
and it gets **at most 150 strokes, outline included**. A page should stay below a few
thousand strokes; 3000 triggers a warning. A filled 120 mm circle costs about 100 shader
bands, or more where details cut through it (the smiley face is 130), and
`spacing_mm: 2` halves that. A fill that goes over is first widened automatically (up to
2× spacing). If it still doesn't fit, `build` fails with `pages[P][I]: ...`.
- For an `svg` item, the whole SVG must fit in 150 strokes, or it fails with its item
  index. Use `fill: {"method": "none"}`, a simpler SVG, or a smaller box.
- `rmdraw svg` defaults to 150 too. `--budget N` is the only way past it, and it warns.
- Plain lines and text are not budgeted per item, but they count towards the page.

**Composition method:**
1. Name the subject's 3–8 recognisable parts (fox: head, ears, muzzle, eyes, nose,
   cheek fur). Plan a bounding box for each on squared paper (in mm).
2. Build from big simple shapes: ellipses and circles for bodies and heads, closed
   polylines for ears, leaves and roofs, beziers for organic contours and tails, arcs
   for smiles and brows.
3. Layer: background areas → main body (filled) → overlapping parts → details (eyes,
   nose) → lines that sit on top (mouth, whiskers) → caption.
4. Stay symmetric where the subject is (mirror x around the centre line: x' = 2·cx − x).
5. Render, look, adjust. Expect 2–3 rounds.

**Worked example** (`examples/smiley.json`; `examples/tree.json` is another):

```json
{
  "name": "Smiley",
  "pages": [[
    {"type": "circle", "cx": 90, "cy": 110, "r": 60, "width_mm": 0.8,
     "fill": {"color": "yellow"}},
    {"type": "ellipse", "cx": 69, "cy": 90, "rx": 6, "ry": 9,
     "fill": {"color": "black"}},
    {"type": "ellipse", "cx": 111, "cy": 90, "rx": 6, "ry": 9,
     "fill": {"color": "black"}},
    {"type": "arc", "cx": 90, "cy": 112, "r": 36, "start_deg": 25, "end_deg": 155,
     "width_mm": 1.2},
    {"type": "text", "text": "Smile", "x": 90, "y": 190, "height": 8}
  ]]
}
```

The face is first, so the eyes (filled, listed later) cut their area out of its yellow
fill. The smile arc runs 25° → 155° clockwise from 3 o'clock, i.e. through 6 o'clock:
a U shape. Result: about 170 strokes.

Python alternative: `rmdraw.model` (`Stroke(points_mm, pen, color, width_mm, rgba)`,
`Page`, `Document`), `rmdraw.rmdoc.write_rmdoc(doc, path)`, `rmdraw.text.text_strokes`,
`rmdraw.fill.shapes_to_strokes`, `rmdraw.shapes_json.from_dict(data)`.

## Verify

1. Preview SVG: `.venv/bin/rmdraw preview out/x.rmdoc -o out/x.svg`. It is rendered
   from the `.rm` bytes, so it shows what was really written.
2. PNG with headless Chrome, then **open the PNG with the Read tool and look at it**:
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
     --hide-scrollbars --window-size=680,906 --screenshot="$PWD/out/x.png" "file://$PWD/out/x.svg"
   ```
   Ask: is it recognisable? Proportions? Gaps or overlaps? Text inside its space?
3. (SSH only.) After a push, check the device's own rendering: `rmdraw push out/x.rmdoc --thumbs out/x-thumbs`
   (or call `rmdraw.device.fetch_thumbnails(uuid, dir)` later). The 362×512 PNG is
   made by the tablet itself. If none appears within 10 s, ask the user to open the
   notebook, then fetch again.
4. `.venv/bin/pytest -q` before committing library changes.

## The device

- **reMarkable Paper Pro**, software 3.29.1.0, developer mode on. **[device]**
- **Two import routes:**
  1. **Desktop app drag and drop (default; no developer mode needed).** The user
     drags the `.rmdoc` into the reMarkable desktop app, and cloud sync puts it on the
     tablet. **[unverified]** that the app accepts our zip layout; ask the user to confirm.
  2. **SSH push (optional).** `rmdraw push`, thumbnail fetching and the reference-page
     protocol all need SSH, and SSH needs **developer mode**. **Enabling developer mode
     factory-resets the Paper Pro** (everything not synced is lost). Never ask a user
     to enable it just for rmdraw. Use route 1 instead. This user already has
     developer mode and SSH, so push is available here.
- **SSH:** key auth as `root@10.11.99.1` over USB (`ssh -o BatchMode=yes root@10.11.99.1`).
- Notebooks live in `/home/root/.local/share/remarkable/xochitl/` as `<uuid>.metadata`,
  `<uuid>.content`, `<uuid>/<page-uuid>.rm`, plus `<uuid>.local` and
  `<uuid>.thumbnails/` that the device writes itself.
- **`rmdraw push` / `rmdraw.device.install_rmdoc` only ADDS:** it refuses if the uuid
  already exists, copies the three parts with scp, then runs `systemctl restart xochitl`
  (the UI restarts for a few seconds). Only push when the user asks.
- **Never delete or modify the user's notebooks or any existing file on the tablet.**
  Reading is fine (ls, cat, scp *from* the device). To replace a pushed notebook, push
  a new build (new uuid) and let the user delete the old one on the tablet.
- The USB web interface (http://10.11.99.1) is **off** on this tablet.
- `--host` must be plain `user@host`. Anything else, e.g. a value starting with `-`, is
  rejected so ssh/scp can't read it as an option.
- The file `.remarkable` in the project root holds a secret. **Never read, print, cat
  or commit it.**

## Format facts (details and evidence: `docs/format-notes.md`)

Tags: **[device]** seen on the user's tablet, **[rmscene]** from rmscene 0.8.0 source,
**[unverified]** believed only.

- `.rmdoc` = zip of `<uuid>.content`, `<uuid>.metadata`, `<uuid>/<page>.rm`. Page order
  comes from `.content` `cPages.pages[].idx.value` ("ba", "bb", ...). **[device]**
- Page = 1620 × 2160 units, 229 PPI → 9.016 units/mm; **x is centred**
  (−810..+810), y runs 0..2160 from the top. **[device]**
- The scene must contain a `SceneInfo` block with `paper_size=(1620, 2160)`;
  rmscene's own sample writer omits it. **[device]**
- Tool ids: fineliner FINELINER_2 (17), ballpoint 15, marker 16, pencil 14, mech.
  pencil 13, calligraphy 21, paintbrush 12, highlighter 18, shader 23. **[device]**
- Pen colours: fixed enums; green = GREEN_2 (10) and yellow = YELLOW_2 (13), not 4/3.
  Highlighter colours 3, 14, 5, 15, 4, 16. **[device]**
- Pens **ignore** `color_rgba`; the shader (colour HIGHLIGHT 9 + rgba) **honours**
  arbitrary ARGB. Fill alpha 230 looks solid; 170 looks washed out. **[device]**
- `point.width` ≈ 4 × stroke width in px. **[rmscene]/[unverified]**. Thickness scale
  2.0 = size 2. **[device]**
- 2-point strokes render as straight lines. Lasso scaling rewrites points; nothing
  special is needed for strokes to be editable. **[device]**
- Minimum speed/pressure values for full-width rendering: **[unverified]** (we write
  pressure 236 and speed 0, and they render fine).

## Learning new facts from device examples

When something is unknown (a new pen, a colour, layers, text blocks), get ground truth
from the tablet instead of guessing. Steps 2–3 need SSH (developer mode; see above).
Without SSH, the user can export the notebook from the desktop app instead.

1. **Reference page protocol.** Ask the user to make a new notebook and draw exactly
   specified strokes at known positions. Example: "a dot in each corner, then one
   horizontal line per pen across the top third, each in a different colour; on page 2,
   a circle, then lasso-copy it and scale the copy 2×". Write down what you asked for.
2. Find it and copy it **read-only**:
   ```bash
   ssh root@10.11.99.1 'grep -l "Rm-reference" /home/root/.local/share/remarkable/xochitl/*.metadata'
   scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl/<uuid>{.content,.metadata} out/ref/
   scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl/<uuid> out/ref/
   ```
3. `.venv/bin/rmdraw dump out/ref/<uuid>/<page>.rm` and compare it with what you asked
   for: tools, colour enums, rgba, widths, bbox positions (device units: x centred).
4. Record each finding in `docs/format-notes.md` with a tag and the date. Copy useful
   pages into `tests/fixtures/reference/` with a test. Update this skill.

**Improving the skill from user-supplied pairs** (an image or SVG plus the user's own
`.rm`/`.rmdoc` or a photo of the tablet): convert the input with rmdraw, dump both
`.rm` files, then compare stroke counts, tools, colours and positions, and the
preview with the device thumbnail. Turn each difference into a test, a code fix and a
skill or format-notes update. Keep the facts tagged.

## Pitfalls

- **Pens ignore rgba** (only the enum counts). For an exact colour, use a shader fill
  or the shader pen. Fineliner outline colours snap to the nearest palette colour.
- **Colours 14–16** (highlighter blue, orange, grey) crash plain rmscene 0.8.0 reads.
  `import rmdraw` installs `rmdraw.rmcompat`, which extends `PenColor`. Always import
  rmdraw before reading `.rm` files with rmscene.
- **SceneInfo paper_size block is required.** The device writes it, and rmscene's
  sample writer leaves it out. `rmdraw.rmwriter` writes it, so don't hand-roll scenes.
- **x is centred** in device units (0 = page middle). In rmdraw you work in mm from
  the top-left, and the conversion is done for you. Watch it when reading dumps.
- **White is a gap, not paint.** White fills draw nothing (they hide what's below).
  A white pen line on colour is just a white stroke. Use white fills to cut holes.
- **Descenders:** text `y` is the cap top. Letters like g, j, p, q, y reach about a third of
  `height` below the baseline. Leave room below text and above the page edge.
- **150-stroke budget per object, enforced** (the outline counts). Dense fills, hatch
  at small spacing and very detailed SVGs blow it, and the build then fails. Widen
  `spacing_mm`, fill fewer areas, or simplify. Pages
  above a few thousand strokes get sluggish to open and lasso.
- Off-page points are an error. Keep 10 mm margins; scaled SVGs can spill.
- Arcs go clockwise in screen space (y down). A "frown" is 205 → 335.
- **`.remarkable` holds a secret. Never read or print it.**
- Never push without the user asking, and never delete or overwrite on the device.
