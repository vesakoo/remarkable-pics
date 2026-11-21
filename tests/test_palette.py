from rmdraw.palette import AWS_CATEGORY_COLORS, FILL_ALPHA, to_pen_color


def test_fill_alpha_constant():
    assert FILL_ALPHA == 230


def test_aws_orange_maps_to_category_color():
    assert to_pen_color((255, 153, 0), "compute")[0] == "yellow"


def test_aws_orange_keeps_rgba():
    assert to_pen_color((255, 153, 0))[1] == (255, 153, 0, 230)


def test_nearest_palette_colour():
    assert to_pen_color((0, 0, 0))[0] == "black"
    assert to_pen_color((200, 60, 40))[0] == "red"
    assert to_pen_color((30, 160, 190))[0] == "cyan"
    assert to_pen_color((255, 153, 0))[0] == "yellow"


def test_white_never_returned():
    assert to_pen_color((255, 255, 255))[0] != "white"


def test_category_table():
    assert AWS_CATEGORY_COLORS == {
        "compute": "yellow", "storage": "green", "database": "blue",
        "networking": "magenta", "integration": "red", "security": "red",
        "analytics": "cyan", "management": "gray", "ai_ml": "cyan",
    }
    for cat, name in AWS_CATEGORY_COLORS.items():
        assert to_pen_color((1, 2, 3), cat)[0] == name
