"""tasks x variants x reps -> claude -p (Sonnet) -> score -> results/summary.csv"""
import json, subprocess, sys, time, re, csv, pathlib, shutil, os
ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-5-5"
HINT = ("A Neo4j graph of this codebase's compiled classes (produced by jQAssistant) is available via the neo4j MCP tools. "
        "Labels: Type (fqn, name), Method, Field, Package, Artifact; relations: DECLARES, EXTENDS, IMPLEMENTS, INVOKES, DEPENDS_ON, OVERRIDES. "
        "Call get_neo4j_schema first. Use it where it helps; source code is still in the working directory.")
VARIANTS = {"A": {"mcp": "none.json", "tools": "Read,Grep,Glob,Bash", "sys": None},
            "B": {"mcp": "neo4j.json", "tools": "Read,Grep,Glob,Bash,mcp__neo4j", "sys": HINT},
            "B0": {"mcp": "neo4j.json", "tools": "Read,Grep,Glob,Bash,mcp__neo4j", "sys": None}}

def worktree(name):
    p = ROOT / "worktrees" / name
    if not p.exists():
        subprocess.run(["git", "-C", str(ROOT / "pulsar"), "worktree", "add", "--detach", str(p), "HEAD"], check=True, capture_output=True)
    return p

def score(task, text):
    found = set(re.findall(r"org\.apache\.pulsar(?:\.\w+)+", text))
    exp = task["expected"]
    tp = len([e for e in exp if e in found])
    if task["id"] == "T07":  # ranked list: compare to first 10 names mentioned
        order = list(dict.fromkeys(re.findall(r"org\.apache\.pulsar(?:\.\w+)+", text)))[:10]
        found = set(order); tp = len([e for e in exp if e in found])
    return {"precision": round(tp / max(len(found), 1), 2), "recall": round(tp / len(exp), 2)}

def run(task, v, rep):
    name = f"{task['id']}-{v}-{rep}"
    wt = worktree(name); cfg = VARIANTS[v]
    cmd = ["claude", "-p", task["prompt"], "--model", MODEL, "--output-format", "json", "--max-turns", "30",
           "--strict-mcp-config", "--mcp-config", str(ROOT / "mcp" / cfg["mcp"]),
           "--allowedTools", cfg["tools"], "--permission-mode", "acceptEdits"]
    if cfg["sys"]: cmd += ["--append-system-prompt", cfg["sys"]]
    if task["type"] == "code": cmd[cmd.index("--allowedTools") + 1] += ",Edit,Write"
    t0 = time.time()
    r = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, encoding="utf-8")
    dt = time.time() - t0
    (ROOT / "results/raw" / f"{name}.json").write_text(r.stdout or r.stderr, encoding="utf-8")
    try:
        ev = json.loads(r.stdout); j = ev[-1] if isinstance(ev, list) else ev
    except Exception: return {"run": name, "error": (r.stderr or r.stdout)[:200]}
    tools = [b["name"] for e in (ev if isinstance(ev, list) else []) if e.get("type") == "assistant"
             for b in e["message"]["content"] if b.get("type") == "tool_use"]
    u = j.get("usage", {})
    row = {"run": name, "task": task["id"], "variant": v, "rep": rep, "turns": j.get("num_turns"), "cost_usd": round(j.get("total_cost_usd", 0), 3),
           "in_tok": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
           "out_tok": u.get("output_tokens"), "secs": round(dt), "tool_calls": len(tools), "mcp_calls": len([t for t in tools if t.startswith("mcp__")])}
    row.update(score(task, j.get("result", "")) if task["type"] == "qa" else check_code(task, wt, name, j.get("result", "")))
    if task["type"] == "code":
        subprocess.run(["git", "-C", str(ROOT / "pulsar"), "worktree", "remove", "--force", str(wt)], capture_output=True)
    return row

def check_code(task, wt, name, answer):
    diff = subprocess.run(["git", "-C", str(wt), "diff"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    (ROOT / "results/raw" / f"{name}.diff").write_text(diff, encoding="utf-8")
    stat = subprocess.run(["git", "-C", str(wt), "diff", "--shortstat"], capture_output=True, text=True).stdout.strip()
    files = len(re.findall(r"^diff --git", diff, re.M))
    cp = subprocess.run(["sh", str(ROOT / "harness/compile.sh"), str(wt), task["modules"]], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = cp.stdout + cp.stderr
    ok = cp.returncode == 0 and "ERROR" not in out and files > 0
    (ROOT / "results/raw" / f"{name}.compile.log").write_text(out, encoding="utf-8")
    return {"compiles": int(ok), "files_changed": files, "diff_lines": len(diff.splitlines())}

if __name__ == "__main__":
    tasks = {t["id"]: t for t in json.loads((ROOT / "tasks/tasks.json").read_text())}
    ids = sys.argv[1].split(","); variants = sys.argv[2].split(","); reps = int(sys.argv[3])
    rows = [run(tasks[i], v, r) for i in ids for v in variants for r in range(1, reps + 1)]
    out = ROOT / "results/summary.csv"; new = not out.exists()
    keys = ["run","task","variant","rep","turns","cost_usd","in_tok","out_tok","secs","compiles","files_changed","diff_lines","tool_calls","mcp_calls","precision","recall","error"]
    with out.open("a", newline="") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore"); 
        if new: w.writeheader()
        w.writerows(rows)
    for r in rows: print(r)
