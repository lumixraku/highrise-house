"""Generate the apartment floor plan from the facade room-window module.

Run from this directory with ``python3 floor_plan.py``. The output is a
schematic SVG: one 4 m window forms one 4 m apartment bay.
"""

from pathlib import Path


PANE_W = 4.0
WINDOWS_LONG = 18
WINDOWS_SHORT = 7
PIER_LONG = 2.0
PIER_SHORT = 2.0
CORE_W, CORE_D = 20.0, 9.0
CORE_OFFSET = 18.0
W = WINDOWS_LONG * PANE_W + 2 * PIER_LONG
D = WINDOWS_SHORT * PANE_W + 2 * PIER_SHORT
OUT = Path(__file__).with_name("out") / "floor_plan.svg"
SCALE = 18
MARGIN_X = 155
MARGIN_Y = 125
VIEW_W = W * SCALE + 2 * MARGIN_X
VIEW_H = D * SCALE + 2 * MARGIN_Y


def sx(x):
    return MARGIN_X + (x + W / 2) * SCALE


def sy(y):
    return MARGIN_Y + (D / 2 - y) * SCALE


def rect(x, y, w, h, cls, label=""):
    attrs = (f'x="{sx(x):.1f}" y="{sy(y + h):.1f}" '
             f'width="{w * SCALE:.1f}" height="{h * SCALE:.1f}" class="{cls}"')
    title = f"<title>{label}</title>" if label else ""
    return f"<rect {attrs}>{title}</rect>"


def line(x1, y1, x2, y2, cls="line"):
    return (f'<line x1="{sx(x1):.1f}" y1="{sy(y1):.1f}" '
            f'x2="{sx(x2):.1f}" y2="{sy(y2):.1f}" class="{cls}" />')


def text(x, y, value, cls="label", anchor="middle", rotate=None):
    transform = (f' transform="rotate({rotate} {sx(x):.1f} {sy(y):.1f})"'
                 if rotate else "")
    return (f'<text x="{sx(x):.1f}" y="{sy(y):.1f}" class="{cls}" '
            f'text-anchor="{anchor}"{transform}>{value}</text>')


def dimension(x1, y1, x2, y2, value, label_offset=0.8):
    parts = [line(x1, y1, x2, y2, "dimension")]
    if y1 == y2:
        parts += [line(x1, y1 - 0.35, x1, y1 + 0.35, "dimension"),
                  line(x2, y2 - 0.35, x2, y2 + 0.35, "dimension"),
                  text((x1 + x2) / 2, y1 + label_offset, value,
                       "dimension-label")]
    else:
        parts += [line(x1 - 0.35, y1, x1 + 0.35, y1, "dimension"),
                  line(x2 - 0.35, y2, x2 + 0.35, y2, "dimension"),
                  text(x1 - label_offset, (y1 + y2) / 2, value,
                       "dimension-label", rotate=-90)]
    return "\n".join(parts)


def plan_svg():
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{VIEW_W:.0f}" height="{VIEW_H:.0f}" viewBox="0 0 {VIEW_W:.0f} {VIEW_H:.0f}">
<style>
  .paper {{ fill: #f5f1e8; }} .outer {{ fill: #e8e0d2; stroke: #17251f; stroke-width: 3; }}
  .room {{ fill: #fbf9f3; stroke: #66766b; stroke-width: 1.2; }}
  .core {{ fill: #203c34; stroke: #10231d; stroke-width: 2; }}
  .corridor {{ fill: #e3ece4; stroke: #7c9785; stroke-width: 1.2; stroke-dasharray: 5 4; }}
  .window {{ stroke: #82c7c2; stroke-width: 5; }} .pier {{ fill: #c7bbaa; }}
  .line {{ stroke: #66766b; stroke-width: 1; }} .dimension {{ stroke: #b36942; stroke-width: 1.2; fill: none; }}
  text {{ font-family: Georgia, 'Times New Roman', serif; fill: #17251f; }}
  .title {{ font-size: 25px; font-weight: bold; letter-spacing: 1px; }}
  .subtitle {{ font-size: 13px; fill: #607066; }} .label {{ font-size: 11px; }}
  .room-label {{ font-size: 10px; font-weight: bold; letter-spacing: .4px; }}
  .core-label {{ font-size: 11px; fill: #f5f1e8; font-weight: bold; }}
  .dimension-label {{ font-size: 11px; fill: #a04e2d; font-weight: bold; }}
  .note {{ font-size: 12px; fill: #607066; }}
</style>
<rect width="100%" height="100%" class="paper" />
{text(-W / 2, D / 2 + 5.1, "APARTMENT FLOOR PLAN", "title", "start")}
{text(-W / 2, D / 2 + 3.8, "TYPICAL RESIDENTIAL FLOOR · 1 WINDOW = 1 ROOM · WINDOW MODULE 4.00 m", "subtitle", "start")}
{rect(-W / 2, -D / 2, W, D, "outer")}
''']

    # Corners are their own 4 x 4 m turning rooms. The edge rooms stop at the
    # corner-room boundary; drawing independent full-length strips here would
    # double-fill the corner squares.
    room_no = 1
    corner_size = 4.0
    for x in (-W / 2, W / 2 - corner_size):
        for y in (-D / 2, D / 2 - corner_size):
            parts.append(rect(x, y, corner_size, corner_size, "corner-room",
                              f"Corner apartment {room_no}"))
            parts.append(text(x + 2, y + 2.4, f"C{room_no:02d}", "room-label"))
            room_no += 1

    for y in (D / 2 - 10, -D / 2):
        for i in range(WINDOWS_LONG):
            x = -W / 2 + PIER_LONG + i * PANE_W
            parts.append(rect(x, y, PANE_W, 10, "room", f"Apartment bay {room_no}"))
            parts.append(text(x + PANE_W / 2, y + 5.4, f"R{room_no:02d}", "room-label"))
            room_no += 1

    edge_y0 = -D / 2 + corner_size
    edge_height = D - 2 * corner_size
    for x in (-W / 2, W / 2 - 8):
        for i in range(int(edge_height // 4)):
            y = edge_y0 + i * 4
            parts.append(rect(x, y, 8, 4, "room", f"Apartment bay {room_no}"))
            parts.append(text(x + 4, y + 2.4, f"R{room_no:02d}", "room-label"))
            room_no += 1

    core_inner_edge = CORE_OFFSET - CORE_W / 2
    core_outer_edge = CORE_OFFSET + CORE_W / 2
    glazing_edge = W / 2 - PIER_LONG
    parts += [rect(-core_inner_edge, -6, 2 * core_inner_edge, 12, "corridor"),
              rect(-glazing_edge, -6, glazing_edge - core_outer_edge, 12, "corridor"),
              rect(core_outer_edge, -6, glazing_edge - core_outer_edge, 12, "corridor"),
              text(0, -0.6, "SHARED CORRIDOR", "label")]

    for cx, label in zip((-CORE_OFFSET, CORE_OFFSET), ("WEST CORE", "EAST CORE")):
        parts += [rect(cx - CORE_W / 2, -CORE_D / 2, CORE_W, CORE_D, "core", label),
                  text(cx, 0.7, label, "core-label"),
                  text(cx, -0.8, "LIFTS + STAIRS", "core-label")]

    parts += [rect(-W / 2, -D / 2, PIER_LONG, D, "pier"),
              rect(W / 2 - PIER_LONG, -D / 2, PIER_LONG, D, "pier"),
              rect(-W / 2, -D / 2, W, PIER_SHORT, "pier"),
              rect(-W / 2, D / 2 - PIER_SHORT, W, PIER_SHORT, "pier")]

    for i in range(WINDOWS_LONG):
        x = -W / 2 + PIER_LONG + (i + 0.5) * PANE_W
        parts += [line(x - 0.65, D / 2 + 0.05, x + 0.65, D / 2 + 0.05, "window"),
                  line(x - 0.65, -D / 2 - 0.05, x + 0.65, -D / 2 - 0.05, "window")]
    for i in range(WINDOWS_SHORT):
        y = -D / 2 + PIER_SHORT + (i + 0.5) * PANE_W
        parts += [line(-W / 2 - 0.05, y - 0.65, -W / 2 - 0.05, y + 0.65, "window"),
                  line(W / 2 + 0.05, y - 0.65, W / 2 + 0.05, y + 0.65, "window")]

    parts += [dimension(-W / 2, -D / 2 - 3.0, W / 2, -D / 2 - 3.0,
                        f"{W:.0f} m overall width", -0.9),
              dimension(W / 2 + 3.0, -D / 2, W / 2 + 3.0, D / 2,
                        f"{D:.0f} m overall depth", -0.9),
              dimension(-W / 2 + PIER_LONG, D / 2 + 1.8,
                        -W / 2 + PIER_LONG + 4, D / 2 + 1.8,
                         "4 m room window", 0.75),
              text(-W / 2, -D / 2 - 6.2,
                    f"{WINDOWS_LONG} rooms × 4 m on each long facade · {WINDOWS_SHORT} rooms × 4 m on each short facade",
                   "note", "start"),
              text(-W / 2, -D / 2 - 7.5,
                    "Blue marks = 4 m room windows · pale blocks = apartment bays · dark blocks = vertical circulation",
                   "note", "start"),
              "</svg>"]
    return "\n".join(parts)


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(plan_svg(), encoding="utf-8")
    print(f"saved -> {OUT}")
    print(f"derived footprint: {W:.0f} x {D:.0f} m")
    print(f"room rule: one {PANE_W:.0f} m window = one room bay")
