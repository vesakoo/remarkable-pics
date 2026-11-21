"""Build out/drawings/aws-architecture/: a simple serverless web app drawn with the AWS icons.

Users -> CloudFront -> S3 (static frontend); Users -> API Gateway (+ Cognito auth)
-> Lambda -> DynamoDB / S3 uploads, with logs to CloudWatch.
Needs the AWS Architecture Icons package under vendor/aws-icons/ (see aws_icons.py).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aws_icons import VENDOR, find_icon, icon_strokes  # noqa: E402
from rmdraw.model import Document, Page, Stroke  # noqa: E402
from rmdraw.text import text_strokes  # noqa: E402

NAME = "AWS Architecture – Serverless web app"
ICON = 22.0
TITLE_H = 2.8
NOTE_H = 2.4

# service -> (icon match, centre x, top y, caption under the title or None)
NODES = {
    "cloudfront": ("Arch_Amazon-CloudFront_48", "Amazon CloudFront", 40, 62, "CDN"),
    "cognito": ("Arch_Amazon-Cognito_48", "Amazon Cognito", 90, 62, "sign-in"),
    "apigw": ("Arch_Amazon-API-Gateway_48", "Amazon API Gateway", 140, 62, "REST API"),
    "s3web": ("Simple-Storage-Service_48", "Amazon S3", 40, 114, "web app (HTML/JS)"),
    "watch": ("Arch_Amazon-CloudWatch_48", "Amazon CloudWatch", 90, 114, "monitoring"),
    "lambda": ("Arch_AWS-Lambda_48", "AWS Lambda", 140, 114, "business logic"),
    "s3up": ("Simple-Storage-Service_48", "Amazon S3", 90, 168, "user uploads"),
    "dynamo": ("Arch_Amazon-DynamoDB_48", "Amazon DynamoDB", 140, 168, "data"),
}


def rounded(x, y, w, h, r, n=6):
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [pts[0]]


def arrow(a, b, dashed=False, color="black", width=0.5, head=2.6):
    (x0, y0), (x1, y1) = a, b
    ang = math.atan2(y1 - y0, x1 - x0)
    st = []
    if dashed:
        length = math.dist(a, b)
        on, off, t = 2.0, 1.5, 0.0
        while t < length:
            t1 = min(t + on, length)
            st.append(Stroke([(x0 + math.cos(ang) * t, y0 + math.sin(ang) * t),
                              (x0 + math.cos(ang) * t1, y0 + math.sin(ang) * t1)],
                             color=color, width_mm=width))
            t = t1 + off
    else:
        st.append(Stroke([a, b], color=color, width_mm=width))
    for side in (-1, 1):
        ah = ang + math.pi - side * math.radians(25)
        st.append(Stroke([b, (x1 + head * math.cos(ah), y1 + head * math.sin(ah))],
                         color=color, width_mm=width))
    return st


def label(s, x, y, align="center"):
    return text_strokes(s, x, y, NOTE_H, align=align, color="blue")


def person(cx, top):
    head = [(cx + 3 * math.cos(2 * math.pi * i / 24), top + 3 + 3 * math.sin(2 * math.pi * i / 24))
            for i in range(25)]
    w = 0.5
    return [Stroke(head, width_mm=w),
            Stroke([(cx, top + 6), (cx, top + 13)], width_mm=w),
            Stroke([(cx - 4, top + 8.5), (cx + 4, top + 8.5)], width_mm=w),
            Stroke([(cx - 3.5, top + 18), (cx, top + 13), (cx + 3.5, top + 18)], width_mm=w)]


def build() -> Document:
    st = text_strokes("Serverless web app on AWS", 90, 10, 5.5)
    # users
    for dx in (-6, 6):
        st += person(90 + dx, 20)
    st += text_strokes("Users (browser / mobile)", 90, 40, TITLE_H)
    # AWS cloud boundary
    st.append(Stroke(rounded(10, 49, 160, 158, 4), color="gray", width_mm=0.5))
    st += text_strokes("AWS Cloud", 14, 52, 3.2, align="left", color="gray")

    port = {}
    for key, (match, title, cx, top, note) in NODES.items():
        box = (cx - ICON / 2, top, ICON, ICON)
        icon, _ = icon_strokes(find_icon(match), box)
        st += icon
        st += text_strokes(title, cx, top + ICON + 2, TITLE_H, max_width_mm=44)
        if note:
            st += text_strokes(note, cx, top + ICON + 6.5, NOTE_H, color="gray")
        port[key] = {"top": (cx, top - 1.5), "bottom": (cx, top + ICON + 11),
                     "left": (cx - ICON / 2 - 1.5, top + ICON / 2),
                     "right": (cx + ICON / 2 + 1.5, top + ICON / 2)}

    p = port
    st += arrow((84, 45), p["cloudfront"]["top"])
    st += label("1 HTTPS", 66, 57)
    st += arrow((96, 45), p["apigw"]["top"])
    st += label("2 HTTPS /api", 112, 58)
    st += arrow(p["apigw"]["left"], p["cognito"]["right"])
    st += label("3 verify", 115, 69)
    st += arrow(p["cloudfront"]["bottom"], p["s3web"]["top"])
    st += label("static files", 42, 103, align="left")
    st += arrow(p["apigw"]["bottom"], p["lambda"]["top"])
    st += label("4 invoke", 142, 103, align="left")
    st += arrow(p["lambda"]["bottom"], p["dynamo"]["top"])
    st += label("5 read / write", 142, 157, align="left")
    st += arrow((p["lambda"]["bottom"][0] - 8, p["lambda"]["bottom"][1]),
                (p["s3up"]["top"][0] + 9, p["s3up"]["top"][1]))
    st += label("files", 120, 157, align="left")
    st += arrow(p["lambda"]["left"], p["watch"]["right"], dashed=True, color="gray")
    st += label("logs", 115, 121)
    st += text_strokes("Drawn with rmdraw + Claude - every line is editable ink", 90, 212, 2.6,
                       color="gray")
    return Document(NAME, [Page(st)])


if __name__ == "__main__":
    if not VENDOR.exists():
        sys.exit(f"missing {VENDOR}")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from build_gallery import OUT, publish
    publish(build(), OUT / "drawings" / "aws-architecture", "aws-architecture")
