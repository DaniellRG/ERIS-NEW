# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(r"D:\Eris_Source\data")
TRANSACTIONS_FILE = DATA_DIR / "finance_transactions.json"
CATEGORIES_FILE = DATA_DIR / "finance_categories.json"
BUDGETS_FILE = DATA_DIR / "finance_budgets.json"

DEFAULT_CATEGORIES = [
    "alimentacion", "transporte", "entretenimiento", "servicios",
    "salud", "educacion", "ropa", "tecnologia", "hogar",
    "inversiones", "otros"
]

BANK_PATTERNS = {
    "galicia": {"sep": ";", "date_col": ["fecha"], "desc_col": ["descripcion", "descripción"], "amount_col": ["monto", "importe"]},
    "macro": {"sep": ";", "date_col": ["fecha"], "desc_col": ["descripcion", "descripción"], "amount_col": ["monto", "importe"]},
    "brubank": {"sep": ",", "date_col": ["fecha", "date"], "desc_col": ["descripcion", "descripción", "description"], "amount_col": ["monto", "importe", "amount"]},
    "mercadopago": {"sep": ",", "date_col": ["fecha", "date"], "desc_col": ["descripcion", "descripción", "description"], "amount_col": ["monto", "importe", "amount"]},
    "generic": {"sep": ",", "date_col": ["fecha", "date"], "desc_col": ["descripcion", "descripción", "description"], "amount_col": ["monto", "importe", "amount"]},
}


def _load_json(path: Path, default=None):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def _save_json(path: Path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_transactions() -> list:
    return _load_json(TRANSACTIONS_FILE, {"transactions": []}).get("transactions", [])


def _save_transactions(txns: list):
    _save_json(TRANSACTIONS_FILE, {"transactions": txns})


def _load_categories() -> list:
    data = _load_json(CATEGORIES_FILE, None)
    if data is None:
        _save_json(CATEGORIES_FILE, {"categories": DEFAULT_CATEGORIES.copy()})
        return DEFAULT_CATEGORIES.copy()
    return data.get("categories", DEFAULT_CATEGORIES)


def _save_categories(cats: list):
    _save_json(CATEGORIES_FILE, {"categories": cats})


def _load_budgets() -> dict:
    return _load_json(BUDGETS_FILE, {"budgets": {}}).get("budgets", {})


def _save_budgets(budgets: dict):
    _save_json(BUDGETS_FILE, {"budgets": budgets})


def _gen_id(txns: list) -> str:
    return f"txn_{len(txns) + 1:06d}"


def _parse_date(date_str: str) -> Optional[str]:
    date_str = date_str.strip()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_amount(amount_str: str) -> Optional[float]:
    cleaned = amount_str.strip().replace("$", "").replace(" ", "")
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _match_col(header: str, candidates: list) -> bool:
    h = header.lower().strip().strip('"').strip("'")
    return h in [c.lower() for c in candidates]


def _auto_detect_category(description: str) -> str:
    desc = description.lower()
    mappings = {
        "alimentacion": ["supermercado", "almacén", "almacen", "comida", "restaurante", "restaur", "mcdonald", "burger", "pizza", "rappi", "pedidos ya", "coto", "carrefour", "jumbo", "dia", "changomas"],
        "transporte": ["uber", "cabify", "naftera", "YPF", "shell", "petrobras", "estacionamiento", "peaje", "subte", "colectivo", "bus", "taxi", "combustible", "auto"],
        "entretenimiento": ["netflix", "spotify", "disney", "hbo", "amazon prime", "cinema", "cine", "teatro", "juego", "steam", "playstation", "xbox"],
        "servicios": ["electricidad", "gas", "agua", "internet", "telefon", "movistar", "personal", "claro", "fibertel", "telecom"],
        "salud": ["farmacia", "hospital", "medico", "medica", "clinica", "clinica", "obra social", "prepag", "dentista"],
        "educacion": ["universidad", "colegio", "curso", "udemy", "coursera", "libro", "educacion", "school"],
        "tecnologia": ["apple", "samsung", "computadora", "notebook", "monitor", "mouse", "teclado", "software", "hardware"],
        "hogar": ["mueble", "decoración", "decoracion", "ferreteria", "casa", "hogar", "limpieza"],
        "ropa": ["zara", "h&m", "pull&bear", "ropa", "calzado", "zapato"],
        "inversiones": ["inversion", "inversión", "fondo", "cedear", "bono", "accion", "acción"],
    }
    for cat, keywords in mappings.items():
        for kw in keywords:
            if kw in desc:
                return cat
    return "otros"


def _detect_bank_params(headers: list, bank: str) -> dict:
    pattern = BANK_PATTERNS.get(bank, BANK_PATTERNS["generic"])
    result = {"sep": pattern["sep"], "date_idx": -1, "desc_idx": -1, "amount_idx": -1}
    for i, h in enumerate(headers):
        hl = h.lower().strip().strip('"').strip("'")
        if result["date_idx"] == -1 and _match_col(h, pattern["date_col"]):
            result["date_idx"] = i
        if result["desc_idx"] == -1 and _match_col(h, pattern["desc_col"]):
            result["desc_idx"] = i
        if result["amount_idx"] == -1 and _match_col(h, pattern["amount_col"]):
            result["amount_idx"] = i
    return result


def tool_add_transaction(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    amount = params.get("amount")
    description = params.get("description")
    category = params.get("category", "otros")
    date = params.get("date")
    if amount is None or description is None:
        return "Parámetros 'amount' y 'description' requeridos."
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return "Monto inválido."
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        parsed = _parse_date(str(date))
        if not parsed:
            return f"Fecha inválida: {date}"
        date = parsed
    categories = _load_categories()
    if category not in categories:
        category = "otros"
    txns = _load_transactions()
    txn = {
        "id": _gen_id(txns),
        "date": date,
        "amount": round(float(amount), 2),
        "description": description,
        "category": category,
        "account": params.get("account", "general"),
        "recurring": bool(params.get("recurring", False)),
        "tags": params.get("tags", []),
    }
    txns.append(txn)
    _save_transactions(txns)
    sign = "-" if amount < 0 else "+"
    return f"Transacción registrada: {txn['id']} | {date} | {sign}${abs(amount):.2f} | {description} [{category}]"


def tool_import_csv(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    filepath = params.get("filepath")
    bank = params.get("bank", "generic")
    if not filepath:
        return "Parámetro 'filepath' requerido."
    filepath = Path(filepath)
    if not filepath.exists():
        return f"Archivo no encontrado: {filepath}"
    pattern = BANK_PATTERNS.get(bank, BANK_PATTERNS["generic"])
    txns = _load_transactions()
    imported = 0
    skipped = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(1024 * 100)
            first_line = content.split("\n")[0]
            sep = pattern["sep"]
            if "\t" in first_line and first_line.count("\t") > first_line.count(sep):
                sep = "\t"
            f.seek(0)
            reader = csv.reader(f, delimiter=sep)
            headers = next(reader, None)
            if not headers:
                return "Archivo CSV vacío o sin headers."
            detected = _detect_bank_params(headers, bank)
            if detected["desc_idx"] == -1 or detected["amount_idx"] == -1:
                return f"No se detectaron columnas requeridas. Headers: {headers}"
            for row in reader:
                try:
                    if detected["amount_idx"] >= len(row):
                        skipped += 1
                        continue
                    amount = _parse_amount(row[detected["amount_idx"]])
                    if amount is None:
                        skipped += 1
                        continue
                    desc = row[detected["desc_idx"]].strip() if detected["desc_idx"] < len(row) else "Sin descripción"
                    date_str = ""
                    if detected["date_idx"] >= 0 and detected["date_idx"] < len(row):
                        date_str = _parse_date(row[detected["date_idx"]]) or ""
                    if not date_str:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                    category = _auto_detect_category(desc)
                    txn = {
                        "id": _gen_id(txns),
                        "date": date_str,
                        "amount": round(amount, 2),
                        "description": desc,
                        "category": category,
                        "account": bank,
                        "recurring": False,
                        "tags": [],
                    }
                    txns.append(txn)
                    imported += 1
                except (IndexError, ValueError):
                    skipped += 1
                    continue
    except Exception as e:
        return f"Error al leer CSV: {e}"
    _save_transactions(txns)
    return f"Importación completada: {imported} transacciones importadas, {skipped} omitidas."


def tool_transactions(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    limit = params.get("limit", 20)
    category = params.get("category")
    from_date = params.get("from_date")
    to_date = params.get("to_date")
    txns = _load_transactions()
    if category:
        txns = [t for t in txns if t.get("category") == category]
    if from_date:
        fd = _parse_date(str(from_date))
        if fd:
            txns = [t for t in txns if t.get("date", "") >= fd]
    if to_date:
        td = _parse_date(str(to_date))
        if td:
            txns = [t for t in txns if t.get("date", "") <= td]
    txns = sorted(txns, key=lambda t: t.get("date", ""), reverse=True)
    if not txns:
        return "No se encontraron transacciones."
    display = txns[:limit]
    lines = []
    for t in display:
        sign = "-" if t["amount"] < 0 else "+"
        lines.append(
            f"{t['id']} | {t['date']} | {sign}${abs(t['amount']):.2f} | "
            f"{t['description'][:40]} [{t['category']}]"
        )
    total_out = sum(t["amount"] for t in display if t["amount"] < 0)
    total_in = sum(t["amount"] for t in display if t["amount"] > 0)
    lines.append(f"\nTotal: {len(txns)} transacciones | Salidas: ${abs(total_out):.2f} | Entradas: ${total_in:.2f}")
    return "\n".join(lines)


def tool_summary(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    now = datetime.now()
    month = params.get("month", now.month)
    year = params.get("year", now.year)
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        return "Mes o año inválido."
    txns = _load_transactions()
    month_txns = [
        t for t in txns
        if _parse_date(t.get("date", ""))
        and _parse_date(t["date"]).startswith(f"{year:04d}-{month:02d}")
    ]
    if not month_txns:
        return f"No hay transacciones para {month:02d}/{year}."
    total_out = sum(t["amount"] for t in month_txns if t["amount"] < 0)
    total_in = sum(t["amount"] for t in month_txns if t["amount"] > 0)
    cat_totals = {}
    for t in month_txns:
        if t["amount"] < 0:
            cat = t.get("category", "otros")
            cat_totals[cat] = cat_totals.get(cat, 0) + abs(t["amount"])
    budgets = _load_budgets()
    lines = [
        f"Resumen {month:02d}/{year}:",
        f"  Total gastos: ${abs(total_out):.2f}",
        f"  Total ingresos: ${total_in:.2f}",
        f"  Balance: ${total_in + total_out:.2f}",
        f"  Transacciones: {len(month_txns)}",
        "",
        "Por categoría:"
    ]
    for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
        budget_info = ""
        if cat in budgets:
            limit = budgets[cat].get("limit", 0)
            if limit > 0:
                pct = (total / limit) * 100
                status = "OK" if pct <= 100 else "EXCEDIDO"
                budget_info = f" (presupuesto: ${limit:.2f} - {pct:.0f}% - {status})"
        lines.append(f"  {cat}: ${total:.2f}{budget_info}")
    return "\n".join(lines)


def tool_categories(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    cats = _load_categories()
    action = params.get("action", "list")
    if action == "add":
        name = params.get("name", "").lower().strip()
        if not name:
            return "Nombre de categoría requerido."
        if name in cats:
            return f"La categoría '{name}' ya existe."
        cats.append(name)
        _save_categories(cats)
        return f"Categoría '{name}' agregada."
    elif action == "remove":
        name = params.get("name", "").lower().strip()
        if name in DEFAULT_CATEGORIES:
            return "No se pueden eliminar categorías predeterminadas."
        if name not in cats:
            return f"Categoría '{name}' no encontrada."
        cats.remove(name)
        _save_categories(cats)
        return f"Categoría '{name}' eliminada."
    return "Categorías:\n" + "\n".join(f"  - {c}" for c in cats)


def tool_budget(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    category = params.get("category")
    limit = params.get("limit")
    if not category:
        budgets = _load_budgets()
        if not budgets:
            return "No hay presupuestos configurados."
        lines = ["Presupuestos:"]
        for cat, data in budgets.items():
            lines.append(f"  {cat}: ${data.get('limit', 0):.2f}/mes")
        return "\n".join(lines)
    budgets = _load_budgets()
    if limit is not None:
        try:
            limit_val = float(limit)
        except (ValueError, TypeError):
            return "Límite inválido."
        budgets[category] = {"limit": limit_val}
        _save_budgets(budgets)
        return f"Presupuesto para '{category}' establecido en ${limit_val:.2f}/mes."
    if category in budgets:
        limit_val = budgets[category].get("limit", 0)
        now = datetime.now()
        txns = _load_transactions()
        month_txns = [
            t for t in txns
            if t.get("category") == category
            and t["amount"] < 0
            and _parse_date(t.get("date", ""))
            and _parse_date(t["date"]).startswith(f"{now.year:04d}-{now.month:02d}")
        ]
        spent = sum(abs(t["amount"]) for t in month_txns)
        pct = (spent / limit_val * 100) if limit_val > 0 else 0
        remaining = limit_val - spent
        status = "OK" if pct <= 100 else "EXCEDIDO"
        return (
            f"Presupuesto '{category}':\n"
            f"  Límite: ${limit_val:.2f}/mes\n"
            f"  Gastado: ${spent:.2f} ({pct:.0f}%)\n"
            f"  Restante: ${remaining:.2f} [{status}]"
        )
    return f"No hay presupuesto para '{category}'. Usa limit= para establecer uno."


def tool_chart(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    chart_type = params.get("type", "monthly")
    txns = _load_transactions()
    if not txns:
        return "No hay transacciones para graficar."
    if chart_type == "monthly":
        monthly = {}
        for t in txns:
            date_str = t.get("date", "")
            if _parse_date(date_str):
                key = date_str[:7]
                monthly[key] = monthly.get(key, 0) + t.get("amount", 0)
        lines = ["Gasto mensual:"]
        for month_key in sorted(monthly.keys()):
            val = monthly[month_key]
            bar_len = min(int(abs(val) / 1000), 40)
            bar = "█" * bar_len
            lines.append(f"  {month_key}: {bar} ${abs(val):.0f}")
        return "\n".join(lines)
    elif chart_type == "category":
        now = datetime.now()
        cat_totals = {}
        for t in txns:
            if t["amount"] < 0 and _parse_date(t.get("date", "")):
                d = _parse_date(t["date"])
                if d and d.startswith(f"{now.year:04d}-{now.month:02d}"):
                    cat = t.get("category", "otros")
                    cat_totals[cat] = cat_totals.get(cat, 0) + abs(t["amount"])
        if not cat_totals:
            return "No hay gastos este mes."
        lines = ["Gastos por categoría (este mes):"]
        max_val = max(cat_totals.values()) if cat_totals else 1
        for cat, val in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            bar_len = int((val / max_val) * 30) if max_val > 0 else 0
            bar = "█" * bar_len
            lines.append(f"  {cat:15s}: {bar} ${val:.0f}")
        return "\n".join(lines)
    elif chart_type == "trend":
        monthly_out = {}
        monthly_in = {}
        for t in txns:
            if _parse_date(t.get("date", "")):
                key = t["date"][:7]
                if t["amount"] < 0:
                    monthly_out[key] = monthly_out.get(key, 0) + abs(t["amount"])
                else:
                    monthly_in[key] = monthly_in.get(key, 0) + t["amount"]
        all_months = sorted(set(list(monthly_out.keys()) + list(monthly_in.keys())))
        lines = ["Tendencia:"]
        for m in all_months:
            out_val = monthly_out.get(m, 0)
            in_val = monthly_in.get(m, 0)
            balance = in_val - out_val
            indicator = "+" if balance >= 0 else ""
            lines.append(f"  {m}: Gasto ${out_val:.0f} | Ingreso ${in_val:.0f} | Balance {indicator}${balance:.0f}")
        return "\n".join(lines)
    return "Tipos disponibles: monthly, category, trend"


def tool_subscriptions(parameters: dict = None, player=None) -> str:
    txns = _load_transactions()
    recurring = [t for t in txns if t.get("recurring")]
    if not recurring:
        seen = {}
        for t in txns:
            desc = t.get("description", "").lower()
            if t["amount"] < 0 and desc:
                if desc not in seen:
                    seen[desc] = {"count": 0, "amount": abs(t["amount"]), "category": t.get("category", "otros")}
                seen[desc]["count"] += 1
        suspected = {k: v for k, v in seen.items() if v["count"] >= 2}
        if not suspected:
            return "No se detectaron suscripciones ni transacciones recurrentes."
        lines = ["Posibles suscripciones (múltiples cobros iguales):"]
        for desc, data in sorted(suspected.items(), key=lambda x: x[1]["count"], reverse=True):
            lines.append(f"  {desc[:40]}: ${data['amount']:.2f} x{data['count']} [{data['category']}]")
        total = sum(d["amount"] * d["count"] for d in suspected.values())
        lines.append(f"\nTotal estimado: ${total:.2f}")
        return "\n".join(lines)
    lines = ["Suscripciones marcadas:"]
    total = 0
    for t in recurring:
        amount = abs(t["amount"])
        total += amount
        lines.append(f"  {t['id']} | {t['date']} | ${amount:.2f} | {t['description']} [{t['category']}]")
    lines.append(f"\nTotal: ${total:.2f}/mes estimado")
    return "\n".join(lines)


def tool_search(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    query = params.get("query", "").lower().strip()
    if not query:
        return "Parámetro 'query' requerido."
    txns = _load_transactions()
    results = [
        t for t in txns
        if query in t.get("description", "").lower()
        or query in t.get("category", "").lower()
        or query in " ".join(t.get("tags", [])).lower()
        or query in t.get("account", "").lower()
    ]
    if not results:
        return f"No se encontraron resultados para '{query}'."
    results = sorted(results, key=lambda t: t.get("date", ""), reverse=True)[:20]
    lines = [f"Resultados para '{query}' ({len(results)}):"]
    for t in results:
        sign = "-" if t["amount"] < 0 else "+"
        lines.append(
            f"  {t['id']} | {t['date']} | {sign}${abs(t['amount']):.2f} | "
            f"{t['description'][:40]} [{t['category']}]"
        )
    return "\n".join(lines)


def tool_export(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    txns = _load_transactions()
    if not txns:
        return "No hay transacciones para exportar."
    out_path = Path(params.get("filepath", str(DATA_DIR / "finance_export.csv")))
    txns = sorted(txns, key=lambda t: t.get("date", ""))
    try:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "amount", "description", "category", "account", "recurring", "tags"])
            for t in txns:
                writer.writerow([
                    t.get("id", ""),
                    t.get("date", ""),
                    t.get("amount", 0),
                    t.get("description", ""),
                    t.get("category", ""),
                    t.get("account", ""),
                    t.get("recurring", False),
                    "|".join(t.get("tags", [])),
                ])
    except Exception as e:
        return f"Error al exportar: {e}"
    return f"Exportadas {len(txns)} transacciones a: {out_path}"


def finance_tracker(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "summary")).lower().strip()
    dispatch = {
        "add_transaction": tool_add_transaction, "import_csv": tool_import_csv,
        "transactions": tool_transactions, "summary": tool_summary,
        "categories": tool_categories, "budget": tool_budget,
        "chart": tool_chart, "subscriptions": tool_subscriptions,
        "search": tool_search, "export": tool_export,
    }
    fn = dispatch.get(action)
    if fn:
        return fn(parameters, player)
    return "Acciones: add_transaction, import_csv, transactions, summary, categories, budget, chart, subscriptions, search, export"
