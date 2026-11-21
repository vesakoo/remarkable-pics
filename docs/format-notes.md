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

## Open questions for calibration

- Answered: pens ignore rgba; shader honours it (see the import test above).
- Is the `.rmdoc` zip layout `<uuid>.content`, `<uuid>.metadata`, `<uuid>/<page>.rm` accepted by the desktop app and USB import, and which of the device's keys are required?
- Minimum speed, direction and pressure values for strokes to render with full width.
