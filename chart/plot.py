#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Generate standalone SVG vector charts (bar, line, scatter, pie) from CSV or JSON data.
#: when=Use when the user wants to visualize data, plot metrics, create a chart, or generate an SVG graph from numbers.
#: network=none
#: stdin=buffer
#: param=data:file:d=CSV or JSON data file mounted at /input/data
#: param=data_text:d=Inline CSV or JSON text (or pipe stdin)
#: param=type:default=bar:d=Chart type: bar, line, scatter, pie
#: param=title:default=:d=Chart title displayed at the top
#: param=x:d=Field name or 1-indexed column for X axis / labels
#: param=y:d=Field name or 1-indexed column for Y axis / values
#: param=width:default=800:d=SVG viewport width in pixels
#: param=height:default=500:d=SVG viewport height in pixels
#: output=chart.svg
import csv
import io
import json
import math
import os
import sys

source_path = os.environ.get("DATA", "")
inline_text = os.environ.get("DATA_TEXT", "")
chart_type = os.environ["TYPE"].strip().lower()
title = os.environ["TITLE"].strip()
x_spec = os.environ.get("X", "").strip()
y_spec = os.environ.get("Y", "").strip()
w_raw = os.environ["WIDTH"].strip()
h_raw = os.environ["HEIGHT"].strip()

try:
    width = int(w_raw)
    height = int(h_raw)
    if width <= 100 or height <= 100:
        raise ValueError
except ValueError:
    print(f"Error: width and height must be integers > 100 (got {w_raw}x{h_raw})", file=sys.stderr)
    sys.exit(1)

if chart_type not in ("bar", "line", "scatter", "pie"):
    print(f"Error: unsupported chart type '{chart_type}' (expected bar, line, scatter, pie)", file=sys.stderr)
    sys.exit(1)

raw_content = ""
if source_path and os.path.exists(source_path):
    with open(source_path, "r", encoding="utf-8", errors="replace") as f:
        raw_content = f.read()
elif inline_text:
    raw_content = inline_text
elif not sys.stdin.isatty():
    raw_content = sys.stdin.read()

if not raw_content.strip():
    print("Error: No data provided via data, data_text, or stdin", file=sys.stderr)
    sys.exit(1)

records = []
# Try JSON first
is_json = False
try:
    parsed = json.loads(raw_content)
    if isinstance(parsed, list):
        if parsed and isinstance(parsed[0], dict):
            records = parsed
            is_json = True
        elif parsed and isinstance(parsed[0], list):
            headers = [f"col_{i+1}" for i in range(len(parsed[0]))]
            records = [dict(zip(headers, r)) for r in parsed]
            is_json = True
except Exception:
    pass

if not is_json:
    # CSV parser
    try:
        sample = raw_content[:4096]
        delim = ","
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except Exception:
            delim = ","
        reader = csv.reader(io.StringIO(raw_content), delimiter=delim)
        header_row = next(reader, None)
        if not header_row:
            print("Error: empty CSV data", file=sys.stderr)
            sys.exit(1)
        headers = [h.strip() or f"col_{i+1}" for i, h in enumerate(header_row)]
        for r in reader:
            if not any(c.strip() for c in r):
                continue
            padded = r + [""] * (len(headers) - len(r))
            records.append(dict(zip(headers, padded[:len(headers)])))
    except Exception as e:
        print(f"Error parsing CSV data: {e}", file=sys.stderr)
        sys.exit(1)

if not records:
    print("Error: no data records found to plot", file=sys.stderr)
    sys.exit(1)

available_cols = list(records[0].keys())

# Resolve X column
x_col = available_cols[0]
if x_spec:
    if x_spec.isdigit() and 1 <= int(x_spec) <= len(available_cols):
        x_col = available_cols[int(x_spec) - 1]
    elif x_spec in available_cols:
        x_col = x_spec
    else:
        print(f"Error: X column '{x_spec}' not found in {available_cols}", file=sys.stderr)
        sys.exit(1)

# Resolve Y column
y_col = None
if y_spec:
    if y_spec.isdigit() and 1 <= int(y_spec) <= len(available_cols):
        y_col = available_cols[int(y_spec) - 1]
    elif y_spec in available_cols:
        y_col = y_spec
    else:
        print(f"Error: Y column '{y_spec}' not found in {available_cols}", file=sys.stderr)
        sys.exit(1)

if not y_col:
    # Pick first numeric column that is not x_col
    for col in available_cols:
        if col == x_col and len(available_cols) > 1:
            continue
        try:
            for r in records[:5]:
                float(str(r[col]).replace(",", "").strip())
            y_col = col
            break
        except Exception:
            continue
    if not y_col:
        y_col = available_cols[1] if len(available_cols) > 1 else available_cols[0]

PALETTE = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#6366f1", "#14b8a6",
]

# Extract points
x_labels = []
y_values = []
for r in records:
    x_val = str(r.get(x_col, "")).strip()
    raw_y = str(r.get(y_col, "")).replace(",", "").strip()
    try:
        y_num = float(raw_y)
    except ValueError:
        y_num = 0.0
    x_labels.append(x_val)
    y_values.append(y_num)

margin_top = 60 if title else 40
margin_bottom = 60
margin_left = 70
margin_right = 40
plot_w = width - margin_left - margin_right
plot_h = height - margin_top - margin_bottom


def escape_xml(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def nice_ticks(val_min, val_max, tick_count=5):
    if val_min == val_max:
        val_min -= 1
        val_max += 1
    val_min = min(0.0, val_min)
    span = val_max - val_min
    rough_step = span / tick_count
    magnitude = 10 ** math.floor(math.log10(rough_step or 1))
    residual = rough_step / magnitude
    if residual <= 1.5:
        step = 1 * magnitude
    elif residual <= 3:
        step = 2 * magnitude
    elif residual <= 7:
        step = 5 * magnitude
    else:
        step = 10 * magnitude
    t_min = math.floor(val_min / step) * step
    t_max = math.ceil(val_max / step) * step
    ticks = []
    curr = t_min
    while curr <= t_max + (step * 0.5):
        ticks.append(round(curr, 6))
        curr += step
    return ticks, t_min, t_max


svg_parts = []
svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
svg_parts.append('<style>')
svg_parts.append('  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }')
svg_parts.append('  .bg { fill: #ffffff; }')
svg_parts.append('  .grid { stroke: #e5e7eb; stroke-width: 1; stroke-dasharray: 3 3; }')
svg_parts.append('  .axis { stroke: #9ca3af; stroke-width: 1.5; }')
svg_parts.append('  .tick-text { font-size: 11px; fill: #6b7280; text-anchor: end; }')
svg_parts.append('  .x-text { font-size: 11px; fill: #6b7280; text-anchor: middle; }')
svg_parts.append('  .title { font-size: 18px; font-weight: 600; fill: #111827; text-anchor: middle; }')
svg_parts.append('  .val-label { font-size: 10px; font-weight: 500; fill: #374151; text-anchor: middle; }')
svg_parts.append('</style>')
svg_parts.append(f'<rect width="{width}" height="{height}" class="bg"/>')

if title:
    svg_parts.append(f'<text x="{width / 2}" y="32" class="title">{escape_xml(title)}</text>')

if chart_type in ("bar", "line", "scatter"):
    ticks, y_min, y_max = nice_ticks(min(y_values or [0]), max(y_values or [1]))
    y_range = (y_max - y_min) or 1.0

    def scale_y(v):
        return margin_top + plot_h - ((v - y_min) / y_range * plot_h)

    # Gridlines and Y ticks
    for t in ticks:
        ty = scale_y(t)
        svg_parts.append(f'<line x1="{margin_left}" y1="{ty}" x2="{margin_left + plot_w}" y2="{ty}" class="grid"/>')
        lbl = f"{t:g}"
        svg_parts.append(f'<text x="{margin_left - 8}" y="{ty + 4}" class="tick-text">{lbl}</text>')

    # Axis lines
    zero_y = scale_y(0.0) if y_min <= 0 <= y_max else (margin_top + plot_h)
    svg_parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" class="axis"/>')
    svg_parts.append(f'<line x1="{margin_left}" y1="{zero_y}" x2="{margin_left + plot_w}" y2="{zero_y}" class="axis"/>')

    n = len(y_values)
    if chart_type == "bar":
        slot_w = plot_w / n
        bar_w = min(slot_w * 0.7, 60)
        for i, (lx, vy) in enumerate(zip(x_labels, y_values)):
            cx = margin_left + (i + 0.5) * slot_w
            bx = cx - bar_w / 2
            by = scale_y(max(0.0, vy))
            b_bottom = scale_y(min(0.0, vy))
            bh = abs(b_bottom - by)
            color = PALETTE[i % len(PALETTE)]
            svg_parts.append(f'<rect x="{bx}" y="{by}" width="{bar_w}" height="{max(bh, 1)}" fill="{color}" rx="3"/>')
            # Bar value text
            v_text_y = by - 4 if vy >= 0 else b_bottom + 12
            svg_parts.append(f'<text x="{cx}" y="{v_text_y}" class="val-label">{vy:g}</text>')
            # X label
            svg_parts.append(f'<text x="{cx}" y="{margin_top + plot_h + 18}" class="x-text">{escape_xml(lx)}</text>')

    elif chart_type == "line":
        slot_w = plot_w / max(n - 1, 1)
        points = []
        for i, (lx, vy) in enumerate(zip(x_labels, y_values)):
            cx = margin_left + i * slot_w
            cy = scale_y(vy)
            points.append((cx, cy))
            svg_parts.append(f'<text x="{cx}" y="{margin_top + plot_h + 18}" class="x-text">{escape_xml(lx)}</text>')

        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        svg_parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{PALETTE[0]}" stroke-width="2.5" stroke-linejoin="round"/>')
        for cx, cy in points:
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{PALETTE[0]}" stroke="#ffffff" stroke-width="1.5"/>')

    elif chart_type == "scatter":
        # Check if X is numeric
        x_nums = []
        all_numeric = True
        for lx in x_labels:
            try:
                x_nums.append(float(lx))
            except ValueError:
                all_numeric = False
                break
        if all_numeric and len(x_nums) == n:
            x_min = min(x_nums)
            x_max = max(x_nums)
            x_span = (x_max - x_min) or 1.0
            def scale_x(v):
                return margin_left + ((v - x_min) / x_span * plot_w)
            for xv, yv in zip(x_nums, y_values):
                cx = scale_x(xv)
                cy = scale_y(yv)
                svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{PALETTE[0]}" fill-opacity="0.8" stroke="#ffffff" stroke-width="1"/>')
        else:
            slot_w = plot_w / n
            for i, (lx, vy) in enumerate(zip(x_labels, y_values)):
                cx = margin_left + (i + 0.5) * slot_w
                cy = scale_y(vy)
                svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{PALETTE[0]}" fill-opacity="0.8" stroke="#ffffff" stroke-width="1"/>')
                svg_parts.append(f'<text x="{cx}" y="{margin_top + plot_h + 18}" class="x-text">{escape_xml(lx)}</text>')

elif chart_type == "pie":
    cx = width / 2 - 80
    cy = margin_top + plot_h / 2
    radius = min(plot_w, plot_h) / 2 - 20
    total = sum(max(0.0, v) for v in y_values) or 1.0

    current_angle = -math.pi / 2
    legend_x = cx + radius + 40
    legend_y = margin_top + 20

    for i, (lx, vy) in enumerate(zip(x_labels, y_values)):
        val = max(0.0, vy)
        slice_angle = (val / total) * 2 * math.pi
        x1 = cx + radius * math.cos(current_angle)
        y1 = cy + radius * math.sin(current_angle)
        x2 = cx + radius * math.cos(current_angle + slice_angle)
        y2 = cy + radius * math.sin(current_angle + slice_angle)

        large_arc = 1 if slice_angle > math.pi else 0
        color = PALETTE[i % len(PALETTE)]

        path_d = f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
        svg_parts.append(f'<path d="{path_d}" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        current_angle += slice_angle

        # Legend item
        pct = (val / total) * 100
        ly = legend_y + i * 22
        if ly < height - 20:
            svg_parts.append(f'<rect x="{legend_x}" y="{ly - 10}" width="12" height="12" fill="{color}" rx="2"/>')
            svg_parts.append(f'<text x="{legend_x + 18}" y="{ly}" font-size="11" fill="#374151">{escape_xml(lx)} ({pct:.1f}%)</text>')

svg_parts.append('</svg>\n')
svg_output = "\n".join(svg_parts)

out_dir = "/output" if os.path.exists("/output") else "."
out_path = os.path.join(out_dir, "chart.svg")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg_output)

file_size = os.path.getsize(out_path)
print(f"Rendered {chart_type} chart ({width}x{height}, {file_size:,} bytes) -> chart.svg")
