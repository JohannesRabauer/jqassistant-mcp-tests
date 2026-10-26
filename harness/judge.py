"""Blind judge: scores each code-run diff 0-10 with an Opus model that sees only task + diff."""
import json, subprocess, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
tasks = {t["id"]: t for t in json.loads((ROOT / "tasks/tasks.json").read_text())}
out = ROOT / "results/judgments.json"
done = json.loads(out.read_text()) if out.exists() else {}
RUBRIC = ("You are a strict code reviewer. Below is a task given to a coding agent and the git diff it produced. "
          "You cannot run the code. Judge: (1) completeness: are all required places changed (declaration, all implementations, all callers)? "
          "(2) precision: no unrelated changes, no wrongly renamed unrelated methods. (3) plausibility of compiling. "
          'Reply with ONLY JSON: {"score":0-10,"complete":true/false,"collateral_damage":true/false,"notes":"max 2 sentences"}')
for d in sorted((ROOT / "results/raw").glob("*.diff")):
    name = d.stem
    tid = name.split("-")[0]
    if (name in done and done[name].get("score") is not None) or tid not in tasks: continue
    diff = d.read_text(encoding="utf-8")
    if len(diff) > 60000:  # drop unchanged context lines to fit
        diff = chr(10).join(l for l in diff.splitlines() if l[:1] in "+-" or l.startswith(("diff ", "@@")))
    diff = diff[:90000] or "(empty diff)"
    prompt = f"{RUBRIC}\n\nTASK:\n{tasks[tid]['prompt']}\n\nDIFF:\n{diff}"
    r = subprocess.run(["claude", "-p", "--model", "claude-opus-5-5", "--output-format", "json", "--max-turns", "1",
                        "--strict-mcp-config", "--mcp-config", str(ROOT / "mcp/none.json"), "--allowedTools", ""],
                       input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT / "results"))
    try:
        ev = json.loads(r.stdout); res = ev[-1] if isinstance(ev, list) else ev
        m = re.search(r"\{.*\}", res["result"], re.S); done[name] = json.loads(m.group(0))
    except Exception as e:
        done[name] = {"score": None, "notes": f"judge error {e}"}
    print(name, done[name]); out.write_text(json.dumps(done, indent=1))
