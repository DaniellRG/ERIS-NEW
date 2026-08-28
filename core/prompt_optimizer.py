"""Prompt optimizer for Eris."""
import json
import re

def prompt_optimizer_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready", "techniques": ["clarity", "structure", "examples", "constraints", "role"]})
    elif action == "optimize":
        prompt = params.get("prompt", "")
        technique = params.get("technique", "auto")
        if not prompt:
            return json.dumps({"error": "Prompt required"})
        optimized = prompt
        suggestions = []
        if len(prompt) < 20:
            suggestions.append("Prompt too short - add more context")
        if "?" not in prompt and "." not in prompt:
            suggestions.append("Add clear ending punctuation")
        if not any(w in prompt.lower() for w in ["please", "use", "create", "generate", "write", "explain", "show"]):
            suggestions.append("Add action verb at the start")
        if "code" in prompt.lower() or "program" in prompt.lower():
            if "language" not in prompt.lower() and "python" not in prompt.lower() and "javascript" not in prompt.lower():
                suggestions.append("Specify programming language")
        if not any(c in prompt for c in ["`", '"', "'"]):
            if any(w in prompt.lower() for w in ["function", "class", "variable"]):
                suggestions.append("Use backticks for code references")
        if len(prompt.split()) < 5:
            suggestions.append("Add more detail about expected output")
        if technique == "auto":
            if "role:" not in prompt.lower() and "act as" not in prompt.lower():
                optimized = "Act as an expert. " + prompt
                suggestions.append("Added role context")
        return json.dumps({"original": prompt, "optimized": optimized, "suggestions": suggestions, "score": max(1, 10 - len(suggestions))})
    elif action == "analyze":
        prompt = params.get("prompt", "")
        if not prompt:
            return json.dumps({"error": "Prompt required"})
        words = len(prompt.split())
        sentences = len(re.split(r'[.!?]+', prompt))
        has_context = any(w in prompt.lower() for w in ["context", "background", "given", "assuming"])
        has_examples = any(w in prompt.lower() for w in ["example", "e.g.", "for instance", "like"])
        has_constraints = any(w in prompt.lower() for w in ["must", "should", "do not", "never", "always", "only"])
        has_role = any(w in prompt.lower() for w in ["role", "act as", "you are", "persona"])
        return json.dumps({
            "words": words, "sentences": sentences,
            "has_context": has_context, "has_examples": has_examples,
            "has_constraints": has_constraints, "has_role": has_role,
            "quality": "good" if all([has_context, has_examples]) else "medium" if any([has_context, has_examples]) else "needs_improvement",
        })
    return json.dumps({"error": "Unknown action"})
