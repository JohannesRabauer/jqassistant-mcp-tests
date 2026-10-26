"""Static charts for the README (light + dark SVG). Palette: dataviz categorical slots 1-3, validated."""
import json, pathlib, statistics as st
ROOT = pathlib.Path(__file__).resolve().parent.parent
rows = json.loads((ROOT / "results/runs.json").read_text())
OUT = ROOT / "docs/charts"; OUT.mkdir(parents=True, exist_ok=True)
VARS = ["A", "B", "B0"]
NAMES = {"A": "A grep only", "B": "B graph + hint", "B0": "B0 graph, no hint"}
THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e0", s={"A": "#2a78d6", "B": "#eb6834", "B0": "#1baf7a"}),
    "dark": dict(bg="#1a1a19", ink="#f0efec", ink2="#c3c2b7", grid="#383835", s={"A": "#3987e5", "B": "#d95926", "B0": "#199e70"}),
}

def cell(task, v, key, agg):
    vals = [r[key] for r in rows if r["task"] == task and r["variant"] == v and r[key] is not None]
    if not vals: return None
    return sum(vals) if agg == "sum" else st.mean(vals)

def grouped(name, title, sub, tasks, key, agg, ymax, fmt, theme, ticks):
    t = THEMES[theme]; W, H = 760, 380; L, R, T, B = 52, 16, 84, 44
    iw, ih = W - L - R, H - T - B
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,Segoe UI,sans-serif">',
         f'<title>{title}</title><rect width="{W}" height="{H}" fill="{t["bg"]}" rx="8"/>',
         f'<text x="{L}" y="26" font-size="16" font-weight="600" fill="{t["ink"]}">{title}</text>',
         f'<text x="{L}" y="45" font-size="12" fill="{t["ink2"]}">{sub}</text>']
    for i, v in enumerate(VARS):  # legend
        x = L + i * 150
        o.append(f'<rect x="{x}" y="54" width="10" height="10" rx="2" fill="{t["s"][v]}"/><text x="{x+15}" y="63" font-size="12" fill="{t["ink2"]}">{NAMES[v]}</text>')
    for val in ticks:  # grid
        y = T + ih - ih * val / ymax
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{t["grid"]}"/><text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{t["ink2"]}">{fmt(val)}</text>')
    gw = iw / len(tasks); bw = min(34, gw / 4)
    for gi, task in enumerate(tasks):
        cx = L + gw * gi + gw / 2
        o.append(f'<text x="{cx:.1f}" y="{H-18}" text-anchor="middle" font-size="12" fill="{t["ink2"]}">{task}</text>')
        for vi, v in enumerate(VARS):
            val = cell(task, v, key, agg)
            if val is None: continue
            x = cx + (vi - 1) * (bw + 4) - bw / 2; h = ih * val / ymax; y = T + ih - h
            o.append(f'<path d="M{x:.1f} {T+ih:.1f}V{y+4:.1f}Q{x:.1f} {y:.1f} {x+4:.1f} {y:.1f}H{x+bw-4:.1f}Q{x+bw:.1f} {y:.1f} {x+bw:.1f} {y+4:.1f}V{T+ih:.1f}Z" fill="{t["s"][v]}"><title>{task} {NAMES[v]}: {fmt(val)}</title></path>')
            o.append(f'<text x="{x+bw/2:.1f}" y="{y-5:.1f}" text-anchor="middle" font-size="10" fill="{t["ink"]}">{fmt(val)}</text>')
    o.append("</svg>")
    (OUT / f"{name}-{theme}.svg").write_text("\n".join(o), encoding="utf-8")

pct = lambda v: f"{v*100:.0f}%"
for th in THEMES:
    grouped("compiles", "Code runs that compile", "Out of 3 runs per task. Higher is better.", ["T03", "T04", "T08", "H1", "H2", "H3"], "compiled", "sum", 3.4, lambda v: f"{v:.0f}", th, [0, 1, 2, 3])
    grouped("judge", "Blind judge score", "Mean of up to 3 runs, scale 0 to 10. Higher is better.", ["T03", "T04", "T08", "H1", "H2", "H3"], "judge", "mean", 11, lambda v: f"{v:.1f}", th, [0, 2, 4, 6, 8, 10])
    grouped("recall", "Question tasks: recall against the true list", "Mean of 3 runs. T07 is the only task where the graph can count what grep cannot.", ["T02", "T07"], "recall", "mean", 1.1, pct, th, [0, .25, .5, .75, 1])
    grouped("cost", "Cost per run", "Mean US dollars per run. Lower is better.", ["T02", "T07", "T03", "T04", "T08", "H1", "H2", "H3"], "cost", "mean", 1.0, lambda v: f"${v:.2f}", th, [0, .25, .5, .75, 1.0])
print("charts written to", OUT)
