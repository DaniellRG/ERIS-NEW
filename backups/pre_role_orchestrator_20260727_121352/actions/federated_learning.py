"""
federated_learning.py — Aprendizaje federado: aprender de patrones sin nube.
Permite que ERIS aprenda de patrones locales de forma privada.
"""
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_FEDERATED_DIR = _BASE / "data" / "federated_learning"
_MODEL_FILE = _FEDERATED_DIR / "local_model.json"
_PATTERNS_FILE = _FEDERATED_DIR / "patterns.json"
_TRAINING_LOG = _FEDERATED_DIR / "training_log.json"


def federated_learning(parameters: dict = None, player=None) -> str:
    """
    Aprendizaje federado local.
    Acciones: train, predict, patterns, status, export_model, import_model, 
              merge_models, evaluate, reset, history
    """
    params = parameters or {}
    action = params.get("action", "status").lower()
    _FEDERATED_DIR.mkdir(parents=True, exist_ok=True)

    if action == "train":
        return _train_local(params)
    elif action == "predict":
        return _predict(params)
    elif action == "patterns":
        return _show_patterns(params)
    elif action == "status":
        return _get_status()
    elif action == "export_model":
        return _export_model(params)
    elif action == "import_model":
        return _import_model(params)
    elif action == "merge_models":
        return _merge_models(params)
    elif action == "evaluate":
        return _evaluate_model(params)
    elif action == "reset":
        return _reset_model()
    elif action == "history":
        return _training_history()
    elif action == "features":
        return _extract_features(params)
    elif action == "cluster":
        return _cluster_patterns(params)
    return "Acciones: train, predict, patterns, status, export_model, import_model, merge_models, evaluate, reset, history, features, cluster"


def _train_local(params: dict) -> str:
    data = params.get("data", [])
    category = params.get("category", "general")
    epochs = int(params.get("epochs", 10))

    if not data:
        return "Error: se requiere 'data' (lista de puntos de entrenamiento)"

    model = _load_model()
    patterns = _load_patterns()

    trained_count = 0
    for item in data:
        if isinstance(item, (int, float, str)):
            item = {"text": str(item), "label": "auto"}
        features = _extract_features_from_item(item)
        label = item.get("label", "unknown")
        pattern_key = _hash_features(features)

        if pattern_key in patterns:
            existing = patterns[pattern_key]
            existing["count"] = existing.get("count", 0) + 1
            existing["confidence"] = min(0.99, existing.get("confidence", 0.5) + 0.05)
            existing["last_seen"] = datetime.now().isoformat()
        else:
            patterns[pattern_key] = {
                "features": features,
                "label": label,
                "category": category,
                "count": 1,
                "confidence": 0.5,
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }
        trained_count += 1

    model["total_trained"] = model.get("total_trained", 0) + trained_count
    model["last_training"] = datetime.now().isoformat()
    model["categories"] = list(set(p.get("category", "") for p in patterns.values()))
    model["pattern_count"] = len(patterns)

    _save_model(model)
    _save_patterns(patterns)
    _log_training("train", trained_count, category)

    return "Entrenado {} patrones (categoría: {}). Total modelo: {} patrones".format(
        trained_count, category, len(patterns))


def _predict(params: dict) -> str:
    input_data = params.get("input", "")
    if not input_data:
        return "Error: se requiere 'input'"

    features = _extract_features_from_item({"text": input_data})
    patterns = _load_patterns()

    if not patterns:
        return "Modelo sin patrones. Entrena primero con action: train"

    matches = []
    for key, pattern in patterns.items():
        similarity = _calculate_similarity(features, pattern.get("features", {}))
        if similarity > 0.3:
            matches.append({
                "label": pattern.get("label"),
                "confidence": pattern.get("confidence", 0.5) * similarity,
                "category": pattern.get("category"),
                "count": pattern.get("count", 1),
            })

    matches.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    if not matches:
        return "No se encontraron patrones similares para: {}".format(input_data[:50])

    lines = ["Predicciones para '{}' ({} matches):".format(input_data[:30], len(matches))]
    for m in matches[:5]:
        lines.append("  {} | conf: {:.2f} | cat: {} | visto {}x".format(
            m.get("label"), m.get("confidence"), m.get("category"), m.get("count")))
    return "\n".join(lines)


def _show_patterns(params: dict) -> str:
    patterns = _load_patterns()
    if not patterns:
        return "No hay patrones registrados"

    limit = int(params.get("limit", 20))
    category = params.get("category", "")

    filtered = list(patterns.values())
    if category:
        filtered = [p for p in filtered if p.get("category") == category]

    filtered.sort(key=lambda x: x.get("count", 0), reverse=True)

    lines = ["Patrones ({} total, mostrando {}):".format(len(filtered), min(limit, len(filtered)))]
    for p in filtered[:limit]:
        lines.append("  {} | cat: {} | conf: {:.2f} | visto {}x".format(
            p.get("label", "?"), p.get("category", "?"),
            p.get("confidence", 0), p.get("count", 0)))
    return "\n".join(lines)


def _get_status() -> str:
    model = _load_model()
    patterns = _load_patterns()
    return "Federated Learning: {} patrones | {} entrenados | Categorías: {} | Último entrenamiento: {}".format(
        len(patterns), model.get("total_trained", 0),
        ", ".join(model.get("categories", [])) or "ninguna",
        model.get("last_training", "nunca")[:16])


def _export_model(params: dict) -> str:
    model = _load_model()
    patterns = _load_patterns()
    export = {"model": model, "patterns": patterns, "exported": datetime.now().isoformat()}
    export_path = _BASE / "data" / "federated_export.json"
    export_path.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Modelo exportado: {} patrones → {}".format(len(patterns), str(export_path))


def _import_model(params: dict) -> str:
    filepath = params.get("filepath", "")
    if not filepath:
        return "Error: se requiere 'filepath'"
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        imported_patterns = data.get("patterns", {})
        patterns = _load_patterns()

        merged = 0
        for key, pattern in imported_patterns.items():
            if key not in patterns:
                patterns[key] = pattern
                merged += 1
            else:
                patterns[key]["count"] = max(patterns[key].get("count", 0), pattern.get("count", 0))
                patterns[key]["confidence"] = max(patterns[key].get("confidence", 0), pattern.get("confidence", 0))

        _save_patterns(patterns)
        return "Modelo importado: {} nuevos patrones, {} actualizados".format(merged, len(imported_patterns) - merged)
    except Exception as e:
        return "Error importando: {}".format(str(e))


def _merge_models(params: dict) -> str:
    other_patterns = params.get("patterns", {})
    if not other_patterns:
        return "Error: se requiere 'patterns' (dict de patrones)"

    patterns = _load_patterns()
    merged = 0
    updated = 0

    for key, pattern in other_patterns.items():
        if key not in patterns:
            patterns[key] = pattern
            merged += 1
        else:
            if pattern.get("confidence", 0) > patterns[key].get("confidence", 0):
                patterns[key]["confidence"] = pattern["confidence"]
            patterns[key]["count"] = patterns[key].get("count", 0) + pattern.get("count", 0)
            updated += 1

    _save_patterns(patterns)
    return "Merge: {} nuevos, {} actualizados. Total: {}".format(merged, updated, len(patterns))


def _evaluate_model(params: dict) -> str:
    test_data = params.get("test_data", [])
    if not test_data:
        return "Error: se requiere 'test_data' (lista de {input, expected})"

    correct = 0
    total = len(test_data)
    for item in test_data:
        input_text = item.get("input", "")
        expected = item.get("expected", "")
        features = _extract_features_from_item({"text": input_text})
        patterns = _load_patterns()

        best_match = None
        best_sim = 0
        for key, pattern in patterns.items():
            sim = _calculate_similarity(features, pattern.get("features", {}))
            if sim > best_sim:
                best_sim = sim
                best_match = pattern.get("label", "")

        if best_match == expected:
            correct += 1

    accuracy = (correct / total * 100) if total else 0
    return "Evaluación: {}/{} correctos ({:.1f}% accuracy)".format(correct, total, accuracy)


def _reset_model() -> str:
    _save_model({"total_trained": 0, "categories": [], "pattern_count": 0})
    _save_patterns({})
    return "Modelo reseteado"


def _training_history() -> str:
    if _TRAINING_LOG.exists():
        try:
            log = json.loads(_TRAINING_LOG.read_text(encoding="utf-8"))
            entries = log.get("entries", [])
            lines = ["Historial de entrenamiento ({} sesiones):".format(len(entries))]
            for e in entries[-10:]:
                lines.append("  {} | {} patrones | {}".format(
                    e.get("timestamp", "?")[:16], e.get("count", 0), e.get("category", "?")))
            return "\n".join(lines)
        except Exception:
            pass
    return "No hay historial de entrenamiento"


def _extract_features(params: dict) -> str:
    data = params.get("data", "")
    if not data:
        return "Error: se requiere 'data'"
    features = _extract_features_from_item({"text": data})
    return "Features: {}".format(json.dumps(features, indent=2))


def _cluster_patterns(params: dict) -> str:
    patterns = _load_patterns()
    if not patterns:
        return "No hay patrones para clustering"

    clusters = {}
    for key, pattern in patterns.items():
        cat = pattern.get("category", "unknown")
        clusters.setdefault(cat, []).append(pattern.get("label", "?"))

    lines = ["Clusters por categoría:"]
    for cat, labels in sorted(clusters.items(), key=lambda x: -len(x[1])):
        lines.append("  {} ({}): {}".format(cat, len(labels), ", ".join(labels[:5])))
    return "\n".join(lines)


def _extract_features_from_item(item):
    text = str(item.get("text", item.get("content", ""))).lower()
    return {
        "length": len(text),
        "words": len(text.split()),
        "has_question": "?" in text,
        "has_exclamation": "!" in text,
        "first_word": text.split()[0] if text.split() else "",
        "char_ratio": sum(1 for c in text if c.isalpha()) / max(len(text), 1),
    }


def _hash_features(features):
    feature_str = json.dumps(features, sort_keys=True)
    return hashlib.md5(feature_str.encode()).hexdigest()[:12]


def _calculate_similarity(f1, f2):
    if not f1 or not f2:
        return 0
    common = sum(1 for k in f1 if k in f2 and f1[k] == f2[k])
    total = max(len(set(f1.keys()) | set(f2.keys())), 1)
    return common / total


def _load_model():
    if _MODEL_FILE.exists():
        try:
            return json.loads(_MODEL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_trained": 0, "categories": [], "pattern_count": 0}


def _save_model(model):
    _MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MODEL_FILE.write_text(json.dumps(model, indent=2), encoding="utf-8")


def _load_patterns():
    if _PATTERNS_FILE.exists():
        try:
            return json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_patterns(patterns):
    _PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PATTERNS_FILE.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")


def _log_training(action, count, category):
    log = {"entries": []}
    if _TRAINING_LOG.exists():
        try:
            log = json.loads(_TRAINING_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    log.setdefault("entries", []).append({
        "action": action, "count": count, "category": category,
        "timestamp": datetime.now().isoformat()
    })
    log["entries"] = log["entries"][-100:]
    _TRAINING_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
