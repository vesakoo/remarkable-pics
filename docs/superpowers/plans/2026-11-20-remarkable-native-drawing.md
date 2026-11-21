# reMarkable Native Drawing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python library and CLI, plus a project skill, that turn vector shapes (from SVG or from Claude's own composition) into native, editable reMarkable Paper Pro notebooks (`.rmdoc` with v6 `.rm` pages). Prove it with a 50-icon AWS notebook.

**Architecture:** One in-memory model (`Document → Page → Stroke`, in millimetres) is fed by front ends: an SVG importer, a stroke font, and a JSON shape list. It is written out by back ends: an `.rm` page writer on top of rmscene, an `.rmdoc` zip packager, and an SVG preview renderer. Format facts that the web couldn't confirm are captured from the user's own tablet over SSH (read-only) and recorded in `docs/format-notes.md`. The skill points to them.

**Tech Stack:** Python 3 (local 3.15.2) in `.venv`. rmscene==0.8.0 (pinned; verified API below), svgelements (SVG parsing, transforms), shapely (fill clipping), HersheyFonts (public-domain single-stroke font), pytest.

**Spec:** `docs/superpowers/specs/2026-11-20-remarkable-native-drawing-skill-design.md`

## Verified rmscene 0.8.0 facts (read from the source on 2026-11-20)

- `PenColor`: BLACK=0, GRAY=1, WHITE=2, YELLOW=3, GREEN=4, PINK=5, BLUE=6, RED=7, GRAY_OVERLAP=8, HIGHLIGHT=9, GREEN_2=10, CYAN=11, MAGENTA=12, YELLOW_2=13. `Line.color_rgba: Optional[tuple[int,int,int,int]]` (tag 8) carries the actual colour for HIGHLIGHT and possibly for others. This is checked in Task 6.
- `Pen`: FINELINER_2=17, BALLPOINT_2=15, MARKER_2=16, PENCIL_2=14, MECHANICAL_PENCIL_2=13, HIGHLIGHTER_2=18, SHADER=23, CALIGRAPHY=21, PAINTBRUSH_2=12 (the `_1` variants are legacy).
- `Point(x: float, y: float, speed: int, direction: int, width: int, pressure: int)`. For v2 it's serialised as f32, f32, u16 speed, u16 width, u8 direction, u8 pressure.
- `Line(color, tool, points, thickness_scale: float, starting_length: float, move_id=None, color_rgba=None)`.
- Page skeleton, taken from `simple_text_document`: `AuthorIdsBlock`, `MigrationInfoBlock(CrdtId(1,1), is_device=True)`, `PageInfoBlock`, `SceneTreeBlock(tree_id=CrdtId(0,11), node_id=CrdtId(0,0), is_update=True, parent_id=CrdtId(0,1))`, `TreeNodeBlock(Group(CrdtId(0,1)))`, `TreeNodeBlock(Group(CrdtId(0,11), label=LwwValue(CrdtId(0,12),"Layer 1")))`, `SceneGroupItemBlock(parent_id=CrdtId(0,1), item=CrdtSequenceItem(CrdtId(0,13), CrdtId(0,0), CrdtId(0,0), 0, CrdtId(0,11)))`. Lines are `SceneLineItemBlock(parent_id=CrdtId(0,11), item=CrdtSequenceItem(item_id, left_id=<previous item id or CrdtId(0,0)>, right_id=CrdtId(0,0), deleted_length=0, value=Line))`.
- Writer: `write_blocks(stream, blocks, options={"version": "3.2.2"})`. Any version above 3.0 writes v2 points.
- Text x-origin is page-centred (`simple_text_document` uses `pos_x=-468, width=936`, which is rM2's 1404 width). The Paper Pro page extents are **unverified** and come from Task 1.

## Global Constraints

- Output is strokes only: no PDF, no raster image, no template background (spec: "No PDF, no embedded raster image, no template background").
- Target device: reMarkable Paper Pro, 11.8″, 2160×1620 @ 229 PPI.
- SSH is **read-only** this round. Never write into `/home/root/.local/share/remarkable/xochitl/` and never stop xochitl. Import goes through the desktop app or the USB web UI (http://10.11.99.1).
- Developer mode must not be required by anything the skill tells a future user to do, except the optional SSH capture.
- Every format fact in `docs/format-notes.md` and the skill is tagged `verified-on-device`, `from-rmscene-source` or `unverified`.
- Per-icon budget is ≤ 150 strokes. When over budget, simplify the fill first, then drop details smaller than 1 mm.
- AWS icon cell is about 20 mm square with the title below, 4 columns, with a clear gap between cells so a lasso around one icon and its title doesn't catch neighbours.
- Downloaded material (AWS asset zip) lives in its own directory `vendor/aws-icons/` and is parsed as data only. Python that reads it runs with `-I` when run ad hoc.

## Review Focus

1. **Real-world SVG features** (nested `<g transform>`, `<use>`, `<rect rx>`, `<circle>`, gradients, `clip-path`). Expected: shapes land in the right place. A gradient fill uses its first stop colour. `clip-path` is ignored with a warning, without crashing. Test in Task 8.
2. **Very long strokes / many points** (big circles at fine tolerance, long hatch lines). Expected: a stroke is split into chunks of ≤ 500 points so the device stays responsive. Test in Task 3.
3. **Coordinates outside the page** (an icon cell placed past the bottom margin). Expected: the layout starts a new page and never writes off-page points. The writer raises `ValueError` on out-of-bounds points. Test in Tasks 3 and 10.
4. **Titles with characters the stroke font lacks** ("Amazon S3 Glacier – Deep", "é", "&"). Expected: missing glyphs are replaced by a space with one warning per character. The title is never dropped. Long titles wrap to 2 lines, then shrink. Test in Task 7.
5. **White or near-white colours** (the AWS glyph is white on colour). Expected: white is never drawn as visible ink on the paper. It becomes a gap in the fill, with the glyph edge outlined in the fill colour. Test in Task 9.

---

### Task 1: Project setup and ground-truth capture from the tablet

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `rmdraw/__init__.py`, `tools/dump_rm.py`, `tests/test_dump_rm.py`, `docs/format-notes.md`, `tests/fixtures/reference/` (copied from the device)

**Interfaces:**
- Produces: `tools/dump_rm.py` CLI `python tools/dump_rm.py <file.rm>` printing one line per stroke: `tool=<Pen name> color=<PenColor name> rgba=<tuple|None> thick=<float> n=<points> bbox=(xmin,ymin,xmax,ymax)`. Function `dump(path: Path) -> list[dict]` with keys `tool, color, rgba, thickness_scale, n_points, bbox`.

- [ ] **Step 1:** `git init`, create `.venv`, write `pyproject.toml` with package `rmdraw`, deps `rmscene==0.8.0`, `svgelements`, `shapely`, `HersheyFonts`, dev dep `pytest`, console script `rmdraw = "rmdraw.cli:main"`. Run `pip install -e '.[dev]'`. Expected: `python -c "import rmscene, svgelements, shapely, HersheyFonts"` exits 0.
- [ ] **Step 2: User checkpoint. Ask the user to draw the reference page** in a new notebook named `RM-REFERENCE` (portrait, blank template):
  1. Fineliner, black, thinnest setting: one dot in each of the four page corners, as close to the corner as possible, and one dot at the exact centre.
  2. A horizontal ruler line across the top using the fineliner.
  3. One short horizontal stroke per pen, top to bottom, each in black: fineliner, ballpoint, marker, pencil, mechanical pencil, calligraphy, paintbrush, highlighter, shader.
  4. One short fineliner stroke per colour, in this order: black, grey, white (on top of a black square), blue, red, green, yellow, cyan, magenta.
  5. One highlighter stroke per highlighter colour, and one shader stroke per shader colour.
  6. Page 2: one fineliner circle about 5 cm across, then lasso it, copy, and paste a 2× scaled copy.
  Ask the user to confirm when done and read the software version from Settings → General → About.
- [ ] **Step 3:** Over SSH, list `xochitl/*.metadata`. Find the one with `"visibleName": "RM-REFERENCE"`, then `scp` its `.metadata`, `.content` and `<uuid>/` directory into `tests/fixtures/reference/`. Also capture `cat /etc/version` and `uname -a` into `docs/format-notes.md`. Read-only: `ls`, `cat`, `grep`, `scp` from the device only.
- [ ] **Step 4: Write the failing test** `tests/test_dump_rm.py::test_reference_page1_has_expected_strokes`. Assert that `dump()` of reference page 1 returns ≥ 5 + 1 + 9 + 9 strokes, that the set of tools includes `FINELINER_2`, `MARKER_2`, `SHADER`, and that some stroke has `color == "CYAN"` or a non-None `rgba`.
- [ ] **Step 5:** Run `pytest tests/test_dump_rm.py -v`. Expected: FAIL (`dump` not defined).
- [ ] **Step 6:** Implement `dump()` with `rmscene.read_tree` and walk the tree for `Line` items.
- [ ] **Step 7:** Run the test. Expected: PASS.
- [ ] **Step 8:** Write `docs/format-notes.md`, tagged `verified-on-device`:
  - page extents (min/max x/y from the corner dots, centre coordinate);
  - units per mm (ruler length ÷ physical width 179 mm);
  - the pen → `Pen` enum, colour → `PenColor`/`rgba` table as the device wrote it;
  - typical `thickness_scale`, `width` and `pressure` per pen;
  - full `.content` and `.metadata` JSON (keys and example values);
  - the file layout inside the document directory, including any `.pagedata`, `-metadata.json` and thumbnails;
  - firmware version;
  - what scaling did to page 2 (were points rewritten, or was a transform stored?).
- [ ] **Step 9:** Commit: `chore: project setup, reference capture, format notes`.

### Task 2: Shape model and page geometry

**Files:**
- Create: `rmdraw/model.py`, `rmdraw/geometry.py`, `tests/test_geometry.py`

**Interfaces:**
- Produces:
  - `Stroke(points: list[tuple[float,float]], pen: str = "fineliner", color: str = "black", width_mm: float = 0.3, rgba: tuple[int,int,int,int] | None = None)`. Points are in mm from the page's top-left.
  - `Page(strokes: list[Stroke])`
  - `Document(name: str, pages: list[Page])`
  - In `geometry.py`: `PAGE_W_MM`, `PAGE_H_MM`, `mm_to_units(x_mm, y_mm) -> tuple[float,float]`, `units_per_mm() -> float`, `width_to_device(pen: str, width_mm: float) -> tuple[float thickness_scale, int point_width]`. Values come from `docs/format-notes.md`; each constant carries a comment citing it.
  - `PEN_NAMES` is a dict from `"fineliner"|"ballpoint"|"marker"|"pencil"|"mechanical_pencil"|"highlighter"|"shader"|"calligraphy"|"paintbrush"` to `Pen`.
  - `COLOR_NAMES` is a dict from `"black"|"gray"|"white"|"blue"|"red"|"green"|"yellow"|"cyan"|"magenta"|"pink"` to `PenColor`.

- [ ] **Step 1: Failing tests:**
  - `test_corners_map_to_reference_extents`: `mm_to_units(0,0)` and `mm_to_units(PAGE_W_MM, PAGE_H_MM)` are within 2% of the corner-dot coordinates recorded from the reference.
  - `test_centre_maps_to_reference_centre`.
  - `test_width_round_trip`: the fineliner 0.3 mm width lands within 25% of the reference fineliner's point width.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the dataclasses and geometry functions.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: shape model and Paper Pro geometry`.

### Task 3: `.rm` page writer

**Files:**
- Create: `rmdraw/rmwriter.py`, `tests/test_rmwriter.py`

**Interfaces:**
- Consumes: `Page`, `Stroke`, `mm_to_units`, `width_to_device`, `PEN_NAMES`, `COLOR_NAMES`.
- Produces: `page_blocks(page: Page) -> list[Block]` and `write_page(page: Page, out: BinaryIO) -> None`. Uses the verified skeleton above. Line item ids are `CrdtId(1, 100 + i)` chained through `left_id`. Strokes longer than `MAX_POINTS = 500` are split. Points get constant `speed`, `direction=0`, and the `width` and `pressure` from the reference fineliner. `color_rgba` is set when `Stroke.rgba` is given.

- [ ] **Step 1: Failing tests:**
  - `test_round_trip_preserves_strokes`: write a page with 3 strokes (fineliner black, marker blue, shader with rgba), read it back with `rmscene.read_tree`, and assert 3 lines, matching tools and colours, and the first point equal to `mm_to_units` within 0.01.
  - `test_long_stroke_is_chunked`: a 1,200-point stroke becomes 3 lines.
  - `test_out_of_bounds_raises`: a point at (−1, 10) mm raises `ValueError`.
  - `test_header_matches_reference_structure`: the block type sequence of the written page starts with the same block types, in the same order, as reference page 1's non-line blocks.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: v6 .rm page writer`.

### Task 4: `.rmdoc` packager

**Files:**
- Create: `rmdraw/rmdoc.py`, `tests/test_rmdoc.py`

**Interfaces:**
- Consumes: `Document`, `write_page`.
- Produces: `write_rmdoc(doc: Document, path: Path) -> str` (returns the document uuid). The zip contains `<uuid>.content`, `<uuid>.metadata` and `<uuid>/<page-uuid>.rm`, plus any other files that Task 1 showed are required. JSON keys and value shapes mirror the reference fixture exactly, apart from ids, names, timestamps and page count.

- [ ] **Step 1: Failing tests:**
  - `test_zip_layout`: names in the zip match the pattern above, one `.rm` per page.
  - `test_content_keys_match_reference`: the recursive key set of `.content` equals the reference's. Page ids in `.content` equal the `.rm` file stems, in order.
  - `test_metadata_fields`: `visibleName == doc.name`, `type == "DocumentType"`, and the rest of the key set equals the reference's.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: rmdoc packager`.

### Task 5: Preview renderer

**Files:**
- Create: `rmdraw/preview.py`, `tests/test_preview.py`

**Interfaces:**
- Produces: `render_rmdoc_svg(path: Path, page_index: int = 0) -> str`. It reads the `.rm` back through rmscene, not from the in-memory model, so the preview shows what the file contains. Stroke width comes from the point widths, colour from `rgba` or the palette, and shader/highlighter get 35% opacity.

- [ ] **Step 1: Failing test** `test_preview_contains_one_path_per_line`. A 3-stroke document gives 3 `<path` or `<polyline` elements, with `viewBox` equal to the page size in mm.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: svg preview of rmdoc pages`.

### Task 6: Calibration notebook and device check

**Files:**
- Create: `examples/calibration.py`, `out/calibration.rmdoc` (git-ignored)
- Modify: `docs/format-notes.md`, and `rmdraw/geometry.py` constants if the device disagrees

**Interfaces:**
- Consumes: `Document`, `write_rmdoc`, `render_rmdoc_svg`.

- [ ] **Step 1:** Write `examples/calibration.py` to build `RM-CALIBRATION`.
  - **Page 1:**
    - numbered markers 1–4 at the corners, 5 mm inset;
    - marker 5 at the centre;
    - a 10 mm grid;
    - every pen × black;
    - every palette colour in fineliner;
    - AWS orange `(255,153,0,255)`, purple `(140,79,255,255)` and pink `(231,21,123,255)` as `rgba` on fineliner, marker and shader.
  - **Page 2:** three fill tests on 20 mm squares:
    - shader band strokes;
    - marker band strokes;
    - hatching at 1.0 and 1.5 mm.
  - Every swatch carries a number label (stroke font from Task 7 isn't ready yet, so use short numeric glyph polylines drawn inline).
- [ ] **Step 2:** Run it, render the preview to `out/calibration-p1.svg`, open it locally and check it visually.
- [ ] **Step 3: User checkpoint.** Ask the user to import `out/calibration.rmdoc` via the desktop app or USB web UI and report:
  - does it open as a notebook;
  - which numbered swatches are wrong or missing;
  - do the AWS rgba colours show as themselves or get snapped;
  - which fill looks best;
  - does lasso-copy and scale of one swatch work.
  Then `scp` the imported copy back read-only to confirm the device didn't rewrite anything.
- [ ] **Step 4:** Record the findings in `docs/format-notes.md` as `verified-on-device` and adjust the geometry constants if needed. Write the chosen fill method and the rgba verdict into `rmdraw/palette.py` defaults in Task 9.
- [ ] **Step 5:** Commit: `feat: calibration notebook and device findings`.

### Task 7: Stroke-font text

**Files:**
- Create: `rmdraw/text.py`, `tests/test_text.py`

**Interfaces:**
- Produces: `text_strokes(s: str, x_mm: float, y_mm: float, height_mm: float, max_width_mm: float | None = None, align: str = "center", color: str = "black") -> list[Stroke]`. Uses the HersheyFonts `futural` font. `y_mm` is the top of the text box. It wraps at word boundaries to at most 2 lines, then shrinks the height until it fits `max_width_mm`.

- [ ] **Step 1: Failing tests:**
  - `test_text_produces_strokes_within_box`: `"Amazon EC2"` at height 2.5 mm, width 22 mm gives strokes whose bbox fits inside the box.
  - `test_wraps_long_title`: `"AWS Elastic Load Balancing"` at width 22 mm gives two text lines (max y spans more than one line height).
  - `test_missing_glyph_becomes_space`: `"Café – S3"` gives strokes, emits a warning per unknown character, and is not empty.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: single-stroke text`.

### Task 8: SVG import

**Files:**
- Create: `rmdraw/svgimport.py`, `tests/test_svgimport.py`, `tests/fixtures/svg/*.svg` (small hand-written fixtures)

**Interfaces:**
- Produces:
  - `FilledShape(outline: list[list[tuple[float,float]]], fill_rgb: tuple[int,int,int] | None, stroke_rgb: tuple[int,int,int] | None)`. The outline holds rings in mm. The first ring is the exterior and any further rings are holes, following SVG even-odd/nonzero as parsed.
  - `svg_to_shapes(path: Path, box: tuple[float,float,float,float], tolerance_mm: float = 0.15) -> list[FilledShape]`. It fits the SVG viewBox into `box = (x, y, w, h)` mm, keeping aspect ratio and centring. Curves are flattened via svgelements at the given tolerance.

- [ ] **Step 1: Failing tests:**
  - `test_rect_maps_into_box`: a 48×48 viewBox `<rect>` maps to the box corners.
  - `test_group_transform_applied`: a `<g transform="translate(10,0)">` shifts the shape.
  - `test_circle_flattened_smoothly`: every vertex of a flattened circle lies within `tolerance_mm` of the true radius.
  - `test_gradient_uses_first_stop`.
  - `test_clip_path_ignored_with_warning`.
  - `test_use_element_resolved`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with `svgelements.SVG.parse(..., reify=True)`. Iterate over `Shape` elements, apply `.segments()` / `npoint` sampling, and read `fill` / `stroke`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: svg to shapes import`.

### Task 9: Fill, palette mapping and budget simplification

**Files:**
- Create: `rmdraw/fill.py`, `rmdraw/palette.py`, `tests/test_fill.py`, `tests/test_palette.py`

**Interfaces:**
- Consumes: `FilledShape`, `Stroke`.
- Produces:
  - `to_pen_color(rgb) -> tuple[str color, tuple|None rgba]`. It uses the rgba verdict from Task 6: if rgba is honoured, it returns the nearest palette name plus exact rgba. Otherwise it returns the category override or the nearest palette name.
  - `AWS_CATEGORY_COLORS: dict[str, str]`, taken from the spec: compute=yellow, storage=green, database=blue, networking=magenta, integration=red, security=red, analytics=cyan, management=gray, ai_ml=cyan.
  - `shapes_to_strokes(shapes: list[FilledShape], method: str, spacing_mm: float, budget: int = 150, color_override: str | None = None) -> list[Stroke]`. `method` is one of `"shader" | "marker" | "hatch"`, with the default chosen in Task 6.
  - A white or near-white fill (all channels ≥ 230) becomes a hole: it's subtracted from the fill area with shapely and its edge is outlined in the parent fill colour.
  - When over budget: (1) increase the spacing in 25% steps, up to 2×; (2) drop rings with area < 1 mm²; (3) Douglas-Peucker simplify the outlines at 0.2 mm.

- [ ] **Step 1: Failing tests:**
  - `test_hatch_covers_square`: hatching a 20 mm square at 1.5 mm spacing gives 13 ± 1 lines, all inside the square.
  - `test_white_glyph_becomes_gap`: a white circle on an orange square gives no stroke points inside the circle (except its outline), and no stroke has colour white.
  - `test_budget_enforced`: a shape with 400 tiny rings gives ≤ 150 strokes.
  - `test_aws_orange_maps_to_category_color` (no-rgba mode): returns `"yellow"`.
  - `test_aws_orange_keeps_rgba` (rgba mode): returns rgba `(255,153,0,255)`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: fills, palette mapping, stroke budget`.

### Task 10: AWS top-50 icon notebook

**Files:**
- Create: `data/aws_top50.json`, `examples/aws_icons.py`, `rmdraw/layout.py`, `tests/test_layout.py`
- Vendor: `vendor/aws-icons/` (git-ignored, downloaded)

**Interfaces:**
- Consumes: `svg_to_shapes`, `shapes_to_strokes`, `text_strokes`, `write_rmdoc`, `render_rmdoc_svg`.
- Produces: `grid_layout(items: list[tuple[str category, str title]], cell_mm: float = 20, title_h_mm: float = 2.5, cols: int = 4, gap_mm: float = 8, margin_mm: float = 12) -> list[list[Cell]]`, where `Cell(category, title, icon_box, title_box)` is grouped per page. A category heading row is emitted when the category changes. A new page starts when the next row doesn't fit.

- [ ] **Step 1:** Write `data/aws_top50.json` with the spec's 50 services, grouped by category in spec order. Each entry is `{"title": "...", "category": "...", "match": "<filename substring>"}`. Titles are the official short names, e.g. "Amazon EC2".
- [ ] **Step 2:** Download the current AWS Architecture Icons asset package from https://aws.amazon.com/architecture/icons/ into `vendor/aws-icons/` and unzip it there. Pick the 48 px service SVGs. Any `match` without a hit gets swapped for the next most common service in that category and reported to the user.
- [ ] **Step 3: Failing tests:**
  - `test_layout_never_leaves_page`: every box lies within the page minus margins for 50 items.
  - `test_cells_do_not_overlap_and_keep_gap`.
  - `test_heading_on_category_change`.
  - `test_50_items_fit_in_at_most_4_pages`.
- [ ] **Step 4:** Run. Expected: FAIL.
- [ ] **Step 5:** Implement `grid_layout`, then `examples/aws_icons.py`, which builds `out/aws-top50.rmdoc` named `AWS Icons – Top 50` and prints the strokes per icon. Any icon over 150 strokes is a bug.
- [ ] **Step 6:** Run the tests. Expected: PASS. Run the example and render every page preview. Visually check that the icons are recognisable and each title sits under its icon.
- [ ] **Step 7: User checkpoint.** The user imports the notebook and checks recognisability, lasso of icon + title, scaling, and responsiveness. Fix what they report.
- [ ] **Step 8:** Commit: `feat: AWS top-50 icon notebook`.

### Task 11: CLI, description workflow, and the skill

**Files:**
- Create: `rmdraw/cli.py`, `rmdraw/shapes_json.py`, `tests/test_cli.py`, `examples/smiley.json`, `.claude/skills/remarkable-native/SKILL.md`
- Modify: `docs/format-notes.md` (final pass)

**Interfaces:**
- Consumes: everything above.
- Produces:
  - Shape JSON schema, `shapes_json.load(path) -> Document`. Format: `{"name": str, "pages": [[{"type": "polyline"|"circle"|"ellipse"|"rect"|"arc"|"text"|"svg", "pen", "color", "width_mm", "fill": {"color", "method"}?, ...geometry in mm}]]}`. `svg` embeds a file path plus a box.
  - CLI:
    - `rmdraw build <shapes.json> -o <out.rmdoc>`
    - `rmdraw svg <file.svg> -o <out.rmdoc> [--box x,y,w,h] [--fill hatch|marker|shader|none]`
    - `rmdraw preview <file.rmdoc> -o <page.svg> [--page N]`
    - `rmdraw dump <file.rm>`

- [ ] **Step 1: Failing tests:**
  - `test_cli_build_smiley`: `rmdraw build examples/smiley.json -o tmp.rmdoc` exits 0, and the zip has 1 page with ≥ 4 strokes.
  - `test_cli_svg`: one fixture SVG gives a valid rmdoc.
  - `test_shapes_json_rejects_unknown_type` with a clear error message.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. `examples/smiley.json` is an original smiling face: a circle, two eyes, and a smile arc, with a yellow hatch fill.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Write `.claude/skills/remarkable-native/SKILL.md`:
  - Frontmatter `name: remarkable-native`. The description says when to use it: making or converting anything into native editable reMarkable notebooks.
  - Sections:
    - what "native" means;
    - the quick recipe for each input (description → shapes JSON → `rmdraw build`; SVG → `rmdraw svg`; raster → not yet, planned);
    - how to draw from a description (compose in mm on the 179 × 239 mm page, palette, pens, fill methods, stroke budget);
    - how to import on the device;
    - format facts, pointing to `docs/format-notes.md` with tags;
    - how to learn new facts from device examples (the Task 1 reference-page protocol, SSH read-only commands);
    - pitfalls.
- [ ] **Step 6: Fresh-session check.** Dispatch a fresh subagent with only the skill. Ask it to make "a simple original fox head, front view" as `out/fox.rmdoc` and render a preview. Fix the skill wherever the subagent had to guess.
- [ ] **Step 7:** Commit: `feat: CLI, shapes JSON, remarkable-native skill`.
