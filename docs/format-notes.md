# reMarkable Paper Pro — native notebook format notes

Tags: **[device]** = verified from the user's own tablet (reference notebook
`Rm-reference`, captured 2026-11-21 over SSH, read-only). **[rmscene]** = read
from rmscene 0.8.0 source. **[unverified]** = believed, not yet proven.

Fixture: `tests/fixtures/reference/8854cd39-dba3-48f7-8c5f-e6b9f0cea45f*`.
Page 1 = `f4017db6-….rm` (pens, colours), page 2 = `ca78643d-….rm` (circle + 2× copy).
The reference was hand-drawn, so all positions are approximate.

## Device

- reMarkable Paper Pro (hostname `imx8mm-ferrari`; "Ferrari" is the Paper Pro's codename), software **3.29.1.0**, build `20261028104944`, kernel 6.12.49, aarch64. [device]
- Stylus: **reMarkable Marker Plus** (user reports model RM05C). The stylus doesn't change the file format: strokes record the selected tool. The Marker Plus eraser end produces eraser actions, i.e. tombstoned strokes, not ink.
- The user also reports firmware **2.23-1.1.84**. The tablet itself reports 3.29.1.0, and v6 `.rm` files only exist on tablet software 3.x, so 2.23-1.1.84 is most likely the Marker Plus stylus firmware. [unverified which device it belongs to]
- Notebooks live in `/home/root/.local/share/remarkable/xochitl/`. We access it read-only. [device]

## Files of one notebook on the device [device]

```
<doc>.metadata     JSON: visibleName, type "DocumentType", parent "", createdTime/lastModified/lastOpened (ms, as strings), lastOpenedPage, new, pinned, source
<doc>.content      JSON: fileType "notebook", formatVersion 2, pageCount, orientation "portrait",
                   cPages.pages[] = {id, idx{timestamp,value:"ba","bb",…}, modifed, template{value:"Blank"}, (scrollTime, verticalScroll)},
                   cPages.lastOpened, cPages.original, cPages.uuids[{first,second}], customZoom* (1404×1872!), extraMetadata (last-used tools), tags, pageTags, zoomMode …
<doc>.local        {"contentFormatVersion": 2}
<doc>/<page>.rm    one v6 scene file per page; file name = page id from .content
<doc>.thumbnails/<page>.png   362×512 previews (device-generated)
```

- Page order comes from `cPages.pages[].idx.value` (fractional-index strings "ba", "bb", …). [device]
- `customZoomPageWidth/Height` still say 1404×1872 (legacy). The real page size is in the `.rm` (below). [device]

## Page geometry [device]

- `SceneInfo.paper_size = (1620, 2160)`, so the page is 1620 × 2160 units, portrait.
- Units = screen pixels at 229 PPI, which is **9.016 units per mm**. Page ≈ 179.7 × 239.6 mm.
- **x is centred**: x ∈ [-810, +810], with 0 at the middle. **y starts at the top**: y ∈ [0, 2160]. The corner dots landed at (-758, 63), (+693, 62), (-785, 2146), (+721, 2118), consistent with this given hand inaccuracy.
- Page 1's `.content` has `verticalScroll: 2160`. The page was scrolled, not extended: the lowest stroke is at y ≈ 2149.

## Scene skeleton written by the device [device]

AuthorIdsBlock → MigrationInfoBlock(1,1, is_device) → PageInfoBlock → **SceneInfo(paper_size=(1620,2160))** → SceneTreeBlock(0:11 under 0:1) → TreeNodeBlock(0:1) → TreeNodeBlock(0:11, "Layer 1") → SceneGroupItemBlock(0:13 → 0:11) → line items (parent 0:11).
This differs from rmscene's `simple_text_document`, which has **no SceneInfo block**. We must write SceneInfo with paper_size (1620, 2160).
Deleted strokes stay as tombstones (`value=None`). Item ids are `CrdtId(1, n)`, increasing.

## Pens (tool ids) [device]

| Tablet tool | `Pen` | thickness_scale (size 1/2/3) | median point.width at size 2 |
|---|---|---|---|
| Fineliner | FINELINER_2 (17) | 1.0 / 2.0 / 3.0 | 16 (size 1 → 8) |
| Ballpoint | BALLPOINT_2 (15) | 2.0 | 18 |
| Marker | MARKER_2 (16) | 2.0 (3.0 → width 69–92) | 41 |
| Pencil | PENCIL_2 (14) | 2.0 | 22 |
| Mechanical pencil | MECHANICAL_PENCIL_2 (13) | 2.0 | 24 |
| Calligraphy | CALIGRAPHY (21) | 2.0 | 8 (varies with direction) |
| Paintbrush | PAINTBRUSH_2 (12) | 2.0 | 36 |
| Highlighter | HIGHLIGHTER_2 (18) | 1.0 | 120 |
| Shader | SHADER (23) | 2.0 | 88 |

- `point.width` is about 4 × the stroke width in px (rmc convention, [rmscene]/[unverified]). Fineliner size 2 ≈ 4 px ≈ 0.44 mm.
- **Straight lines are stored as just 2 points** (the tablet's straighten-line feature). A 2-point stroke is valid and renders as a straight line. [device]
- Dots are 1–2 point strokes with low pressure. [device]

## Colours [device]

Pens (fineliner etc.) use **fixed palette enums, no rgba**:

| Colour | `PenColor` value |
|---|---|
| black | BLACK 0 |
| grey | GRAY 1 |
| white | WHITE 2 |
| blue | BLUE 6 |
| red | RED 7 |
| green | **GREEN_2 10** (not GREEN 4) |
| yellow | **YELLOW_2 13** (not YELLOW 3) |
| cyan | CYAN 11 |
| magenta | MAGENTA 12 |

Highlighter: 6 colours, enum only, no rgba. Menu order top to bottom: yellow **3**, blue **14**, pink **5**, orange **15**, green **4**, grey **16**.
**Values 14, 15 and 16 are unknown to rmscene 0.8.0** (`PenColor` raises an error, so the block becomes an UnreadableBlock). We must extend the enum or patch around it to read and write them.

Shader: 8 colours. Each has `color = HIGHLIGHT (9)` plus **`color_rgba` (r, g, b, a)** with alpha. Menu order:
grey/black (33,30,28,64), orange (254,178,0,115), purple (192,127,210,128), blue (48,74,224,77),
red (194,49,50,102), green (145,218,113,128), yellow (250,231,25,115), cyan (116,210,232,102).
`.content` stores the shader colour as `"ArgbCode"` with a signed 32-bit ARGB integer, e.g. 1724002610 = 0x66C23132 = a102 r194 g49 b50.
This means the shader takes **arbitrary ARGB**. That's the best candidate for AWS category colours. [device]. Whether pens accept arbitrary rgba is [unverified], to be tested in the calibration notebook.

## Lasso: copy, move, scale [device]

- A moved stroke gets `move_id`.
- **Scaling rewrites the points** (no transform is stored) and multiplies `thickness_scale`: the 2× copy has thickness_scale 3.411 vs 2.0, and points spread by 1.70×.
- So generated strokes need nothing special to be copyable or scalable.

## Import test of a generated notebook (RM-SMOKE, 2026-11-21) [device]

- Generated by rmdraw (rmwriter + rmdoc). Installed by copying `<doc>.content`, `<doc>.metadata` and `<doc>/<page>.rm` into xochitl/ over SSH, then `systemctl restart xochitl` (the user authorised device writes). The USB web interface (10.11.99.1:80) was off.
- xochitl accepted it: log line `loaded pageId=…, version=6`. It created `<doc>.local` and a thumbnail by itself. The device thumbnail is stored at `tests/fixtures/smoke-device-thumbnail.png`.
- Geometry matches: a 40 mm square at (20,20) mm and the circle land exactly where expected.
- All 8 fineliner palette colours render correctly (green = GREEN_2, yellow = YELLOW_2).
- **Shader + `color_rgba` (255,153,0,140) renders as AWS orange.** The shader honours arbitrary ARGB.
- **Fineliner RED + `color_rgba` orange renders RED.** Pens ignore `color_rgba`; only the enum counts.
- Highlighter HIGHLIGHT_ORANGE (15) renders orange, with a square-ended band.
- Consequence for fills: use the shader with exact rgba for coloured areas. Use palette pens for outlines and text.
- Thumbnails of pushed notebooks (seen across several pushes, e.g. the fresh-session fox test): sometimes ready within ~10 s, sometimes after more than 40 s, sometimes only once the notebook is opened on the tablet. Often only page 1 gets one. `rmdraw thumbs <uuid>` retries. [device]

## Fill defaults [device]

- RM-CALIBRATION showed shader fills at alpha 170 look washed out; alpha 230 looks solid. `palette.FILL_ALPHA` is 230.
- Of the spacing/inset variants, shader spacing 1.2 mm with the quarter inset (band edge inset by width/4) gave the most solid icon, at ~36 strokes. These are the `shapes_to_strokes` defaults.

## Fox v1 on the device (photo, 2026-11-21) [device]

- Shader bands with round caps overshooting the edge by ~width/4 are clearly visible: a
  dashed/wavy border on white gaps and saw-tooth slanted edges. Fixed by the "contour"
  fill (`rmdraw/fill.py`): nothing is painted outside the shape.
- 1.2 mm bands with overlap 1.25 show as visible horizontal stripes on large areas.
  Spacing/overlap swatches are on page 2 of "Fox v2" (uuid 5787c77a-…); pending the
  user's pick.
- Acute corners (ear tips, ellipse ends) were left white; contour fill adds spurs.
- `#e8740c` rendered tan; stronger oranges are on the swatch page.

## Open questions for calibration

- Answered: pens ignore rgba; shader honours it (see the import test above).
- Answered 2026-11-21 [device]: the desktop app accepts our `.rmdoc` by drag and drop (`out/owl.rmdoc`); it synced to the tablet, which showed it after a restart. Still open: which of the device's `.content` keys are required.
- Confirmed again 2026-11-24 [device]: `out/aws-icons/aws-icons-top50.rmdoc` dragged into a folder (`rema-pics`) in the macOS desktop app. The app showed it at once with a page-1 thumbnail rendered from our strokes and "Page 1 of 4". It reached the tablet, in the same folder, within about a minute, with no restart this time.
- Minimum speed, direction and pressure values for strokes to render with full width.

## Where these facts are used

- `.claude/skills/remarkable-native/SKILL.md` is the working summary for future sessions. Keep its tags in step with this file.
- Tools: `rmdraw build|svg|preview|dump|push` (`rmdraw/cli.py`). `rmdraw dump <page.rm>` is the way to read device examples. `tools/dump_rm.py` is kept as a wrapper.
- New device findings: follow the reference-page protocol in the skill, tag them here, and add a fixture plus a test.

## Solid (opaque) fills for stickers — 2026-11-22

rmdraw's white fill is a gap: it draws nothing, so a lassoed shape pasted over other ink lets
that ink show through. For sticker-like templates (`examples/doodles.py`) every filled shape
gets an opaque base first: a contour fill of **white fineliner** strokes (1.75 mm wide, 1.4 mm
apart), then the shader colour on top, then the outline.

- **White pen ink is opaque** on the Paper Pro: it covers what is below it. [device] (user, 2026-11-22)
- **Only the shader and the highlighter are translucent**; every other pen (fineliner, ballpoint,
  marker, pencils, calligraphy, paintbrush) paints opaque. [device] (user, 2026-11-22)
- So a shader colour on its own lets ink below show through; on a white-pen base it is solid.
