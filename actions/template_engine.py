"""Template engine module for generating documents from templates."""

import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from string import Template

DATA_DIR = Path(__file__).parent / "data" / "templates"

BUILTIN_TEMPLATES = {
    "invoice": {
        "name": "Invoice",
        "ext": ".txt",
        "template": (
            "INVOICE\n"
            "========================================\n"
            "Invoice #: ${invoice_number}\n"
            "Date: ${date}\n"
            "Due Date: ${due_date}\n\n"
            "From:\n"
            "  ${from_name}\n"
            "  ${from_address}\n"
            "  ${from_email}\n\n"
            "To:\n"
            "  ${to_name}\n"
            "  ${to_address}\n\n"
            "Items:\n"
            "----------------------------------------\n"
            "${items}\n"
            "----------------------------------------\n\n"
            "Subtotal: $${subtotal}\n"
            "Tax (${tax_rate}%): $${tax}\n"
            "Total: $${total}\n\n"
            "Payment Terms: ${payment_terms}\n"
            "Notes: ${notes}\n"
        ),
        "defaults": {
            "invoice_number": "INV-001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": "",
            "from_name": "",
            "from_address": "",
            "from_email": "",
            "to_name": "",
            "to_address": "",
            "items": "  Item 1          x1    $0.00",
            "subtotal": "0.00",
            "tax_rate": "0",
            "tax": "0.00",
            "total": "0.00",
            "payment_terms": "Net 30",
            "notes": ""
        }
    },
    "letter": {
        "name": "Formal Letter",
        "ext": ".txt",
        "template": (
            "${date}\n\n"
            "${sender_name}\n"
            "${sender_address}\n"
            "${sender_email}\n\n"
            "Dear ${recipient_name},\n\n"
            "${body}\n\n"
            "Sincerely,\n"
            "${sender_name}\n"
            "${sender_title}\n"
        ),
        "defaults": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sender_name": "",
            "sender_address": "",
            "sender_email": "",
            "recipient_name": "",
            "body": "",
            "sender_title": ""
        }
    },
    "contract": {
        "name": "Contract",
        "ext": ".txt",
        "template": (
            "CONTRACT AGREEMENT\n"
            "========================================\n\n"
            "Date: ${date}\n"
            "Contract ID: ${contract_id}\n\n"
            "PARTIES:\n"
            "  Party A: ${party_a}\n"
            "  Party B: ${party_b}\n\n"
            "TERMS AND CONDITIONS:\n"
            "${terms}\n\n"
            "DURATION:\n"
            "  Start Date: ${start_date}\n"
            "  End Date: ${end_date}\n\n"
            "COMPENSATION:\n"
            "  ${compensation}\n\n"
            "SIGNATURES:\n\n"
            "Party A: _________________________  Date: _________\n"
            "  ${party_a}\n\n"
            "Party B: _________________________  Date: _________\n"
            "  ${party_b}\n"
        ),
        "defaults": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "contract_id": "CTR-001",
            "party_a": "",
            "party_b": "",
            "terms": "1. This agreement shall be binding upon both parties.\n2. Both parties agree to the terms outlined herein.",
            "start_date": "",
            "end_date": "",
            "compensation": ""
        }
    },
    "report": {
        "name": "Report",
        "ext": ".txt",
        "template": (
            "${report_title}\n"
            "========================================\n"
            "Author: ${author}\n"
            "Date: ${date}\n"
            "Department: ${department}\n\n"
            "EXECUTIVE SUMMARY\n"
            "----------------------------------------\n"
            "${summary}\n\n"
            "FINDINGS\n"
            "----------------------------------------\n"
            "${findings}\n\n"
            "RECOMMENDATIONS\n"
            "----------------------------------------\n"
            "${recommendations}\n\n"
            "CONCLUSION\n"
            "----------------------------------------\n"
            "${conclusion}\n"
        ),
        "defaults": {
            "report_title": "Report Title",
            "author": "",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "department": "",
            "summary": "",
            "findings": "",
            "recommendations": "",
            "conclusion": ""
        }
    },
    "receipt": {
        "name": "Receipt",
        "ext": ".txt",
        "template": (
            "RECEIPT\n"
            "========================================\n"
            "Receipt #: ${receipt_number}\n"
            "Date: ${date}\n"
            "Time: ${time}\n\n"
            "Merchant: ${merchant}\n"
            "Address: ${address}\n\n"
            "Items Purchased:\n"
            "----------------------------------------\n"
            "${items}\n"
            "----------------------------------------\n\n"
            "Subtotal: $${subtotal}\n"
            "Tax: $${tax}\n"
            "Total: $${total}\n\n"
            "Payment Method: ${payment_method}\n"
            "Transaction ID: ${transaction_id}\n\n"
            "Thank you for your purchase!\n"
        ),
        "defaults": {
            "receipt_number": "RCP-001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "merchant": "",
            "address": "",
            "items": "",
            "subtotal": "0.00",
            "tax": "0.00",
            "total": "0.00",
            "payment_method": "Cash",
            "transaction_id": ""
        }
    },
    "resume": {
        "name": "Resume",
        "ext": ".txt",
        "template": (
            "${full_name}\n"
            "========================================\n"
            "${address} | ${phone} | ${email}\n"
            "${linkedin}\n\n"
            "OBJECTIVE\n"
            "----------------------------------------\n"
            "${objective}\n\n"
            "EXPERIENCE\n"
            "----------------------------------------\n"
            "${experience}\n\n"
            "EDUCATION\n"
            "----------------------------------------\n"
            "${education}\n\n"
            "SKILLS\n"
            "----------------------------------------\n"
            "${skills}\n\n"
            "CERTIFICATIONS\n"
            "----------------------------------------\n"
            "${certifications}\n"
        ),
        "defaults": {
            "full_name": "",
            "address": "",
            "phone": "",
            "email": "",
            "linkedin": "",
            "objective": "",
            "experience": "",
            "education": "",
            "skills": "",
            "certifications": ""
        }
    }
}


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_custom_templates() -> dict:
    _ensure_data_dir()
    custom = {}
    for f in DATA_DIR.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                custom[f.stem] = data
            except (json.JSONDecodeError, OSError):
                pass
    return custom


def _get_all_templates() -> dict:
    all_tmpls = dict(BUILTIN_TEMPLATES)
    custom = _load_custom_templates()
    all_tmpls.update(custom)
    return all_tmpls


def _fill_template(template_text: str, variables: dict) -> str:
    result = template_text
    for key, value in variables.items():
        result = result.replace(f"${{{key}}}", str(value))

    def _replace_missing(match):
        var_name = match.group(1)
        return f"[{var_name}]"

    result = re.sub(r'\$\{(\w+)\}', _replace_missing, result)
    return result


def template_engine(parameters: dict, player=None) -> str:
    action = parameters.get("action", "generate")

    if action == "generate":
        template_name = parameters.get("template", "")
        variables = parameters.get("variables", {})
        output = parameters.get("output", "")

        all_tmpls = _get_all_templates()
        if template_name not in all_tmpls:
            available = ", ".join(sorted(all_tmpls.keys()))
            return f"Error: Template '{template_name}' not found. Available: {available}"

        tmpl = all_tmpls[template_name]
        ext = tmpl.get("ext", ".txt")

        defaults = tmpl.get("defaults", {})
        merged = dict(defaults)
        merged.update(variables)

        filled = _fill_template(tmpl["template"], merged)

        if output:
            output = os.path.expanduser(output)
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

            try:
                import docx
                doc = docx.Document()
                for line in filled.split("\n"):
                    doc.add_paragraph(line)
                if not output.endswith(".docx"):
                    output = Path(output).with_suffix(".docx")
                doc.save(str(output))
                return f"Generated {template_name} document (.docx) -> {output}\n\n{filled}"
            except ImportError:
                pass

            if not output.endswith(ext):
                output = Path(output).with_suffix(ext)
            Path(output).write_text(filled, encoding="utf-8")
            return f"Generated {template_name} document -> {output}\n\n{filled}"
        else:
            return f"Template: {template_name}\n{'=' * 60}\n{filled}"

    elif action == "list":
        all_tmpls = _get_all_templates()
        lines = ["Available Templates:", "=" * 40]
        for name, tmpl in sorted(all_tmpls.items()):
            lines.append(f"  {name}: {tmpl.get('name', name)} ({tmpl.get('ext', '.txt')})")
            defaults = tmpl.get("defaults", {})
            lines.append(f"    Variables: {', '.join(sorted(defaults.keys()))}")
        lines.append(f"\nTotal: {len(all_tmpls)} templates")
        return "\n".join(lines)

    elif action == "create":
        name = parameters.get("name", "")
        template_text = parameters.get("template", "")
        if not name:
            return "Error: 'name' parameter required."
        if not template_text:
            return "Error: 'template' parameter required."

        _ensure_data_dir()
        custom = {
            "name": name,
            "ext": ".txt",
            "template": template_text,
            "defaults": {}
        }

        vars_in_template = re.findall(r'\$\{(\w+)\}', template_text)
        for v in vars_in_template:
            custom["defaults"][v] = ""

        out_path = DATA_DIR / f"{name}.json"
        out_path.write_text(json.dumps(custom, indent=2), encoding="utf-8")
        return f"Created template '{name}' with variables: {', '.join(vars_in_template)}\nSaved to {out_path}"

    elif action == "preview":
        template_name = parameters.get("template", "")
        all_tmpls = _get_all_templates()
        if template_name not in all_tmpls:
            return f"Error: Template '{template_name}' not found."
        tmpl = all_tmpls[template_name]
        return f"Template: {template_name}\n{'=' * 60}\n{tmpl['template']}\n\nDefaults: {json.dumps(tmpl.get('defaults', {}), indent=2)}"

    elif action == "save":
        template_name = parameters.get("template", "")
        variables = parameters.get("variables", {})
        output = parameters.get("output", "")

        if not output:
            return "Error: 'output' parameter required."
        if not template_name:
            return "Error: 'template' parameter required."

        all_tmpls = _get_all_templates()
        if template_name not in all_tmpls:
            return f"Error: Template '{template_name}' not found."

        tmpl = all_tmpls[template_name]
        defaults = tmpl.get("defaults", {})
        merged = dict(defaults)
        merged.update(variables)

        filled = _fill_template(tmpl["template"], merged)
        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        Path(output).write_text(filled, encoding="utf-8")
        return f"Saved generated document -> {output}"

    else:
        return f"Error: Unknown action '{action}'. Available: generate, list, create, preview, save"
