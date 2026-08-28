"""Coverage reporter for Eris."""
import json
import subprocess
from pathlib import Path

def coverage_reporter_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready"})
    elif action == "run":
        path = params.get("path", "src/")
        test_path = params.get("test_path", "tests/")
        try:
            r = subprocess.run(
                "python -m pytest {} --cov={} --cov-report=json --cov-report=term --no-header -q".format(test_path, path),
                shell=True, capture_output=True, text=True, timeout=120
            )
            output = r.stdout + r.stderr
            cov_json = Path("coverage.json")
            if cov_json.exists():
                data = json.loads(cov_json.read_text(encoding="utf-8"))
                summary = data.get("totals", {})
                return json.dumps({
                    "total_coverage": round(summary.get("percent_covered", 0), 1),
                    "lines_covered": summary.get("covered_lines", 0),
                    "lines_total": summary.get("num_statements", 0),
                    "missing": summary.get("missing_lines", 0),
                    "output": output[-1000:],
                })
            return json.dumps({"output": output[-2000:], "coverage_file": "not found"})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    elif action == "report":
        cov_json = Path("coverage.json")
        if not cov_json.exists():
            return json.dumps({"error": "No coverage data. Run coverage first."})
        data = json.loads(cov_json.read_text(encoding="utf-8"))
        files = {}
        for f, fdata in data.get("files", {}).items():
            files[f] = round(fdata.get("summary", {}).get("percent_covered", 0), 1)
        sorted_files = sorted(files.items(), key=lambda x: x[1])
        return json.dumps({
            "total": round(data.get("totals", {}).get("percent_covered", 0), 1),
            "worst": [{"file": f, "coverage": c} for f, c in sorted_files[:5]],
            "best": [{"file": f, "coverage": c} for f, c in sorted_files[-5:]],
        })
    return json.dumps({"error": "Unknown action"})
