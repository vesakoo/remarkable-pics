# Examples

**smiley.json**: an original smiling face in shapes JSON, and the worked example in the
`remarkable-native` skill. It has a 120 mm (r 60) yellow shader-filled circle with a bold black
outline, two black-filled eyes listed after the face so they cut their area out of its
fill, a 25°→155° smile arc, and a stroke-font caption. Build it with
`.venv/bin/rmdraw build examples/smiley.json -o out/smiley.rmdoc`.

**tree.json**: a simple original tree in shapes JSON. A green grass line with a few
tufts comes first. Then comes a tapered trunk, a closed polyline with a brown
`#8b5a2b` shader fill (the shader renders exact RGB), outlined in `red`, the nearest
pen palette colour to brown. Last is a canopy of four overlapping green-filled circles.
Each later circle hides the earlier ones where they overlap, and the canopy hides the
top of the trunk. Build it with `.venv/bin/rmdraw build examples/tree.json -o out/tree.rmdoc`.

**calibration.py**: builds `out/calibration.rmdoc`, the two-page notebook used to
calibrate the device. It has corner crosses and a 10 mm grid, a sample line for every
pen, shader bands at two alphas, and fill spacing and inset variants. The fill defaults
in `rmdraw.fill` come from viewing it on the tablet.

**aws_icons.py**: builds `out/aws-top50.rmdoc`, the 50 most-used AWS service icons
grouped by category, each with a stroke-font title under it. It needs the AWS
Architecture Icons package unzipped under `vendor/aws-icons/` (git-ignored). It is the
reference for icon sheets: `grid_layout`, `svg_to_shapes` per cell, a stroke budget per
icon, and raising the curve tolerance when an icon goes over budget.
