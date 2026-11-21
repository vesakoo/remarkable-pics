# reMarkable native drawing skill — design

Date: 2026-11-20
Status: approved by user 2026-11-20

## Intent and why

The user wants Claude to be able to produce **native, editable reMarkable notebooks**
for a **reMarkable Paper Pro** (confirmed by the user: 11.8″ colour, 2160×1620 @
229 PPI). Firmware version: not yet known. The calibration step records it.

"Native" means pages made of real pen strokes in reMarkable's own v6 `.rm` format,
packaged as a notebook. On the tablet they must be erasable, lasso-selectable,
copyable and scalable like the user's own handwriting. **No PDF, no embedded raster
image, no template background.**

Two input kinds, long term:
1. **Any image** (SVG, PNG, JPG, …) → strokes.
2. **A verbal description** ("a fox", "a smiling face", "a tree", "a mind map with
   three branches") → Claude composes vector shapes → strokes.

Understanding the format itself is the point. The user will later ask to improve the
skill with specific image/file pairs. The knowledge therefore has to live in a
reusable project skill plus a small converter library, not in one-off scripts.

## First concrete deliverable

A notebook of the **50 most commonly used AWS architecture service icons**, in
**outline plus fill**, each with a **written title under it**, laid out so the user
can lasso an icon together with its title and paste it into their own diagrams.

## Goals

- A project skill (`.claude/skills/remarkable-native/SKILL.md`) that teaches any
  future session: the `.rmdoc` package structure, the v6 `.rm` stroke model (pens,
  colours, widths, coordinates), the Paper Pro page geometry, how to get files onto
  the tablet, and known pitfalls.
- A small Python library + CLI in this project that turns a list of vector shapes
  (polylines/paths with stroke colour, pen, width, optional fill) into a valid
  `.rmdoc`.
- An SVG → shapes front end (covers the AWS icons and any vector art).
- A shapes-from-description workflow: Claude writes shapes (SVG or a simple JSON
  shape list) and runs them through the same pipeline.
- Stroke-font text so titles are pen strokes. That way they lasso and scale together
  with the icon.
- The AWS 50-icon notebook, verified on the device.

## Non-goals (for now)

- Raster image → strokes (photos, scans). This is planned as the next step after the
  AWS notebook proves the pipeline. The SVG/shape core is designed so a tracing front
  end can plug in later.
- Reading or round-tripping the user's own notebooks, except for format calibration.
- Sync automation (cloud API, SSH, developer mode). Transfer stays manual.
- All ~800 AWS icons. We start with 50. The rest come later by request.

## Anti-goals (failure even if it "works")

- Output that the tablet shows as a PDF or image layer and that can't be edited
  stroke by stroke.
- Fills so dense that notebooks become sluggish to open, lasso or scale on the
  device. Be reasonable: when exact fill is too complex, simplify.
- Requiring developer mode. On the Paper Pro, enabling it factory-resets the device.
- Guessing format details silently. Anything not verified goes in the skill marked
  "unverified" until a device test confirms it.

## Constraints and known facts (from research)

- **Package:** `.rmdoc` is a zip notebook. It can be imported by **drag-and-drop into
  the reMarkable desktop app** (syncs via cloud) or via the **USB web interface**
  (http://10.11.99.1). drawj2d already produces `.rmdoc` for the Paper Pro this way,
  which proves the route works.
- **Pages:** v6 `.rm` files (firmware 3.x). The Python library **rmscene** (v0.8.x)
  reads them and has an experimental writer (`write_blocks`). It is used for
  round-trip tests and supports newer pens/colours.
- **Paper Pro colours** (per drawj2d): black, grey, white, blue, red, green, yellow,
  cyan, magenta, plus highlighter colours (yellow, green, pink, grey). Other colours
  must be mapped to the nearest palette entry. Unverified: whether arbitrary ARGB
  stroke colours are honoured (rmscene has `color_rgba` for highlights).
- **Paper Pro page** is about 179 × 239 mm on screen. Exact coordinate units/origin
  are unverified. They are believed to be the 1404 px wide reMarkable coordinate
  space with x centred, but the Paper Pro may differ.
- **Unverified, must be confirmed by reading rmscene source + a device test:** pen and
  colour enum values, point fields (x, y, speed, direction, width, pressure), the
  `.content`/`.metadata` JSON fields and file layout inside `.rmdoc`, the page
  coordinate system, and how many strokes per page stay responsive.

## Approaches considered (conversion of filled AWS icons)

| | Approach | Trade-off |
|-|-|-|
| A | Outlines only, category colour | Light, crisp, scales well. Loses the solid square look. |
| **B** | **Outlines + fill** ← **user's choice** | Closest to real icons. Risk of heavy files. Mitigated by "be reasonable" (below). |
| C | Let drawj2d convert | Fastest, but a black box. The skill would not learn the format. Used only as a cross-check. |

User picked **B, with the instruction to be reasonable when exact fill is too
complex.** Interpretation (Claude's proposal):
- The coloured background square/shape gets a fill. Preferred mechanism: a few wide
  **marker/shader strokes** if the device test shows they cover cleanly. Fallback:
  parallel hatching at moderate spacing, about 1–1.5 mm.
- The white glyph inside the icon is drawn as **outlines** with a fill gap (no
  hatching inside it), so it reads as white-on-colour.
- Tiny details below about 1 mm are dropped. Curves are flattened to polylines with a
  tolerance tuned so strokes stay smooth.
- Per-icon budget: aim for ≤ ~150 strokes per icon. If an icon exceeds it, simplify
  the fill first, then the details.
- **Category colours (Claude's call):** the calibration page tests whether exact AWS
  colours given as custom ARGB values show on the device. If they don't, each AWS
  category gets a *deliberately chosen, distinct* palette colour. We don't snap to the
  nearest colour, because that would merge categories. Example: compute = yellow,
  storage = green, database = blue, networking = magenta, integration = red,
  security = red with the black glyph kept, analytics = cyan, management = grey,
  AI/ML = cyan. Where two categories must share a colour, the category headings on
  the page keep them apart.
- **Icon list check (Claude's call):** names are matched against the current AWS
  asset package. Any icon missing from it is swapped for the next most common service
  in the same category, and the swap is reported.

## Decided "how"

- **Language/library:** Python 3 + rmscene (Claude's call; the user handed over the how).
- **Location:** this folder (`/Users/vesakankkunen/remarkable-pics`). Library in
  `rmdraw/`, skill in `.claude/skills/remarkable-native/`, outputs in `out/`.
- **Source icons:** AWS's official Architecture Icons asset package (SVG). AWS
  publishes it for customers drawing architecture diagrams.
- **Titles:** drawn as strokes with a single-stroke (Hershey-style) font, fineliner,
  black, centred under each icon. Claude's call: typed-text blocks in `.rm` can't be
  positioned freely per icon and wouldn't lasso with the icon.
- **Layout:** grid of icons grouped by category, with a category heading per group.
  Each icon is about 20 mm square with its title below. About 4 columns × 5–6 rows per
  page, so roughly 3 pages for 50 icons. A clear gap between cells so a lasso around
  one icon + title doesn't catch neighbours.

## Calibration step (learning the format "from scratch" where docs run out)

Before the 50-icon run:

1. Claude reads rmscene's source to pin down enums, point fields and the writer API.
   Claude documents each fact in the skill with its source.
2. Claude generates a **calibration notebook**: a page with every pen × colour,
   width steps, a ruler/grid showing the coordinate extents (corners and centre
   marked), a fill test (shader vs marker vs hatching), one stroke-font sample, and
   3 AWS icons.
3. The user imports it, checks it, and reports what looks wrong (with a photo if
   needed).
4. The user also exports **one reference page** they draw on the tablet, following
   Claude's instructions on exactly what to draw: a stroke in each pen/colour at a
   known position, e.g. touching each corner. Claude decodes it and compares it with
   what Claude writes. Any difference corrects the skill.
   - **The user has SSH access to the tablet** (developer mode is already on). The
     reference page's raw files are copied **read-only** from
     `/home/root/.local/share/remarkable/xochitl/` (`scp`), along with the matching
     `.content`/`.metadata`. This gives ground truth for the file layout and JSON
     fields too. The firmware version is read over SSH as well. Claude records it in
     the skill as the version the skill was verified against.
   - SSH is used only for **reading** in this round. Generated notebooks are still
     imported via the desktop app or the USB web interface, so nothing writes into
     xochitl's live data folder. Writing directly over SSH could be added later by
     request.

Only after that does the 50-icon notebook get generated.

## Proposed 50 icons (Claude's pick; user may edit)

Compute: EC2, Lambda, ECS, EKS, Fargate, Elastic Beanstalk, Lightsail, Batch, EC2 Auto Scaling
Containers: ECR
Storage: S3, EBS, EFS, S3 Glacier, Backup
Database: RDS, Aurora, DynamoDB, ElastiCache, Redshift, DocumentDB
Networking: VPC, CloudFront, Route 53, API Gateway, Elastic Load Balancing, Direct Connect, Transit Gateway
Integration: SQS, SNS, EventBridge, Step Functions, AppSync
Analytics: Kinesis Data Streams, Athena, Glue, EMR, OpenSearch Service
Security: IAM, Cognito, KMS, Secrets Manager, WAF, Shield
Management: CloudWatch, CloudFormation, CloudTrail, Systems Manager
AI/ML: SageMaker AI, Bedrock

## Success

- The notebook opens on the Paper Pro as a normal notebook. Every icon and title can
  be erased, lassoed, copied, moved and scaled.
- The icons are recognisable at a glance as their AWS service.
- Lasso and scale feel responsive.
- A fresh Claude session can read the skill and produce a new drawing (e.g. a fox)
  without redoing the research.

## Left to the builder

- Exact curve-flattening tolerance, hatch spacing, stroke widths. These are tuned
  from the calibration feedback.
- Stroke-font source (any public-domain single-stroke font, e.g. Hershey).
- `.content`/`.metadata` field details, determined from rmscene and the reference
  export.
- Internal module structure of `rmdraw/`.
