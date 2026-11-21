import pytest

from rmdraw.text import text_strokes


def _bbox(strokes):
    xs = [p[0] for s in strokes for p in s.points]
    ys = [p[1] for s in strokes for p in s.points]
    return min(xs), min(ys), max(xs), max(ys)


def test_text_produces_strokes_within_box():
    ss = text_strokes("Amazon EC2", 50, 10, 2.5, max_width_mm=22)
    assert ss
    x0, y0, x1, y1 = _bbox(ss)
    assert x0 >= 50 - 11 - 1e-6 and x1 <= 50 + 11 + 1e-6
    assert y0 >= 10 - 1e-6 and y1 <= 10 + 2.5 * 2.5 + 1e-6


def test_wraps_long_title():
    ss = text_strokes("AWS Elastic Load Balancing", 50, 10, 2.5, max_width_mm=22)
    x0, y0, x1, y1 = _bbox(ss)
    assert y1 - y0 > 2.5 * 1.5
    assert x1 - x0 <= 22 + 1e-6


def test_missing_glyph_becomes_space():
    with pytest.warns(UserWarning) as rec:
        ss = text_strokes("Café € – S3", 50, 10, 2.5)
    assert ss
    assert len(rec) == 1 and "€" in str(rec[0].message)


def test_accents_fold_to_base_letters():
    def pts(s):
        return [st.points for st in text_strokes(s, 50, 10, 2.5)]
    assert pts("Café – S3") == pts("Cafe – S3")


def test_strokes_are_joined():
    assert len(text_strokes("L", 0, 0, 5)) == 1


def test_empty_and_left_align():
    assert text_strokes("", 0, 0, 3) == []
    x0, _, _, _ = _bbox(text_strokes("Hi", 20, 0, 3, align="left"))
    assert x0 >= 20 - 1e-6
