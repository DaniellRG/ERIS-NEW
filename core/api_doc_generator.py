"""API documentation generator for Eris."""
import json
from pathlib import Path

def api_doc_generator_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"formats": ["openapi_3_0", "openapi_3_1", "markdown"]})
    elif action == "generate_openapi":
        title = params.get("title", "API")
        version = params.get("version", "1.0.0")
        endpoints = params.get("endpoints", [])
        spec = {
            "openapi": "3.0.3",
            "info": {"title": title, "version": version},
            "paths": {},
        }
        for ep in endpoints:
            path = ep.get("path", "/")
            method = ep.get("method", "get").lower()
            spec["paths"].setdefault(path, {})[method] = {
                "summary": ep.get("summary", ""),
                "parameters": [{"name": p.get("name"), "in": "query", "schema": {"type": p.get("type", "string")}} for p in ep.get("params", [])],
                "responses": {"200": {"description": "Success"}},
            }
        output = params.get("output", "")
        if output:
            Path(output).write_text(json.dumps(spec, indent=2), encoding="utf-8")
        return json.dumps({"spec": spec, "output": output or "inline"})
    elif action == "generate_markdown":
        title = params.get("title", "API")
        endpoints = params.get("endpoints", [])
        md = "# {} API Documentation\n\n".format(title)
        for ep in endpoints:
            md += "## {} `{}`\n\n".format(ep.get("method", "GET").upper(), ep.get("path", "/"))
            md += "{}\n\n".format(ep.get("summary", ""))
            if ep.get("params"):
                md += "### Parameters\n\n| Name | Type | Required |\n|------|------|----------|\n"
                for p in ep.get("params", []):
                    md += "| {} | {} | {} |\n".format(p.get("name"), p.get("type", "string"), p.get("required", "no"))
                md += "\n"
        output = params.get("output", "")
        if output:
            Path(output).write_text(md, encoding="utf-8")
        return json.dumps({"markdown": md[:3000], "output": output or "inline"})
    return json.dumps({"error": "Unknown action"})
