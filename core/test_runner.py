"""Test runner for Eris."""
import json
import subprocess
from pathlib import Path

def test_runner_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready", "frameworks": ["pytest", "unittest", "node"]})
    elif action == "run":
        path = params.get("path", "tests/")
        framework = params.get("framework", "auto")
        verbose = params.get("verbose", True)
        if framework == "auto":
            if (Path(path) / "package.json").exists():
                framework = "node"
            else:
                framework = "pytest"
        if framework == "pytest":
            cmd = "python -m pytest {} --tb=short --no-header".format(path)
            if verbose:
                cmd += " -v"
        elif framework == "node":
            cmd = "cd {} && npm test".format(path)
        elif framework == "unittest":
            cmd = "python -m unittest discover -s {}".format(path)
        else:
            return json.dumps({"error": "Unknown framework"})
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            output = r.stdout + r.stderr
            passed = output.count("PASSED") + output.count("✓") + output.count("passed")
            failed = output.count("FAILED") + output.count("✗") + output.count("failed")
            errors = output.count("ERROR")
            return json.dumps({"framework": framework, "passed": passed, "failed": failed, "errors": errors, "output": output[-2000:]})
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "Tests timed out (120s)"})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    elif action == "discover":
        path = params.get("path", ".")
        test_files = list(Path(path).rglob("test_*.py")) + list(Path(path).rglob("*_test.py")) + list(Path(path).rglob("*.test.js")) + list(Path(path).rglob("*.spec.js"))
        return json.dumps({"files": [str(f) for f in test_files[:50]], "count": len(test_files)})
    return json.dumps({"error": "Unknown action"})
