# Gallery — ready-to-import reMarkable notebooks

Every `.rmdoc` here is a native notebook for the **reMarkable Paper Pro**: real pen
strokes you can erase, lasso, move, copy and scale. Download one and **drag it into the
reMarkable desktop app**; it syncs to the tablet (restart the tablet if it doesn't show up).

Rebuild everything with `.venv/bin/python tools/build_gallery.py` (the AWS sheet needs the
icon package, see below). PNGs are previews rendered from the written strokes; files in
`tablet/` are the tablet's own renderings.

## ⭐ AWS architecture icons — top 50

[`aws-icons/aws-icons-top50.rmdoc`](aws-icons/aws-icons-top50.rmdoc) · 4 pages · 50 icons ·
~5 000 strokes. Each icon is a coloured, outlined shape with its name handwritten underneath,
grouped by category. Lasso an icon and its title, copy it into your own notes and scale it
— instant hand-drawn architecture diagrams.

| Compute & Storage | Database & Networking |
|---|---|
| ![AWS icons page 1](aws-icons/aws-icons-top50-p1.png) | ![AWS icons page 2](aws-icons/aws-icons-top50-p2.png) |
| **Integration & Analytics** | **Security, Management & ML** |
| ![AWS icons page 3](aws-icons/aws-icons-top50-p3.png) | ![AWS icons page 4](aws-icons/aws-icons-top50-p4.png) |

On the tablet (page 1, an earlier build): [`aws-icons/tablet/aws-icons-p1-tablet.png`](aws-icons/tablet/aws-icons-p1-tablet.png)

Source: [`examples/aws_icons.py`](../examples/aws_icons.py) with
[`data/aws_top50.json`](../data/aws_top50.json). It needs the official
[AWS Architecture Icons](https://aws.amazon.com/architecture/icons/) package unzipped under
`vendor/aws-icons/`. The icons are © Amazon Web Services and are used under AWS's terms for
architecture diagrams.

## Quantum circuit symbols

[`symbols/quantum-gates/quantum-gates.rmdoc`](symbols/quantum-gates/quantum-gates.rmdoc) · 15 pages.
Page 1: single-qubit gate tiles (H X Y Z S T SX B I P, S† T† SX†, RX RY RZ U M, reset, barrier) and
multi-qubit gates (CX, CZ, CCX/Toffoli, CXC, SWAP, CSWAP/Fredkin, iSWAP, √SWAP), plus loose control
dots, targets and connectors to build any controlled gate. Pages 2–5: gate matrices, hand-lettered
(single-qubit, rotations P/RX/RY/RZ/U, two-qubit 4×4, Toffoli and Fredkin 8×8). Page 6: kets and bras for
0, 1, +, −, i+, i−, the Bell states β00–β11 and ready In/Out boxes. Pages 7–8: state vectors (one qubit, general |ψ⟩, two-qubit basis,
Bell states). Page 9: six Bloch spheres
from different angles, state vector left empty to draw by hand. Pages 10–15: empty circuit
templates for 1–6 qubits. Tiles are sized to the template wires, so lasso → copy → paste fits.

| Gates | Gate matrices | States | Bloch spheres | 3-qubit template |
|---|---|---|---|---|
| ![gates](symbols/quantum-gates/quantum-gates-p1.png) | ![matrices](symbols/quantum-gates/quantum-gates-p2.png) | ![states](symbols/quantum-gates/quantum-gates-p6.png) | ![bloch](symbols/quantum-gates/quantum-gates-p9.png) | ![circuit](symbols/quantum-gates/quantum-gates-p12.png) |

Source: [`examples/quantum_gates.py`](../examples/quantum_gates.py)

## Presentation doodles

[`symbols/doodles/doodles.rmdoc`](symbols/doodles/doodles.rmdoc) · 4 pages · sketchnote style with
a light hand-drawn wobble. Page 1: people (standing, waving, cheering, pointing, thinking,
shrugging, walking, big idea, question, presenting, at the desk, team) and seven faces. Page 2:
20 arrows (curved, loop, cycle, block, branch/merge, spiral, growth, process chevrons, marker…).
Page 3: speech, thought, shout and whisper bubbles, dialogue, banner, sticky note, frames, scroll,
tag, numbered list, highlights, braces and dividers. Page 4: 30 idea icons (light bulb, gear,
rocket, target, trophy, chart, calendar, lock, flag, puzzle, globe, megaphone, hourglass…).

| People | Arrows | Bubbles & frames | Idea icons |
|---|---|---|---|
| ![people](symbols/doodles/doodles-p1.png) | ![arrows](symbols/doodles/doodles-p2.png) | ![bubbles](symbols/doodles/doodles-p3.png) | ![icons](symbols/doodles/doodles-p4.png) |

Source: [`examples/doodles.py`](../examples/doodles.py)

## Drawings

| | Notebook | Made from | Strokes |
|---|---|---|---|
| <img src="drawings/aws-architecture/aws-architecture.png" width="160"> | [aws-architecture.rmdoc](drawings/aws-architecture/aws-architecture.rmdoc) | [examples/aws_architecture.py](../examples/aws_architecture.py) | 1259 |
| <img src="drawings/owl-coloring/owl-coloring.png" width="160"> | [owl-coloring.rmdoc](drawings/owl-coloring/owl-coloring.rmdoc) — a coloring page: outlines only, colour it in on the tablet | [examples/owl_coloring.json](../examples/owl_coloring.json) | 87 |
| <img src="drawings/owl/owl.png" width="160"> | [owl.rmdoc](drawings/owl/owl.rmdoc) | [examples/owl.json](../examples/owl.json) | 799 |
| <img src="drawings/fox/fox.png" width="160"> | [fox.rmdoc](drawings/fox/fox.rmdoc) · [on tablet](drawings/fox/tablet/fox-tablet.png) | [examples/fox.json](../examples/fox.json) | 235 |
| <img src="drawings/smiley/smiley.png" width="160"> | [smiley.rmdoc](drawings/smiley/smiley.rmdoc) | [examples/smiley.json](../examples/smiley.json) | 175 |
| <img src="drawings/tree/tree.png" width="160"> | [tree.rmdoc](drawings/tree/tree.rmdoc) | [examples/tree.json](../examples/tree.json) | 246 |

## Calibration

Test pages used to learn how the tablet renders pens and fills.

| | Notebook | What it tests |
|---|---|---|
| <img src="calibration/pens-and-fills-p1.png" width="160"> | [pens-and-fills.rmdoc](calibration/pens-and-fills.rmdoc) | page corners and a 10 mm grid, every pen, shader colours and alpha, icon fill variants ([on tablet](calibration/tablet/pens-and-fills-p1-tablet.png)) |
| <img src="calibration/fill-swatches.png" width="160"> | [fill-swatches.rmdoc](calibration/fill-swatches.rmdoc) | fill band spacing × overlap, and three oranges |

## Layout

```
out/
├── aws-icons/      aws-icons-top50.rmdoc, page previews, tablet/
├── symbols/        other symbol libraries (quantum-gates/, doodles/)
├── drawings/<name>/<name>.rmdoc + <name>.png (+ tablet/)
├── calibration/    test notebooks
└── *.*             anything loose here is scratch (git-ignored)
```
