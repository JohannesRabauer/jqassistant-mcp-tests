"""Builds docs/report.html: one self-contained file with the run data embedded."""
import json, re, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results/raw"
runs = json.loads((ROOT / "results/runs.json").read_text())
judge = json.loads((ROOT / "results/judgments.json").read_text())
tasks = {t["id"]: {"id": t["id"], "type": t["type"], "prompt": t["prompt"]} for t in json.loads((ROOT / "tasks/tasks.json").read_text())}
KIND = {"Grep": "search", "Glob": "search", "Bash": "shell", "Read": "read", "Edit": "edit", "Write": "edit"}

for r in runs:
    ev = json.loads((R / f"{r['run']}.json").read_text(encoding="utf-8"))
    mix, queries = collections.Counter(), []
    for e in ev:
        if e.get("type") != "assistant": continue
        for b in e["message"]["content"]:
            if b.get("type") != "tool_use": continue
            mix["graph" if b["name"].startswith("mcp__") else KIND.get(b["name"], "other")] += 1
            if b["name"].endswith("read_neo4j_cypher") and len(queries) < 4:
                queries.append(re.sub(r"\s+", " ", b["input"].get("query", ""))[:400])
    j = judge.get(r["run"], {})
    r.update(toolmix=dict(mix), queries=queries, answer=(ev[-1].get("result") or "")[:900],
             note=j.get("notes") if j.get("score") is not None else None,
             complete=j.get("complete"), collateral=j.get("collateral_damage"))
    errs, log = [], R / f"{r['run']}.compile.log"
    if log.exists():
        for m in re.finditer(r"ERROR\] /src/(\S+?\.java):\[(\d+),\d+\] ([^\n]+)", log.read_text(encoding="utf-8", errors="replace")):
            s = f"{m.group(1).split('/')[-1]}:{m.group(2)} {m.group(3).strip()}"
            if s not in errs: errs.append(s)
    r["errlist"] = errs[:4]

data = json.dumps({"runs": runs, "tasks": tasks}).replace("</", "<\\/")
html = (ROOT / "harness/report_template.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
out = ROOT / "docs/report.html"; out.parent.mkdir(exist_ok=True); out.write_text(html, encoding="utf-8")
print(out, len(html))
