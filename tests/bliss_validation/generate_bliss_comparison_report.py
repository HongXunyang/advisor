#!/usr/bin/env python3
"""Write bliss_ub_comparison_report.html: ADVISOR vs BLISS UB-matrix comparison.

Run from any directory:
    python3 tests/bliss_validation/generate_bliss_comparison_report.py

Loads `test_bliss_ub_comparison.py` for the CSV loader, frame rotation,
tolerances and metrics, and runs its actual checks (`run_all_checks`): the
report's verdict, check count and conclusion are derived from those results,
and a failing check is listed in the report and makes this script exit 1.
The output is a single self-contained HTML file (inline CSS/SVG/JS).
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import math
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np

spec = importlib.util.spec_from_file_location("bliss_cmp", HERE / "test_bliss_ub_comparison.py")
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)

OUTPUT = HERE / "bliss_ub_comparison_report.html"
SHOWCASE_LINES = (37, 2)  # worst Kabsch gap (monoclinic) and a typical cubic case
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"


def crystal_system(lat):
    a, b, c, al, be, ga = (lat[k] for k in ("a", "b", "c", "alpha", "beta", "gamma"))
    right = all(abs(x - 90) < 1e-9 for x in (al, be, ga))
    if right and abs(a - b) < 1e-9 and abs(b - c) < 1e-9:
        return "cubic"
    if right and abs(a - b) < 1e-9:
        return "tetragonal"
    if right:
        return "orthorhombic"
    if abs(al - 90) < 1e-9 and abs(ga - 90) < 1e-9:
        return "monoclinic"
    return "triclinic"


def last_digit_units(case, raw_row, ub_bl):
    """|ADVISOR BL - BLISS| for each entry, in units of the last decimal
    supplied for that BLISS value (precision varies from 5 to 9 decimals)."""
    col = cmp.HEADER.index("u11")
    units = []
    for k, (value, text) in enumerate(zip(ub_bl.ravel(), raw_row[col:col + 9])):
        decimals = len(text.strip().split(".")[1]) if "." in text else 0
        units.append((abs(value - float(text)) * 10 ** decimals, case["line"], cmp.BLISS_COLUMNS[k], text.strip(), decimals))
    return units


def analyse():
    rows = []
    raw_by_line = {line: row for line, row in enumerate(cmp.RAW_ROWS[1:], start=2)}
    for case in cmp.CASES:
        kabsch = cmp.fit(case, cmp.FIT_METHOD_KABSCH)
        bl = cmp.fit(case, cmp.FIT_METHOD_BUSING_LEVY)
        ub_k = cmp.BLISS_FROM_ADVISOR @ kabsch.UB
        ub_bl = cmp.BLISS_FROM_ADVISOR @ bl.UB
        rows.append({
            "line": case["line"],
            "system": crystal_system(case["lattice"]),
            "lattice": case["lattice"],
            "energy": case["energy_keV"],
            "hkl": [tuple(int(m[k]) if float(m[k]).is_integer() else m[k] for k in "HKL")
                    for m in case["measurements"]],
            "csv_dev": float(np.abs(kabsch.UB - case["ub_advisor"]).max()),
            "k_dev": float(np.abs(ub_k - case["ub_bliss"]).max()),
            "k_mis": cmp.misorientation_deg(ub_k, case["ub_bliss"]),
            "bl_dev": float(np.abs(ub_bl - case["ub_bliss"]).max()),
            "bl_mis": cmp.misorientation_deg(ub_bl, case["ub_bliss"]),
            "mismatch": cmp.interreflection_angle_mismatch_deg(case),
            "units": last_digit_units(case, raw_by_line[case["line"]], ub_bl),
            "ub_k": ub_k, "ub_bl": ub_bl, "ub_bliss": case["ub_bliss"],
            "measurements": case["measurements"],
        })
    return rows


def sci(x, digits=1):
    if x == 0:
        return "0"
    exp = int(math.floor(math.log10(abs(x))))
    mant = x / 10 ** exp
    return f"{mant:.{digits}f}×10<sup>{exp}</sup>"


def matrix_html(m, fmt="{:+.8f}"):
    cells = "".join("<tr>" + "".join(f"<td>{fmt.format(v)}</td>" for v in row) + "</tr>" for row in m)
    return f'<table class="matrix"><tbody>{cells}</tbody></table>'


# ---------------------------------------------------------------- SVG figures

def marker(marker_id, css_class):
    """Arrowhead in user units, coloured by CSS class (WebKit ignores
    fill="context-stroke", which would otherwise draw it black)."""
    return (f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" markerHeight="10" '
            f'markerUnits="userSpaceOnUse" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" class="{css_class}"/></marker>')


def axes_svg(title, axes, note, program):
    """Top view of the scattering plane; z points out of the page in both.
    axes: list of (label, dx, dy) unit directions in screen coords (y down)."""
    cx, cy, r = 130, 155, 70
    parts = [f'<svg viewBox="0 0 260 270" role="img" aria-label="{html.escape(title)}">',
             f'<defs>{marker(f"ah-{program}", f"mk-{program}")}{marker(f"ah-beam-{program}", "mk-beam")}</defs>',
             f'<text x="130" y="20" class="svg-title" text-anchor="middle">{html.escape(title)}</text>',
             # beam: enters from the bottom, travels up the page through the sample
             f'<line x1="{cx}" y1="262" x2="{cx}" y2="{cy + 14}" class="beam" marker-end="url(#ah-beam-{program})"/>',
             f'<text x="{cx + 8}" y="250" class="svg-muted">incident beam</text>',
             f'<circle cx="{cx}" cy="{cy}" r="9" class="sample"/>',
             f'<circle cx="{cx}" cy="{cy}" r="2.5" class="zdot"/>']
    for label, dx, dy in axes:
        x2, y2 = cx + dx * r, cy + dy * r
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" class="axis {program}-axis" marker-end="url(#ah-{program})"/>')
        lx, ly = cx + dx * (r + 18), cy + dy * (r + 18) + 5
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="axis-label {program}-axis" text-anchor="middle">{label}</text>')
    parts.append(f'<text x="{cx + 14}" y="{cy + 24}" class="svg-muted">z ⊙ (up)</text>')
    parts.append(f'<text x="130" y="44" class="svg-muted" text-anchor="middle">{html.escape(note)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def methods_svg():
    """Schematic: measured q1, q2 (solid) vs rotated lattice vectors U·g1,
    U·g2 (dashed) when the lattice angle between them is too small by Δ."""
    def panel(x0, title, g1_off, g2_off, caption):
        o = (x0 + 40, 180)
        L = 130
        def vec(angle_deg):
            a = math.radians(angle_deg)
            return o[0] + L * math.cos(a), o[1] - L * math.sin(a)
        q1, q2 = 20, 75
        p = [f'<text x="{x0 + 130}" y="22" class="svg-title" text-anchor="middle">{title}</text>']
        for (q_ang, q_lab), (g_ang, g_lab) in (((q1, "q₁"), (q1 + g1_off, "U·g₁")),
                                               ((q2, "q₂"), (q2 + g2_off, "U·g₂"))):
            for ang, cls in ((q_ang, "vec-q"), (g_ang, "vec-g")):
                x, y = vec(ang)
                p.append(f'<line x1="{o[0]}" y1="{o[1]}" x2="{x:.1f}" y2="{y:.1f}" class="{cls}" marker-end="url(#ah-{cls})"/>')
            if abs(q_ang - g_ang) < 0.5:  # coincident: one shared label
                labels = [(q_ang, f"{q_lab} = {g_lab}", "start", 10)]
            else:  # the vector at the larger angle is labelled on its left, the other on its right
                hi, lo = sorted(((q_ang, q_lab), (g_ang, g_lab)), reverse=True)
                labels = [(hi[0], hi[1], "end", -8), (lo[0], lo[1], "start", 8)]
            for ang, text, anchor, dx in labels:
                x, y = vec(ang)
                p.append(f'<text x="{x + dx:.1f}" y="{y + 4:.1f}" class="vec-label" text-anchor="{anchor}">{text}</text>')
        p.append(f'<circle cx="{o[0]}" cy="{o[1]}" r="3" class="zdot"/>')
        p.append(f'<text x="{x0 + 130}" y="212" class="svg-muted" text-anchor="middle">{caption}</text>')
        return "".join(p)

    return ('<svg viewBox="0 0 560 222" role="img" aria-label="Busing–Levy versus Kabsch schematic">'
            f'<defs>{marker("ah-vec-q", "mk-q")}{marker("ah-vec-g", "mk-g")}</defs>'
            + panel(0, "Busing–Levy (BLISS)", 0, -12, "q₁ matched exactly; full Δ on reflection 2")
            + panel(290, "Kabsch (least squares)", 6, -6, "error Δ split between both reflections")
            + "</svg>")


def dot_chart(rows):
    """Per-case max |ΔUB| vs BLISS, log scale, both ADVISOR methods."""
    W, H, ml, mr, mt, mb = 760, 300, 78, 16, 16, 44
    lo, hi = -10, -1
    n = len(rows)
    def x(i):
        return ml + (i + 0.5) * (W - ml - mr) / n
    def y(v):
        lv = min(max(math.log10(max(v, 10 ** lo)), lo), hi)
        return mt + (hi - lv) / (hi - lo) * (H - mt - mb)
    p = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
         'aria-label="Maximum UB element difference from BLISS per case, log scale">']
    for e in range(lo, hi + 1):
        yy = y(10 ** e)
        p.append(f'<line x1="{ml}" x2="{W - mr}" y1="{yy:.1f}" y2="{yy:.1f}" class="grid"/>')
        p.append(f'<text x="{ml - 8}" y="{yy + 4:.1f}" class="tick" text-anchor="end">10<tspan dy="-6" font-size="9">{e}</tspan></text>')
    # Kabsch label above its line, Busing-Levy label below (clear of the dots).
    for tol, label, dy in ((cmp.KABSCH_ATOL, "Kabsch tolerance 0.02", -5),
                           (cmp.BUSING_LEVY_ATOL, "Busing–Levy tolerance 10⁻⁶", 14)):
        yy = y(tol)
        p.append(f'<line x1="{ml}" x2="{W - mr}" y1="{yy:.1f}" y2="{yy:.1f}" class="tol"/>')
        p.append(f'<text x="{W - mr - 4}" y="{yy + dy:.1f}" class="tol-label" text-anchor="end">{label}</text>')
    for i, r in enumerate(rows):
        if i % 5 == 0 or i == n - 1:
            p.append(f'<text x="{x(i):.1f}" y="{H - mb + 16}" class="tick" text-anchor="middle">{r["line"]}</text>')
    p.append(f'<text x="{(ml + W - mr) / 2}" y="{H - 6}" class="tick" text-anchor="middle">CSV line</text>')
    ymid = (mt + H - mb) / 2
    p.append(f'<text x="14" y="{ymid:.1f}" class="tick" text-anchor="middle" transform="rotate(-90 14 {ymid:.1f})">'
             'max |ADVISOR − BLISS| (Å⁻¹)</text>')
    for i, r in enumerate(rows):
        tip = (f'Line {r["line"]} · {r["system"]}|Kabsch: {r["k_dev"]:.2e} Å⁻¹ ({r["k_mis"]:.3f}°)'
               f'|Busing–Levy: {r["bl_dev"]:.2e} Å⁻¹')
        for key, cls in (("k_dev", "s1"), ("bl_dev", "s2")):
            p.append(f'<circle cx="{x(i):.1f}" cy="{y(r[key]):.1f}" r="4.5" class="dot {cls}" data-tip="{html.escape(tip)}"/>')
        p.append(f'<rect x="{x(i) - 9:.1f}" y="{mt}" width="18" height="{H - mt - mb}" class="hit" data-tip="{html.escape(tip)}"/>')
    p.append("</svg>")
    return "".join(p)


def scatter_chart(rows):
    """Kabsch–BLISS misorientation vs |inter-reflection angle mismatch|."""
    W, H, ml, mr, mt, mb = 760, 300, 78, 16, 16, 44
    xmax = 1.0
    def x(v):
        return ml + v / xmax * (W - ml - mr)
    def y(v):
        return mt + (1 - v / xmax) * (H - mt - mb)
    p = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
         'aria-label="Kabsch versus BLISS misorientation against reflection-angle mismatch">']
    for t in np.arange(0, 1.01, 0.2):
        p.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/>')
        p.append(f'<text x="{ml - 8}" y="{y(t) + 4:.1f}" class="tick" text-anchor="end">{t:.1f}°</text>')
        p.append(f'<text x="{x(t):.1f}" y="{H - mb + 16}" class="tick" text-anchor="middle">{t:.1f}°</text>')
    p.append(f'<line x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}" class="tol"/>')
    p.append(f'<text x="{x(0.62):.1f}" y="{y(0.66):.1f}" class="tol-label" text-anchor="end">bound: misorientation = |Δ|</text>')
    p.append(f'<text x="{(ml + W - mr) / 2}" y="{H - 6}" class="tick" text-anchor="middle">'
             '|lattice-predicted − measured angle between reflections 1 and 2|</text>')
    ymid = (mt + H - mb) / 2
    p.append(f'<text x="14" y="{ymid:.1f}" class="tick" text-anchor="middle" transform="rotate(-90 14 {ymid:.1f})">'
             'ADVISOR Kabsch vs BLISS misorientation</text>')
    for r in rows:
        tip = (f'Line {r["line"]} · {r["system"]}|mismatch Δ = {r["mismatch"]:+.3f}°'
               f'|Kabsch misorientation = {r["k_mis"]:.3f}°')
        p.append(f'<circle cx="{x(abs(r["mismatch"])):.1f}" cy="{y(r["k_mis"]):.1f}" r="5" class="dot s1" data-tip="{html.escape(tip)}"/>')
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------- page

CSS = """
:root{--bg:#fcfcfb;--surface:#ffffff;--text:#0b0b0b;--text-2:#52514e;--muted:#7a7974;--border:#e4e3df;
--grid:#ecebe7;--accent:#2a78d6;--s1:#2a78d6;--s2:#eb6834;--good:#1f7a3a;--warn:#9a6700;--code:#f4f3f0;--adv:#0b7a75;--bliss:#5b3fc4;--heat:#e34948;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--surface:#1a1a19;--text:#ffffff;
--text-2:#c3c2b7;--muted:#8f8e86;--border:#33332f;--grid:#2a2a27;--accent:#3987e5;--s1:#3987e5;--s2:#d95926;
--good:#5cc27a;--warn:#e0a63a;--code:#22221f;--adv:#3cc4b8;--bliss:#a18ff0;--heat:#e66767;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141413;--surface:#1a1a19;--text:#ffffff;--text-2:#c3c2b7;--muted:#8f8e86;--border:#33332f;
--grid:#2a2a27;--accent:#3987e5;--s1:#3987e5;--s2:#d95926;--good:#5cc27a;--warn:#e0a63a;--code:#22221f;--adv:#3cc4b8;--bliss:#a18ff0;--heat:#e66767;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 80px}
h1{font-size:28px;line-height:1.2;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:19px;margin:44px 0 10px;padding-top:4px;border-top:1px solid var(--border);padding-top:24px}
h3{font-size:15px;margin:22px 0 6px}
p,li{color:var(--text)} .sub{color:var(--text-2);margin:0 0 24px}
.muted{color:var(--muted)} small{color:var(--text-2)}
code,.mono,.matrix td{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
code{background:var(--code);padding:1px 5px;border-radius:4px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:20px 0}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.tile .label{color:var(--text-2);font-size:13px}.tile .value{font-size:24px;font-weight:600;margin-top:2px}
.tile .note{color:var(--muted);font-size:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin:14px 0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:640px){.two{grid-template-columns:1fr}}
svg{width:100%;height:auto;display:block}
.svg-title{font-size:14px;font-weight:600;fill:var(--text)} .svg-muted{font-size:11px;fill:var(--muted)}
.axis{stroke:var(--text);stroke-width:2} .axis-label{font-size:14px;font-weight:600;fill:var(--text)}
.beam{stroke:var(--s2);stroke-width:2.5} .sample{fill:var(--surface);stroke:var(--text-2);stroke-width:1.5}
.zdot{fill:var(--text)}
.vec-q{stroke:var(--text);stroke-width:2} .vec-g{stroke:var(--s1);stroke-width:2;stroke-dasharray:6 4}
.vec-label{font-size:12px;fill:var(--text)}
.mk-adv{fill:var(--adv)} .mk-bliss{fill:var(--bliss)} .mk-beam{fill:var(--s2)} .mk-q{fill:var(--text)} .mk-g{fill:var(--s1)}
.frame svg{max-width:300px;margin:0 auto}
.chart .grid{stroke:var(--grid);stroke-width:1} .chart .tick{font-size:11px;fill:var(--muted)}
.chart .tol{stroke:var(--text-2);stroke-width:1} .chart .tol-label{font-size:11px;fill:var(--text-2)}
.dot{stroke:var(--surface);stroke-width:2} .dot.s1{fill:var(--s1)} .dot.s2{fill:var(--s2)}
.hit{fill:transparent} .hit:hover{fill:var(--grid);fill-opacity:.5}
.legend{display:flex;gap:18px;font-size:13px;color:var(--text-2);margin:4px 0 8px;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface)}
table.data{border-collapse:collapse;width:100%;font-size:13px}
table.data th,table.data td{padding:6px 8px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--grid)}
table.data th{color:var(--text-2);font-weight:600;position:sticky;top:0;background:var(--surface)}
table.data td:first-child,table.data th:first-child,table.data td.l,table.data th.l{text-align:left}
table.data .hl{background:color-mix(in srgb,var(--adv) 8%,transparent)}
table.data td.hl{color:var(--text);font-weight:600}
table.data tr.groups th{font-size:12px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);text-align:center}
table.data tr.groups th.l{text-align:left} table.data tr.groups th.hl{color:var(--text)}
table.data th{vertical-align:bottom}
table.data th .unit{display:block;font-weight:400;font-size:11px;color:var(--muted)}
.colguide dl{display:grid;grid-template-columns:minmax(140px,210px) 1fr;gap:6px 16px;margin:10px 0;font-size:14px}
.colguide dt{font-weight:600} .colguide dd{margin:0;color:var(--text-2)} .colguide p{margin:10px 0 0;font-size:14px}
@media (max-width:640px){.colguide dl{grid-template-columns:1fr} .colguide dd{margin-bottom:6px}}
table.matrix{border-collapse:collapse;margin:6px 0;border-left:2px solid var(--text-2);border-right:2px solid var(--text-2)}
table.matrix td{padding:2px 10px;text-align:right}
.card.fail{border-color:var(--warn)}
.pass{color:var(--good);font-weight:600}.warn{color:var(--warn);font-weight:600}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--text);border:1px solid var(--border);
border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.12);display:none;max-width:280px;z-index:10}
#tip b{display:block;margin-bottom:2px}
/* program names: colour + weight, so identity never rests on colour alone */
.adv{color:var(--adv);font-weight:650} .bliss{color:var(--bliss);font-weight:650}
tspan.adv{fill:var(--adv);font-weight:650} tspan.bliss{fill:var(--bliss);font-weight:650}
.axis.adv-axis{stroke:var(--adv)} .axis.bliss-axis{stroke:var(--bliss)}
.axis-label.adv-axis{fill:var(--adv)} .axis-label.bliss-axis{fill:var(--bliss)}
nav.toc{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--border);
margin:0 -16px 8px;padding:8px 16px;display:flex;gap:4px 14px;flex-wrap:wrap;font-size:13px}
nav.toc a{color:var(--text-2);text-decoration:none} nav.toc a:hover{color:var(--text);text-decoration:underline}
h2{scroll-margin-top:52px}
.algo{border-left:3px solid var(--adv)} .algo p{margin:6px 0} .katex-display{margin:8px 0;overflow-x:auto;overflow-y:hidden}
.mstack{display:grid;grid-template-columns:minmax(150px,max-content) max-content;gap:10px 22px;align-items:center;
background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:8px 0;overflow-x:auto}
.mstack .mlabel{font-size:13px;font-weight:600} .mnote{font-size:12px;font-weight:400;color:var(--text-2);margin-top:2px}
@media (max-width:560px){.mstack{grid-template-columns:1fr}}
table.matrix td.h{border-radius:3px}
.heatkey{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);margin:6px 0 2px}
.heatkey .bar{width:140px;height:10px;border-radius:5px;
background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--heat) 55%,transparent));border:1px solid var(--border)}
table.data th.sortable{cursor:pointer;user-select:none} table.data th.sortable:hover{color:var(--text)}
table.data th.sortable::after{content:" ↕";color:var(--muted);font-weight:400}
table.data th[aria-sort="ascending"]::after{content:" ↑";color:var(--text)}
table.data th[aria-sort="descending"]::after{content:" ↓";color:var(--text)}
pre.cmd{background:var(--code);border-radius:8px;padding:10px 12px;overflow-x:auto;font-size:13px;margin:8px 0}
dl.prov{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;font-size:13px;margin:8px 0 0}
dl.prov dt{color:var(--text-2)} dl.prov dd{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all}
@media print{
  :root,:root:not([data-theme="light"]),:root[data-theme="dark"]{--bg:#fff;--surface:#fff;--text:#000;--text-2:#444;
  --muted:#666;--border:#ccc;--grid:#e6e6e6;--code:#f3f3f3;--adv:#0b7a75;--bliss:#5b3fc4;--heat:#e34948;--s1:#2a78d6;--s2:#eb6834;color-scheme:light}
  nav.toc,#tip{display:none} main{max-width:none;padding:0}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .card,.tile,.mstack,svg,pre,table.matrix{break-inside:avoid} h2,h3{break-after:avoid}
  .tablewrap{overflow:visible;border:0} table.data th{position:static}
}
"""

JS = r"""
const tip=document.getElementById('tip');
const brand=t=>t.replace(/\b(ADVISOR|BLISS)\b/g,m=>'<span class="'+(m==='BLISS'?'bliss':'adv')+'">'+m+'</span>');
document.querySelectorAll('[data-tip]').forEach(el=>{
  el.addEventListener('mousemove',e=>{const [h,...rest]=el.dataset.tip.split('|');
    tip.innerHTML=brand('<b>'+h+'</b>'+rest.join('<br>'));tip.style.display='block';
    const x=Math.min(e.clientX+14,window.innerWidth-300);tip.style.left=x+'px';tip.style.top=(e.clientY+14)+'px';});
  el.addEventListener('mouseleave',()=>{tip.style.display='none'});
});
// Sortable per-case table: numeric columns sort on data-v, text columns on their text.
document.querySelectorAll('table.data.sortable-table').forEach(table=>{
  const heads=[...table.tHead.rows[table.tHead.rows.length-1].cells];
  heads.forEach((th,col)=>{
    th.classList.add('sortable');th.tabIndex=0;
    const sort=()=>{
      const asc=th.getAttribute('aria-sort')!=='ascending';
      heads.forEach(h=>h.removeAttribute('aria-sort'));th.setAttribute('aria-sort',asc?'ascending':'descending');
      const key=r=>{const c=r.cells[col];return c.dataset.v!==undefined?parseFloat(c.dataset.v):c.textContent;};
      const rows=[...table.tBodies[0].rows].sort((a,b)=>{const x=key(a),y=key(b);
        return (typeof x==='number'?x-y:String(x).localeCompare(String(y)))*(asc?1:-1);});
      rows.forEach(r=>table.tBodies[0].appendChild(r));
    };
    th.addEventListener('click',sort);th.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();sort();}});
  });
});
"""

# Rendered by KaTeX (auto-render) when online; the TeX source stays readable offline.
ALGORITHM_HTML = r"""
<div class="card algo" id="algorithm">
<b>How the UB matrix is computed</b>
<p>For each reflection \(i\) with Miller indices \(\mathbf h_i\), ADVISOR builds the lattice vector and the measured
scattering vector in the sample (φ-axis) frame:</p>
$$\mathbf g_i = B\,\mathbf h_i,\qquad
\mathbf q_i = R(\theta_i,\chi_i,\phi_i)^{\mathsf T}\,\mathbf Q^{\text{lab}}_i,\qquad
R = R_z(\theta)\,R_y(\chi)\,R_x(\phi),$$
<p>where the columns of \(B\) are \(\mathbf a^*,\mathbf b^*,\mathbf c^*\) (with the factor \(2\pi\)), and
\(\mathbf Q^{\text{lab}} = k\,(-\sin 2\theta,\ \cos 2\theta-1,\ 0)\) with \(k = 2\pi/\lambda\).
Both methods then find a rotation \(U\) with \(\mathbf q_i \approx U\mathbf g_i\) and report \(UB = U\,B\).</p>
<p><b>Busing–Levy</b> (ADVISOR default, and what BLISS uses). Reflection 1 is matched exactly, and reflection 2 fixes
the rotation about it:</p>
$$T(\mathbf a,\mathbf b) = \big[\,\hat{\mathbf a},\ \hat{\mathbf t}\times\hat{\mathbf a},\ \hat{\mathbf t}\,\big],\quad
\hat{\mathbf t} = \frac{\mathbf a\times\mathbf b}{\lVert\mathbf a\times\mathbf b\rVert},\qquad
U = T(\mathbf q_1,\mathbf q_2)\;T(\mathbf g_1,\mathbf g_2)^{\mathsf T}.$$
<p><b>Kabsch</b> (ADVISOR option). A least-squares fit over all reflections, solved by SVD:</p>
$$U = \arg\min_{U\in SO(3)}\sum_i \lVert \mathbf q_i - U\mathbf g_i\rVert^2:\qquad
\sum_i \mathbf g_i\mathbf q_i^{\mathsf T} = W\Sigma V^{\mathsf T},\quad
U = V\,\mathrm{diag}\!\big(1,1,\det VW^{\mathsf T}\big)\,W^{\mathsf T}.$$
<p>BLISS applies the same Busing–Levy construction in its own lab frame, so
<span class="mono">UB<sub>BLISS</sub> = P·UB<sub>ADVISOR</sub></span>, with P given in section 1.</p>
</div>
"""


_NAME = re.compile(r"\b(ADVISOR|BLISS)\b")
_SKIP = {"script", "style", "title", "code", "pre"}


def colorize_names(page):
    """Wrap every visible ADVISOR/BLISS in a coloured span (tspan inside SVG).
    Text inside script/style/title/code/pre and inside tag attributes is left alone."""
    out, skip, svg = [], [], 0
    for part in re.split(r"(<[^>]+>)", page):
        if part.startswith("<"):
            tag = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
            name = tag.group(1).lower() if tag else ""
            closing, selfclosing = part.startswith("</"), part.endswith("/>")
            if name in _SKIP and not selfclosing:
                skip.append(name) if not closing else (skip.pop() if skip and skip[-1] == name else None)
            if name == "svg" and not selfclosing:
                svg += -1 if closing else 1
            out.append(part)
        elif skip or not part:
            out.append(part)
        else:
            wrap = "tspan" if svg else "span"
            out.append(_NAME.sub(lambda m: f'<{wrap} class="{"bliss" if m.group(1) == "BLISS" else "adv"}">'
                                           f'{m.group(1)}</{wrap}>', part))
    return "".join(out)


def heat_matrix(m, reference=None, fmt="{:+.8f}", texts=None):
    """3x3 matrix; when a reference is given, tint each cell by |m - reference|
    on a log scale from 1e-9 (no tint) to 1e-2 (strongest). `texts` (row-major
    strings) overrides the formatted numbers, e.g. to show CSV values verbatim."""
    rows_html = []
    for i in range(3):
        cells = []
        for j in range(3):
            style, title = "", ""
            if reference is not None:
                d = abs(m[i, j] - reference[i, j])
                f = min(max((math.log10(max(d, 1e-12)) + 9) / 7, 0.0), 1.0)
                style = f' style="background:color-mix(in srgb,var(--heat) {55 * f:.0f}%,transparent)"'
                title = f' title="|Δ| = {d:.2e} Å⁻¹"'
            shown = texts[3 * i + j] if texts else fmt.format(m[i, j])
            cells.append(f'<td class="h"{style}{title}>{shown}</td>')
        rows_html.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="matrix"><tbody>{"".join(rows_html)}</tbody></table>'


def showcase_html(rows):
    """Explicit matrices for a few rows: ADVISOR Kabsch, ADVISOR Busing-Levy and
    BLISS, all in the BLISS lab frame (ADVISOR matrices multiplied by P)."""
    by_line = {r["line"]: r for r in rows}
    raw_by_line = {line: row for line, row in enumerate(cmp.RAW_ROWS[1:], start=2)}
    col = cmp.HEADER.index("u11")
    blocks = []
    for line in SHOWCASE_LINES:
        r = by_line.get(line)
        if r is None:
            continue
        lat = r["lattice"]
        refl = " and ".join(
            "(" + " ".join(f"{m[k]:g}" for k in "HKL") + f") at 2θ = {m['tth']:g}°" for m in r["measurements"])
        lattice_txt = (f'a, b, c = {lat["a"]:g}, {lat["b"]:g}, {lat["c"]:g} Å; '
                       f'α, β, γ = {lat["alpha"]:g}, {lat["beta"]:g}, {lat["gamma"]:g}°')
        blocks.append(f"""
<h3>CSV line {line} · {r["system"]}, {r["energy"]:g} keV</h3>
<p class="muted" style="margin:0">{lattice_txt}. Reflections {refl}. Reflection-angle mismatch Δ = {r["mismatch"]:+.3f}°.</p>
<div class="mstack">
<div class="mlabel">ADVISOR · Kabsch<div class="mnote">max |Δ| = {r["k_dev"]:.2e} Å⁻¹<br>misorientation {r["k_mis"]:.3f}°</div></div>
{heat_matrix(r["ub_k"], r["ub_bliss"])}
<div class="mlabel">ADVISOR · Busing–Levy<div class="mnote">max |Δ| = {r["bl_dev"]:.2e} Å⁻¹<br>misorientation {angle_txt(r["bl_mis"])}</div></div>
{heat_matrix(r["ub_bl"], r["ub_bliss"])}
<div class="mlabel">BLISS (reference)<div class="mnote">verbatim from the CSV</div></div>
{heat_matrix(r["ub_bliss"], texts=[t if t.startswith("-") else "+" + t
                                   for t in (x.strip() for x in raw_by_line[line][col:col + 9])])}
</div>""")
    return "".join(blocks)


def angle_txt(deg):
    return "< 10⁻⁶°" if deg < 1e-6 else f"{deg:.1e}°"


def provenance():
    """Commit and input hash, so a reader can tie the report to exact inputs."""
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True,
                                  timeout=10).stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"
    dirty = git("status", "--porcelain", "--untracked-files=no")
    commit = git("rev-parse", "--short", "HEAD") + (" (with uncommitted changes)" if dirty not in ("", "unknown") else "")
    return {
        "Generated": date.today().isoformat(),
        "Git commit": commit,
        "CSV": f"tests/bliss_validation/{cmp.CSV_PATH.name}",
        "CSV SHA-256": hashlib.sha256(cmp.CSV_PATH.read_bytes()).hexdigest(),
    }


def build(rows, outcomes):
    n = len(rows)
    failures = [o for o in outcomes if o[2] is not None]
    n_checks, n_failed = len(outcomes), len(failures)
    passed = n_failed == 0
    failed_names = {name for name, _, _ in failures}

    def holds(check_name):
        return "holds for all rows" if check_name not in failed_names else "<span class='warn'>FAILS</span>"

    all_units = [u for r in rows for u in r["units"]]
    worst_unit = max(all_units)
    over_half = [u for u in all_units if u[0] > 0.5]
    decimals = sorted({u[4] for u in all_units})
    if failures:
        fail_items = "".join(
            f"<li><code>{html.escape(name)}</code>{'' if line is None else f' — CSV line {line}'}: "
            f"{html.escape(msg)}</li>" for name, line, msg in failures[:50])
        verdict_html = (f'<div class="card fail"><b>Validation FAILED: {n_failed} of {n_checks} checks.</b>'
                        f'<ul>{fail_items}</ul>'
                        + ('<p>… more failures not shown.</p>' if n_failed > 50 else '') + '</div>')
    else:
        verdict_html = ""
    systems = {}
    for r in rows:
        systems[r["system"]] = systems.get(r["system"], 0) + 1
    systems_txt = ", ".join(f"{v} {k}" for k, v in sorted(systems.items(), key=lambda kv: -kv[1]))
    max_bl = max(r["bl_dev"] for r in rows)
    max_k = max(r["k_dev"] for r in rows)
    max_kmis = max(r["k_mis"] for r in rows)
    max_csv = max(r["csv_dev"] for r in rows)
    worst = max(rows, key=lambda r: r["k_mis"])
    example = cmp.CASES[0]
    ex_k = cmp.fit(example, cmp.FIT_METHOD_KABSCH).UB

    def angle_cell(deg):
        # arccos-based angles can't resolve below ~1e-6 deg (float64 rounding of the trace)
        shown = f"{deg:.3f}" if deg >= 1e-3 else (f"{deg:.1e}" if deg >= 1e-6 else "&lt; 10⁻⁶")
        return f'<td class="hl" data-v="{deg}">{shown}</td>'

    table_rows = []
    for r in rows:
        lat = r["lattice"]
        lattice_tip = (f'a, b, c = {lat["a"]:g}, {lat["b"]:g}, {lat["c"]:g} Å; '
                       f'α, β, γ = {lat["alpha"]:g}, {lat["beta"]:g}, {lat["gamma"]:g}°; E = {r["energy"]:g} keV')
        hkl = " / ".join("(" + " ".join(f"{v:g}" for v in h) + ")" for h in r["hkl"])
        table_rows.append(
            f'<tr><td data-v="{r["line"]}">{r["line"]}</td>'
            f'<td class="l" title="{lattice_tip}">{r["system"]}</td><td class="l">{hkl}</td>'
            f'<td data-v="{abs(r["mismatch"])}">{r["mismatch"]:+.3f}</td>'
            f'<td class="hl" data-v="{r["bl_dev"]}">{r["bl_dev"]:.1e}</td>'
            f'<td class="hl" data-v="{r["k_dev"]}">{r["k_dev"]:.1e}</td>'
            + angle_cell(r["bl_mis"]) + angle_cell(r["k_mis"]) + "</tr>")

    tol_rows = [
        ("ADVISOR (Kabsch, current code) vs ADVISOR values in CSV", "1×10<sup>−9</sup> Å⁻¹",
         sci(max_csv), "Only floating-point noise is expected; confirms the CSV was produced by this code."),
        ("ADVISOR Busing–Levy vs BLISS, element-wise", "1×10<sup>−6</sup> Å⁻¹", sci(max_bl),
         f"BLISS values were supplied with {decimals[0]}–{decimals[-1]} decimals, so the reference itself is only good to "
         "about 10<sup>−7</sup>–10<sup>−9</sup>. 10<sup>−6</sup> stays clear of that, yet is about 10<sup>4</sup>× below the "
         "Kabsch–BLISS gap, so an algorithm or convention difference could not pass."),
        ("ADVISOR Kabsch vs BLISS, element-wise", "0.02 Å⁻¹", sci(max_k),
         "Methods legitimately differ on inconsistent data; set just under 2× the worst observed case."),
        ("ADVISOR Kabsch vs BLISS, misorientation", "1.0°", f"{max_kmis:.3f}°",
         "Same reasoning, in angle. A tighter, data-driven check follows."),
        ("Kabsch vs BLISS misorientation vs reflection-angle mismatch |Δ|", "misorientation ≤ |Δ| + 10<sup>−4</sup>°",
         holds("check_kabsch_close_to_bliss_and_gap_explained"), "Physical bound: the two methods coincide when Δ = 0."),
        ("Convention: best signed permutation", "P unique; runner-up ≥ 10× worse",
         holds("check_convention_is_unique_signed_permutation"),
         "Searched all 48 signed permutations independently for each row."),
    ]
    tol_html = "".join(f"<tr><td class='l'>{a}</td><td>{b}</td><td>{c}</td><td class='l' style='white-space:normal'>{d}</td></tr>"
                       for a, b, c, d in tol_rows)

    conclusion_html = conclusion(rows, outcomes, max_bl, max_kmis)
    advisor_axes = axes_svg("ADVISOR lab frame", [("X", 1, 0), ("Y", 0, -1)], "beam along +Y", "adv")
    bliss_axes = axes_svg("BLISS lab frame", [("x", 0, -1), ("y", -1, 0)], "beam along +x", "bliss")
    prov = "".join(f"<dt>{k}</dt><dd>{html.escape(v)}</dd>" for k, v in provenance().items())
    nav = ('<nav class="toc" aria-label="Contents">'
           + "".join(f'<a href="#{anchor}">{label}</a>' for anchor, label in (
               ("intro", "Introduction"), ("algorithm", "Algorithm"), ("convention", "1 · Convention"),
               ("methods", "2 · Methods"), ("tolerances", "3 · Tolerances"), ("results", "4 · Results"),
               ("reproduce", "5 · Reproduce"), ("conclusion", "6 · Conclusion")))
           + "</nav>")
    katex = (f'<link rel="stylesheet" href="{KATEX}/katex.min.css">'
             f'<script defer src="{KATEX}/katex.min.js"></script>'
             f'<script defer src="{KATEX}/contrib/auto-render.min.js" onload="renderMathInElement(document.body,'
             "{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\\\(',right:'\\\\)',display:false}],"
             'throwOnError:false})"></script>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ADVISOR vs BLISS UB</title>{katex}<style>{CSS}</style></head>
<body><main>
<h1>ADVISOR vs BLISS: UB-matrix validation</h1>
<p class="sub">ESRF ID20 · {n} orientation determinations · generated {date.today().isoformat()} by
<code>generate_bliss_comparison_report.py</code></p>
{nav}
<h2 id="intro" style="border-top:0;padding-top:0">Introduction</h2>
<p>ADVISOR determines the crystal orientation matrix <b>UB</b> from two measured Bragg reflections. To
validate it against the software used at the beamline, a beamline scientist at ESRF ID20 ran the same
{n} two-reflection cases through <b>BLISS</b> ({systems_txt} crystals, 7.5–13.5 keV). Each row of
<code>bliss_ub_test.csv</code> holds the inputs (energy, lattice, two reflections with
θ, χ, φ, 2θ), ADVISOR's UB (<code>UB_ij</code>, computed with ADVISOR's original Kabsch method) and
BLISS's UB (<code>uij</code>). This report establishes the convention mapping between the two programs,
quantifies the residual discrepancy, explains it, and documents the tolerances used in
<code>test_bliss_ub_comparison.py</code>.</p>
{ALGORITHM_HTML}
<div class="tiles">
<div class="tile"><div class="label">Frame convention</div><div class="value">1 rotation</div>
<div class="note">same P for all {n} rows</div></div>
<div class="tile"><div class="label">Busing–Levy vs BLISS (max)</div><div class="value">{max_bl:.1e}</div>
<div class="note">Å⁻¹, below the last supplied digit</div></div>
<div class="tile"><div class="label">Kabsch vs BLISS (max)</div><div class="value">{max_kmis:.2f}°</div>
<div class="note">misorientation, line {worst["line"]} ({worst["system"]})</div></div>
<div class="tile"><div class="label">Checks (run for this report)</div>
<div class="value {'pass' if passed else 'warn'}">{n_checks - n_failed} / {n_checks} pass</div>
<div class="note">same functions as the pytest suite</div></div>
</div>
{verdict_html}

<h2 id="convention">1 · Coordinate convention</h2>
<p>For every row, the BLISS matrix is ADVISOR's matrix with its <b>rows</b> rearranged:
<code>u1j = UB_2j</code>, <code>u2j = −UB_1j</code>, <code>u3j = UB_3j</code>. In matrix form</p>
<div class="two">
<div class="card"><b>UB<sub>BLISS</sub> = P · UB<sub>ADVISOR</sub></b>
{matrix_html(cmp.BLISS_FROM_ADVISOR, "{:+.0f}")}
<small>det P = +1: a −90° rotation about the vertical z axis.</small></div>
<div class="card"><b>Example, CSV line {example["line"]}</b> (Kabsch)
<div class="mono" style="margin-top:6px">P · UB<sub>ADVISOR</sub></div>{matrix_html(cmp.BLISS_FROM_ADVISOR @ ex_k, "{:+.5f}")}
<div class="mono">UB<sub>BLISS</sub></div>{matrix_html(example["ub_bliss"], "{:+.5f}")}</div>
</div>
<p>Because the rows of UB are the lab-frame (φ-axis-frame) components of Q, a row permutation with a sign
is purely a <b>relabelling of the laboratory axes</b>; the columns (the reciprocal-lattice basis, i.e. the
B matrix) are untouched. P is a proper rotation, so both frames are right-handed and share the vertical z
axis. ADVISOR puts the beam along +Y; BLISS's +x is ADVISOR's +Y, i.e. the beam direction, and BLISS's
+y is ADVISOR's −X. Both sketches below show the same physical setup seen from above.</p>
<div class="two">
<div class="card frame">{advisor_axes}</div>
<div class="card frame">{bliss_axes}</div>
</div>
<p>The mapping was found without assuming it. For each row, all 48 signed 3×3 permutations M were tried, and the one
minimising max|M·UB<sub>ADVISOR</sub> − UB<sub>BLISS</sub>| was taken. P won on every row, and
the runner-up was always at least 10× worse. The two monoclinic rows (β = 109.04°) agree too, so the
B-matrix conventions are the same in both programs.</p>

<h2 id="methods">2 · Why the numbers still differ: Busing–Levy vs Kabsch</h2>
<p>After applying P, ADVISOR's CSV values still differ from BLISS by up to {max_k:.1e} Å⁻¹
({max_kmis:.2f}° of misorientation). The cause is the orientation algorithm, not a bug:</p>
<ul>
<li><b>BLISS – Busing–Levy</b> (Acta Cryst. 22, 457, 1967): reflection 1 is the <i>primary</i> and is matched
exactly; reflection 2 (<i>secondary</i>) only fixes the rotation about it.</li>
<li><b>ADVISOR (original) – Kabsch</b>: the rotation that best fits both reflections in the
least-squares sense.</li>
</ul>
<div class="card">{methods_svg()}
<div class="legend"><span>— measured scattering vector q</span><span style="color:var(--s1)">‒ ‒ lattice vector after rotation, U·g</span></div>
</div>
<p>If the measured angle between the two reflections equals the angle implied by the lattice constants,
the two methods give the same U. Real data never match perfectly: lattice constants are entered
to a few decimals, and motor positions carry their own errors. Kabsch spreads the mismatch Δ over both
reflections, while Busing–Levy puts all of it on reflection 2, so the two U differ by at most |Δ|.
To confirm this, a Busing–Levy mode was added to ADVISOR. It is now the default, and Kabsch stays
selectable from the UB Matrix panel. With Busing–Levy, the largest difference from BLISS over all
{n} rows is <b>{max_bl:.1e} Å⁻¹</b>.</p>
<p><b>How close is that?</b> The BLISS values in the CSV were supplied with {decimals[0]}–{decimals[-1]} decimals
(mostly 8). Every Busing–Levy difference is smaller than one unit in the last digit supplied for that value (worst:
{worst_unit[0]:.2f} units, line {worst_unit[1]} <code>{worst_unit[2]} = {worst_unit[3]}</code>, given to {worst_unit[4]} decimals).
{f"All but {len(over_half)} entr{'y is' if len(over_half) == 1 else 'ies are'} within half a unit, as expected from rounding; the exception"
 f"{'' if len(over_half) == 1 else 's'} would fit truncation or a dropped digit."
 if over_half else "All are within half a unit, as expected from rounding."}
That the remaining difference comes from the precision of the supplied numbers is an inference. It has not been
checked against BLISS's own full-precision output.</p>

<h3>Per-case discrepancy from BLISS</h3>
<div class="legend"><span><i style="background:var(--s1)"></i>ADVISOR Kabsch</span>
<span><i style="background:var(--s2)"></i>ADVISOR Busing–Levy</span></div>
<div class="card">{dot_chart(rows)}</div>
<small>Max |element difference| in Å⁻¹ after applying P, log scale. The Busing–Levy differences are at the
level of the last digits supplied in the CSV. Hover a column for details; full values are in the table below.</small>

<h3>Kabsch gap is bounded by the data inconsistency</h3>
<div class="card">{scatter_chart(rows)}</div>
<small>{"Every point lies on or below the diagonal." if "check_kabsch_close_to_bliss_and_gap_explained" not in failed_names else "<span class='warn'>Some rows violate the bound; see the failures above.</span>"} The largest gaps belong to the rows with the largest
reflection-angle mismatch: {", ".join(f'line {r["line"]} ({r["system"]}, Δ = {r["mismatch"]:+.2f}°)' for r in sorted(rows, key=lambda r: -abs(r["mismatch"]))[:3])}.</small>

<h2 id="tolerances">3 · Tolerances</h2>
<div class="tablewrap"><table class="data"><thead><tr><th class="l">Comparison</th><th>Tolerance</th>
<th>Observed worst</th><th class="l">Rationale</th></tr></thead><tbody>{tol_html}</tbody></table></div>
<p class="muted">UB is in Å⁻¹ and includes the factor 2π (|Q| = 2π/d), the same convention in both programs.</p>

<h2 id="results">4 · Per-case results</h2>
<p>Two rows written out in full, for visual review: line {SHOWCASE_LINES[0]} has the largest Kabsch gap, and line
{SHOWCASE_LINES[1]} is typical. All matrices are in BLISS's lab frame, with ADVISOR's results multiplied by P, and
values are in Å⁻¹. Each ADVISOR cell is tinted by its difference from BLISS. Hover a cell for the exact value.</p>
<div class="heatkey"><span>Cell tint = |ADVISOR − BLISS|:</span><span>≤ 10⁻⁹</span><span class="bar"></span><span>10⁻² Å⁻¹</span></div>
{showcase_html(rows)}
<h3>All cases</h3>
<p class="muted" style="margin-top:0">Click a column header to sort (the angle-mismatch column sorts by size, ignoring sign).
Hover a crystal for its lattice and energy. The highlighted columns are the comparison with BLISS.</p>
<div class="tablewrap"><table class="data sortable-table"><thead>
<tr class="groups"><th colspan="3" class="l">Case</th><th>Input data</th>
<th colspan="2" class="hl">Max |ΔUB| vs BLISS<span class="unit">Å⁻¹</span></th>
<th colspan="2" class="hl">Misorientation vs BLISS<span class="unit">°</span></th></tr>
<tr><th>Line</th><th class="l">Crystal</th><th class="l">Reflections 1 / 2</th>
<th>Angle mismatch<span class="unit">°</span></th>
<th class="hl">Busing–Levy</th><th class="hl">Kabsch</th><th class="hl">Busing–Levy</th><th class="hl">Kabsch</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table></div>

<div class="card colguide">
<b>What the columns mean</b>
<dl>
<dt>Line · Crystal · Reflections</dt>
<dd>The CSV line, the crystal system implied by the lattice constants, and the two reflections (H K L), in the order they were used.
Reflection 1 is Busing–Levy's primary.</dd>
<dt>Angle mismatch</dt>
<dd>The lattice-predicted minus the measured angle between the two reflections. This is the only kind of input error that
makes Busing–Levy and Kabsch disagree. It is 0 for perfectly consistent data.</dd>
<dt>Max |ΔUB| vs BLISS</dt>
<dd>The largest of the nine element differences between ADVISOR's UB (rotated into BLISS's frame with P) and BLISS's UB,
in Å⁻¹. For Busing–Levy this is the validation result: {"in this run, every value is below the 10⁻⁶ Å⁻¹ tolerance" if "check_busing_levy_matches_bliss" not in failed_names else "<span class='warn'>some values exceed the 10⁻⁶ Å⁻¹ tolerance; see the failures at the top</span>"}.
For Kabsch it shows the size of the method difference (tolerance 0.02 Å⁻¹).</dd>
<dt>Misorientation vs BLISS</dt>
<dd>The angle of the rotation that takes ADVISOR's orientation onto BLISS's: one number for how far apart the two
orientations are, independent of the lattice. Busing–Levy values are at numerical-noise level. "&lt; 10⁻⁶" means the
angle is below what this calculation can resolve, which is about 10⁻⁶°.
{"On every row, the Kabsch value is no larger than the angle mismatch" if "check_kabsch_close_to_bliss_and_gap_explained" not in failed_names else "<span class='warn'>Some rows break the bound (Kabsch misorientation ≤ angle mismatch); see the failures at the top</span>"}
(see the scatter plot in section 2).</dd>
</dl>
</div>

<h2 id="reproduce">5 · How to reproduce</h2>
<div class="card">
<pre class="cmd"># the {n_checks} checks in this report, plus tests of the report itself
python3 -m pytest tests/bliss_validation

# rebuild this page (exits 1 if any check fails)
python3 tests/bliss_validation/generate_bliss_comparison_report.py</pre>
<dl class="prov">{prov}</dl>
</div>
<p class="muted">To add cases, append rows to the CSV with the same columns and run both commands. The report re-runs
the same check functions as the pytest suite, so its verdict cannot drift from the tests.</p>

<h2 id="conclusion">6 · Conclusion</h2>
{conclusion_html}
</main><div id="tip"></div><script>{JS}</script></body></html>
"""


def conclusion(rows, outcomes, max_bl, max_kmis):
    n = len(rows)
    failures = [o for o in outcomes if o[2] is not None]
    if failures:
        return (f'<p class="warn">Validation failed: {len(failures)} of {len(outcomes)} checks did not pass '
                '(listed at the top). The conclusions of earlier runs do not apply to this data until the '
                'failures are explained.</p>')
    return f"""<ul>
<li><b>Convention.</b> ADVISOR and BLISS use the same reciprocal-lattice (B) convention, and their lab frames
differ by one fixed rotation: <span class="mono">UB<sub>BLISS</sub> = P·UB<sub>ADVISOR</sub></span>, a −90° turn about the vertical axis,
because BLISS puts x along the beam while ADVISOR puts Y along it. No handedness or sign problem exists.</li>
<li><b>Agreement.</b> With the new Busing–Levy mode (now ADVISOR's default), ADVISOR agrees with BLISS to
≤ {max_bl:.1e} Å⁻¹ on all {n} cases, smaller than one unit in the last digit supplied for every value. ADVISOR's original Kabsch fit stays within
{max_kmis:.2f}°, and each row's gap is bounded by how inconsistent that row's two reflections are with the lattice.</li>
<li><b>Regression protection.</b> <code>tests/bliss_validation/test_bliss_ub_comparison.py</code> enforces all of the
above ({len(outcomes)} checks, all passing in this run). Re-run this generator after adding new BLISS rows to the CSV.</li>
</ul>"""


def main():
    rows = analyse()
    outcomes = cmp.run_all_checks(cmp.HEADER, cmp.RAW_ROWS, cmp.CASES)
    OUTPUT.write_text(colorize_names(build(rows, outcomes)), encoding="utf-8")
    failures = [o for o in outcomes if o[2] is not None]
    print(f"wrote {OUTPUT}: {len(outcomes) - len(failures)}/{len(outcomes)} checks pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
