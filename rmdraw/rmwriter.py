"""Write a Page as a native v6 .rm scene (skeleton verified on device, see docs/format-notes.md)."""

import uuid
from typing import BinaryIO

import rmdraw  # noqa: F401  (installs the extended PenColor)
from rmscene import CrdtId, write_blocks
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_items import Group, Line, PenColor, Point
from rmscene.scene_stream import (
    AuthorIdsBlock,
    Block,
    MigrationInfoBlock,
    PageInfoBlock,
    SceneGroupItemBlock,
    SceneInfo,
    SceneLineItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
)
from rmscene.tagged_block_common import LwwValue

from .geometry import (
    COLOR_NAMES,
    PAGE_H_MM,
    PAGE_W_MM,
    PEN_NAMES,
    mm_to_units,
    width_to_device,
)
from .model import Page, Stroke

MAX_POINTS = 500
# Median pressure of the reference fineliner (device capture).
PRESSURE = 236


def _check(stroke: Stroke, idx: int) -> None:
    if len(stroke.points) < 1:
        raise ValueError(f"stroke {idx} has no points")
    for j, (x, y) in enumerate(stroke.points):
        if not (0 <= x <= PAGE_W_MM and 0 <= y <= PAGE_H_MM):
            raise ValueError(
                f"stroke {idx} point {j} ({x:.2f}, {y:.2f}) mm is outside the "
                f"page (0..{PAGE_W_MM:.1f}, 0..{PAGE_H_MM:.1f})"
            )


def _chunks(points: list) -> list[list]:
    if len(points) <= MAX_POINTS:
        return [points]
    out, i = [], 0
    while True:
        out.append(points[i : i + MAX_POINTS])
        if i + MAX_POINTS >= len(points):
            return out
        i += MAX_POINTS - 1  # overlap one point


def _color(stroke: Stroke) -> PenColor:
    if stroke.pen == "shader" or (
        stroke.rgba is not None and stroke.pen in ("highlighter", "shader")
    ):
        return PenColor.HIGHLIGHT
    return COLOR_NAMES[stroke.color]


def _lines(stroke: Stroke) -> list[Line]:
    scale, width = width_to_device(stroke.pen, stroke.width_mm)
    pts = [
        Point(*mm_to_units(x, y), speed=0, direction=0, width=width, pressure=PRESSURE)
        for x, y in stroke.points
    ]
    return [
        Line(
            color=_color(stroke),
            tool=PEN_NAMES[stroke.pen],
            points=chunk,
            thickness_scale=scale,
            starting_length=0.0,
            color_rgba=tuple(stroke.rgba) if stroke.rgba is not None else None,
        )
        for chunk in _chunks(pts)
    ]


def page_blocks(page: Page) -> list[Block]:
    for i, s in enumerate(page.strokes):
        _check(s, i)
    blocks: list[Block] = [
        AuthorIdsBlock(author_uuids={1: uuid.uuid4()}),
        MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True),
        PageInfoBlock(
            loads_count=1,
            merges_count=0,
            text_chars_count=0,
            text_lines_count=0,
            type_folio_use_count=0,
        ),
        SceneInfo(
            current_layer=LwwValue(timestamp=CrdtId(0, 0), value=CrdtId(0, 0)),
            background_visible=LwwValue(timestamp=CrdtId(0, 0), value=True),
            root_document_visible=LwwValue(timestamp=CrdtId(0, 0), value=True),
            paper_size=(1620, 2160),
        ),
        SceneTreeBlock(
            tree_id=CrdtId(0, 11),
            node_id=CrdtId(0, 0),
            is_update=True,
            parent_id=CrdtId(0, 1),
        ),
        TreeNodeBlock(Group(node_id=CrdtId(0, 1))),
        TreeNodeBlock(
            Group(
                node_id=CrdtId(0, 11),
                label=LwwValue(timestamp=CrdtId(0, 12), value="Layer 1"),
            )
        ),
        SceneGroupItemBlock(
            parent_id=CrdtId(0, 1),
            item=CrdtSequenceItem(
                item_id=CrdtId(0, 13),
                left_id=CrdtId(0, 0),
                right_id=CrdtId(0, 0),
                deleted_length=0,
                value=CrdtId(0, 11),
            ),
        ),
    ]
    prev = CrdtId(0, 0)
    n = 0
    for s in page.strokes:
        for line in _lines(s):
            item_id = CrdtId(1, 100 + n)
            n += 1
            blocks.append(
                SceneLineItemBlock(
                    parent_id=CrdtId(0, 11),
                    item=CrdtSequenceItem(
                        item_id=item_id,
                        left_id=prev,
                        right_id=CrdtId(0, 0),
                        deleted_length=0,
                        value=line,
                    ),
                )
            )
            prev = item_id
    return blocks


def write_page(page: Page, out: BinaryIO) -> None:
    write_blocks(out, page_blocks(page), options={"version": "3.2.2"})
