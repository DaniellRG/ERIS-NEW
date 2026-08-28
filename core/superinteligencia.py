"""
core/superinteligencia.py — Puerta de entrada unificada para las 36 features.

Todas las funciones se registran como tools en tool_declarations.py.
Este archivo las dispatcha a los módulos correctos.
"""
from __future__ import annotations

import json


def reflection(parameters: dict = None) -> str:
    """Reflexión profunda o rápida."""
    params = parameters or {}
    task = params.get("task", "")
    context = params.get("context", "")
    quick = params.get("quick", False)

    if quick:
        from core.reflection import quick_check
        return quick_check(task)

    from core.reflection import reflect
    result = reflect(task, context)
    return json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)


def skill_recommender(parameters: dict = None) -> str:
    """Recomienda skills para una tarea."""
    params = parameters or {}
    query = params.get("query", "")
    from core.skill_recommender import recommend_skills
    result = recommend_skills(query)
    if isinstance(result, list):
        return json.dumps([{"name": s.get("name", ""), "score": s.get("score", 0),
                            "reason": s.get("reason", "")} for s in result[:5]],
                           ensure_ascii=False, indent=2)
    return str(result)


def progressive_context(parameters: dict = None) -> str:
    """Construye contexto progresivo."""
    params = parameters or {}
    task = params.get("task", "")
    level = int(params.get("level", 2))
    from core.progressive_context import build_progressive_context
    result = build_progressive_context(query=task, level=level)
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


def tool_cache(parameters: dict = None) -> str:
    """Cache de resultados de tools."""
    params = parameters or {}
    action = params.get("action", "stats")
    tool = params.get("tool", "")
    args_raw = params.get("args", "{}")
    from core.tool_cache import get_tool_cache
    cache = get_tool_cache()

    if action == "stats":
        stats = cache.stats()
        return json.dumps(stats, ensure_ascii=False, indent=2)
    elif action == "get":
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except Exception:
            args = {}
        result = cache.get(tool, args)
        return str(result) if result else "No encontrado en cache"
    elif action == "set":
        result = params.get("result", "")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except Exception:
            args = {}
        cache.set(tool, args, result)
        return "Resultado cacheado"
    elif action == "clear":
        cache.clear()
        return "Cache limpiado"
    return "Acción desconocida"


def verification_layer(parameters: dict = None) -> str:
    """Verifica output de tool."""
    params = parameters or {}
    tool_name = params.get("tool_name", "")
    output = params.get("output", "")
    from core.verification_layer import verify_tool_output, maybe_fix_output

    if not tool_name:
        return "Parámetro tool_name requerido"

    verification = verify_tool_output(tool_name, output)
    fixed = maybe_fix_output(tool_name, output, verification)
    return json.dumps({
        "valid": verification.get("valid", False),
        "message": verification.get("message", ""),
        "fixed": fixed != output,
    }, ensure_ascii=False, indent=2)


def plan_adaptation(parameters: dict = None) -> str:
    """Adapta un plan ante fallos."""
    params = parameters or {}
    plan = params.get("plan", [])
    failure = params.get("failure", "")
    context = params.get("context", "")
    goal = params.get("goal", "")
    if isinstance(plan, str):
        plan = [{"task": plan}]
    failed_step = {"task": failure or "tarea fallida"}
    from core.plan_adaptation import adapt_plan
    try:
        result = adapt_plan(plan, failed_step, failure, goal)
        if isinstance(result, list):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    except TypeError:
        return json.dumps({"error": "plan debe ser lista de pasos"}, ensure_ascii=False)


def prompt_compressor(parameters: dict = None) -> str:
    """Comprime historial de conversación."""
    params = parameters or {}
    history = params.get("history", "")
    keep_recent = int(params.get("keep_recent", 6))
    max_tokens = int(params.get("max_tokens", 2000))
    from core.prompt_compressor import compress_history
    if isinstance(history, str):
        messages = [{"role": "user", "content": history}]
    else:
        messages = history
    compressed = compress_history(messages, keep_recent=keep_recent, max_tokens=max_tokens)
    if isinstance(compressed, list):
        return json.dumps(compressed, ensure_ascii=False, indent=2)
    return str(compressed)


def knowledge_distiller(parameters: dict = None) -> str:
    """Extrae patrones de conocimiento."""
    params = parameters or {}
    interaction = params.get("interaction", "")
    goal = params.get("goal", "")
    result = params.get("result", "")
    from core.knowledge_distillation import extract_patterns
    patterns = extract_patterns(interaction, goal, result)
    if isinstance(patterns, list):
        return json.dumps(patterns, ensure_ascii=False, indent=2)
    return str(patterns)


def agent_as_tool(parameters: dict = None) -> str:
    """Delega a un sub-agente."""
    params = parameters or {}
    task = params.get("task", "")
    context = params.get("context", "")
    from core.agent_as_tool import delegate_smart
    return delegate_smart([task], context)


def batch_executor(parameters: dict = None) -> str:
    """Ejecuta tareas en paralelo."""
    params = parameters or {}
    tasks_raw = params.get("tasks", "[]")
    try:
        tasks = json.loads(tasks_raw) if isinstance(tasks_raw, str) else tasks_raw
    except Exception:
        tasks = [{"task": tasks_raw}]
    if isinstance(tasks, dict):
        tasks = [tasks]
    normalized = []
    for t in tasks:
        if isinstance(t, dict):
            if "name" not in t:
                t = {"name": t.get("task", t.get("tool", "shell")), "arguments": t}
            if not isinstance(t.get("arguments", {}), dict):
                t["arguments"] = {"command": str(t["arguments"])}
            normalized.append(t)
        else:
            normalized.append({"name": "shell", "arguments": {"command": str(t)}})
    from core.batch_executor import execute_batch
    results = execute_batch(normalized, max_workers=int(params.get("max_workers", 4)))
    return json.dumps(results, ensure_ascii=False, indent=2) if isinstance(results, dict) else str(results)


def cost_tracker(parameters: dict = None) -> str:
    """Tracking de costos."""
    params = parameters or {}
    action = params.get("action", "session")
    from core.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()

    if action == "session":
        return json.dumps(tracker.get_session_summary(), ensure_ascii=False, indent=2)
    elif action == "daily":
        return json.dumps(tracker.get_daily_summary(), ensure_ascii=False, indent=2)
    elif action == "status":
        return tracker.format_status()
    elif action == "record":
        provider = params.get("provider", "unknown")
        model = params.get("model", "unknown")
        inp = int(params.get("input_tokens", 0))
        out = int(params.get("output_tokens", 0))
        tracker.record_request(provider, model, input_tokens=inp, output_tokens=out)
        return "Costo registrado"
    return "Acción desconocida"


def error_recovery(parameters: dict = None) -> str:
    """Recuperación de errores."""
    params = parameters or {}
    action = params.get("action", "diagnose")
    tool_name = params.get("tool_name", "")
    error = params.get("error", "")
    args_raw = params.get("args", "{}")
    try:
        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
    except Exception:
        args = {}
    from core.error_recovery import get_error_recovery
    recovery = get_error_recovery()

    if action == "diagnose":
        result = recovery.diagnose(error, tool_name, args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "recover":
        result = recovery.try_recovery(error, tool_name, args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    return "Acción desconocida"


def metrics_dashboard(parameters: dict = None) -> str:
    """Dashboard de métricas."""
    params = parameters or {}
    action = params.get("action", "summary")
    from core.metrics_dashboard import get_dashboard
    dashboard = get_dashboard()

    if action == "summary":
        return json.dumps(dashboard.get_summary(), ensure_ascii=False, indent=2)
    elif action == "tools":
        tool = params.get("tool", "")
        return json.dumps(dashboard.get_tool_stats(tool), ensure_ascii=False, indent=2)
    elif action == "format":
        return dashboard.format_dashboard()
    return "Acción desconocida"


def intent_classifier(parameters: dict = None) -> str:
    """Clasifica intención."""
    params = parameters or {}
    query = params.get("query", "")
    from core.intent_classifier import classify_intent
    result = classify_intent(query)
    return json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)


def conversation_brancher(parameters: dict = None) -> str:
    """Genera branches de conversación."""
    params = parameters or {}
    question = params.get("question", "")
    goal = params.get("goal", question)
    context = params.get("context", "")
    from core.conversation_branching import generate_branches
    branches = generate_branches(goal, context)
    if isinstance(branches, list):
        return json.dumps(branches, ensure_ascii=False, indent=2)
    return str(branches)


def auto_documenter(parameters: dict = None) -> str:
    """Genera documentación."""
    params = parameters or {}
    action = params.get("action", "analyze")
    path = params.get("path", "")
    changes_raw = params.get("changes", "[]")

    if action == "analyze":
        from core.auto_documentation import analyze_code_for_docs
        result = analyze_code_for_docs(path)
        return json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)
    elif action == "changelog":
        try:
            changes = json.loads(changes_raw) if isinstance(changes_raw, str) else changes_raw
        except Exception:
            changes = [{"type": "changed", "description": path or "cambios"}]
        from core.auto_documentation import generate_changelog
        result = generate_changelog(changes)
        return str(result)
    elif action == "migrate":
        try:
            changes = json.loads(changes_raw) if isinstance(changes_raw, str) else changes_raw
        except Exception:
            changes = [{"type": "changed", "description": path or "cambios"}]
        from core.auto_documentation import suggest_migration
        result = suggest_migration(changes)
        return str(result) if result else "Sin migración sugerida"
    return "Acción desconocida"


def tool_dep_graph(parameters: dict = None) -> str:
    """Grafo de dependencias de tools."""
    params = parameters or {}
    action = params.get("action", "critical")
    tool = params.get("tool", "")
    from core.tool_dependency_graph import get_dependency_graph
    graph = get_dependency_graph()

    if action == "critical":
        critical = graph.get_critical_tools()
        return json.dumps(critical, ensure_ascii=False, indent=2)
    elif action == "parallel":
        groups = graph.get_parallel_groups()
        return json.dumps(groups, ensure_ascii=False, indent=2)
    elif action == "deps" and tool:
        affected = graph.get_affected_tools(tool)
        return json.dumps(affected, ensure_ascii=False, indent=2)
    elif action == "format":
        return graph.format_graph()
    return "Acción desconocida"


def smart_retry(parameters: dict = None) -> str:
    """Reintento inteligente."""
    params = parameters or {}
    action = params.get("action", "execute")
    tool = params.get("tool", "")
    args_raw = params.get("args", "{}")

    if action == "execute":
        from core.error_recovery import get_error_recovery
        recovery = get_error_recovery()
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except Exception:
            args = {}
        result = recovery.try_recovery("fallo al ejecutar %s" % tool, tool, args)
        return json.dumps(result, ensure_ascii=False, indent=2) if result else "No se pudo recuperar"
    elif action == "classify":
        error = params.get("error", "")
        from core.smart_retry import classify_error
        return classify_error(error)
    return "Acción desconocida"


def self_evolving_prompts(parameters: dict = None) -> str:
    """Auto-evolución de prompts."""
    params = parameters or {}
    action = params.get("action", "learn")
    from core.self_evolving_prompts import record_and_learn, get_evolved_rules

    if action == "learn":
        question = params.get("question", "")
        failed = params.get("failed_answer", "")
        feedback = params.get("feedback", "")
        result = record_and_learn(question, failed, feedback)
        return str(result)
    elif action == "rules":
        rules = get_evolved_rules()
        return json.dumps(rules, ensure_ascii=False, indent=2) if isinstance(rules, list) else str(rules)
    elif action == "suffix":
        from core.self_evolving_prompts import build_evolved_prompt_suffix
        return build_evolved_prompt_suffix()
    return "Acción desconocida"


def semantic_deduplicator(parameters: dict = None) -> str:
    """Deduplicación semántica."""
    params = parameters or {}
    action = params.get("action", "all")
    from core.semantic_deduplication import deduplicate_episodic, deduplicate_semantic, deduplicate_all

    if action == "episodic":
        return json.dumps(deduplicate_episodic(), ensure_ascii=False, indent=2)
    elif action == "semantic":
        return json.dumps(deduplicate_semantic(), ensure_ascii=False, indent=2)
    elif action == "all":
        return deduplicate_all()
    return "Acción desconocida"


def adaptive_temperature(parameters: dict = None) -> str:
    """Temperatura dinámica."""
    params = parameters or {}
    query = params.get("query", "")
    override = params.get("override")
    from core.adaptive_temperature import get_temperature
    result = get_temperature(query, override=override)
    return json.dumps(result, ensure_ascii=False, indent=2)


def task_tree(parameters: dict = None) -> str:
    """Árbol de tareas."""
    params = parameters or {}
    action = params.get("action", "decompose")
    goal = params.get("goal", "")
    task_id = params.get("task_id", "")
    result_text = params.get("result", "")

    if action == "decompose":
        from core.task_decomposition_tree import decompose_goal
        tree = decompose_goal(goal, params.get("context", ""))
        task_tree._active = tree
        return tree.format_tree()
    elif action == "status":
        tree = getattr(task_tree, "_active", None)
        if tree:
            return json.dumps(tree.get_summary(), ensure_ascii=False, indent=2)
        return "No hay árbol activo"
    elif action == "mark_completed" and task_id:
        tree = getattr(task_tree, "_active", None)
        if tree:
            tree.mark_completed(task_id, result_text)
            return "Tarea completada"
        return "No hay árbol activo"
    elif action == "mark_failed" and task_id:
        tree = getattr(task_tree, "_active", None)
        if tree:
            tree.mark_failed(task_id, result_text)
            return "Tarea marcada como fallida"
        return "No hay árbol activo"
    return "Acción desconocida"


def proactive_suggester(parameters: dict = None) -> str:
    """Sugerencias proactivas."""
    params = parameters or {}
    task = params.get("task", "")
    tool_used = params.get("tool_used", "")
    result = params.get("result", "")
    from core.proactive_suggestions import suggest_next_steps, format_suggestions
    sugs = suggest_next_steps(task, result, tool_used)
    return format_suggestions(sugs)


def conversation_replayer(parameters: dict = None) -> str:
    """Reproduce sesiones."""
    params = parameters or {}
    action = params.get("action", "list")
    session_id = params.get("session_id", "")

    if action == "list":
        from core.conversation_replay import list_sessions
        sessions = list_sessions()
        return json.dumps(sessions, ensure_ascii=False, indent=2)
    elif action == "view":
        from core.conversation_replay import replay_session
        return replay_session(session_id)
    elif action == "tools":
        from core.conversation_replay import extract_tool_sequence
        tools = extract_tool_sequence(session_id)
        return json.dumps(tools, ensure_ascii=False, indent=2)
    return "Acción desconocida"


def smart_file_organizer(parameters: dict = None) -> str:
    """Organizador de archivos."""
    params = parameters or {}
    action = params.get("action", "stats")
    path = params.get("path", "")
    directory = params.get("directory", ".")

    if action == "related":
        from core.smart_file_organizer import suggest_related_files
        result = suggest_related_files(path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "orphans":
        from core.smart_file_organizer import find_orphan_files
        result = find_orphan_files(directory)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "stats":
        from core.smart_file_organizer import get_usage_stats
        return json.dumps(get_usage_stats(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def test_generator(parameters: dict = None) -> str:
    """Generador de tests."""
    params = parameters or {}
    action = params.get("action", "analyze")
    path = params.get("path", "")

    if action == "analyze":
        from core.test_generator import analyze_code_for_tests
        result = analyze_code_for_tests(path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "generate":
        from core.test_generator import generate_tests_for_file
        return generate_tests_for_file(path)
    return "Acción desconocida"


def context_optimizer(parameters: dict = None) -> str:
    """Optimizador de contexto."""
    params = parameters or {}
    action = params.get("action", "budget")
    provider = params.get("provider", "openrouter")
    complexity = int(params.get("complexity", 1))
    messages_raw = params.get("messages", "")

    if action == "budget":
        from core.context_window_optimizer import calculate_budget
        budget = calculate_budget(provider, task_complexity=complexity)
        return json.dumps(budget, ensure_ascii=False, indent=2)
    elif action == "optimize" and messages_raw:
        try:
            messages = json.loads(messages_raw)
        except Exception:
            messages = [{"role": "user", "content": messages_raw}]
        from core.context_window_optimizer import optimize_messages, calculate_budget
        budget = calculate_budget(provider, task_complexity=complexity)
        total_budget = budget.get("total_budget") or budget.get("max_tokens", 8000)
        optimized = optimize_messages(messages, total_budget)
        return json.dumps(optimized, ensure_ascii=False, indent=2)
    return "Acción desconocida"


def backup_prioritizer(parameters: dict = None) -> str:
    """Priorizador de backups."""
    params = parameters or {}
    action = params.get("action", "stats")
    directory = params.get("directory", ".")
    path = params.get("path", "")

    if action == "prioritize":
        from core.backup_prioritizer import prioritize_files
        result = prioritize_files(directory)
        return json.dumps(result[:10], ensure_ascii=False, indent=2)
    elif action == "mark":
        from core.backup_prioritizer import mark_backed_up
        mark_backed_up(path)
        return "Marcado como respaldado"
    elif action == "stats":
        from core.backup_prioritizer import get_backup_stats
        return json.dumps(get_backup_stats(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def skill_creator(parameters: dict = None) -> str:
    """Creador de skills."""
    params = parameters or {}
    action = params.get("action", "detect")
    pattern_raw = params.get("pattern", "")
    name = params.get("name", "")

    if action == "detect":
        from core.skill_auto_creator import detect_repetitive_patterns
        patterns = detect_repetitive_patterns()
        return json.dumps(patterns, ensure_ascii=False, indent=2)
    elif action == "create" and pattern_raw:
        try:
            pattern = json.loads(pattern_raw)
        except Exception:
            pattern = {"pattern": pattern_raw, "tools": ["shell"], "count": 3, "suggested_name": name or "auto-skill"}
        from core.skill_auto_creator import create_skill_from_pattern
        path = create_skill_from_pattern(pattern, name=name)
        return "Skill creado en: %s" % path
    elif action == "suggest":
        from core.skill_auto_creator import suggest_skills
        return json.dumps(suggest_skills(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def error_pattern_db(parameters: dict = None) -> str:
    """Base de errores y soluciones."""
    params = parameters or {}
    action = params.get("action", "stats")
    error = params.get("error", "")
    tool = params.get("tool", "")
    solution = params.get("solution", "")
    error_id = params.get("error_id", "")

    if action == "record":
        from core.error_pattern_db import record_error
        result = record_error(error, tool=tool)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "solution":
        from core.error_pattern_db import record_solution
        record_solution(error_id, solution, success=True)
        return "Solución registrada"
    elif action == "find":
        from core.error_pattern_db import find_solution
        result = find_solution(error)
        return json.dumps(result, ensure_ascii=False, indent=2) if result else "Sin solución conocida"
    elif action == "stats":
        from core.error_pattern_db import get_error_stats
        return json.dumps(get_error_stats(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def session_debugger(parameters: dict = None) -> str:
    """Debugger de sesiones."""
    params = parameters or {}
    action = params.get("action", "analyze")
    session_id = params.get("session_id", "")
    session2 = params.get("session2", "")

    if action == "analyze":
        from core.session_replay_debugger import format_session_report
        return format_session_report(session_id)
    elif action == "compare" and session2:
        from core.session_replay_debugger import compare_sessions
        result = compare_sessions(session_id, session2)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "report":
        from core.session_replay_debugger import format_session_report
        return format_session_report(session_id)
    return "Acción desconocida"


def capability_assessor(parameters: dict = None) -> str:
    """Auto-evaluación de capacidades."""
    params = parameters or {}
    action = params.get("action", "score")
    tool = params.get("tool", "")
    success = params.get("success", True)

    if action == "score":
        from core.capability_self_assessment import get_overall_score
        return json.dumps(get_overall_score(), ensure_ascii=False, indent=2)
    elif action == "weak":
        from core.capability_self_assessment import get_weak_areas
        return json.dumps(get_weak_areas(), ensure_ascii=False, indent=2)
    elif action == "full":
        from core.capability_self_assessment import format_assessment
        return format_assessment()
    elif action == "record":
        from core.capability_self_assessment import record_tool_usage
        record_tool_usage(tool, success)
        return "Uso registrado"
    return "Acción desconocida"


# ── Batch 2: Features #37-#45 ──


def feedback_learner(parameters: dict = None) -> str:
    """Aprende del feedback del usuario."""
    params = parameters or {}
    action = params.get("action", "stats")

    if action == "record":
        from core.user_feedback_learner import record_feedback
        record_feedback(
            params.get("response_summary", ""),
            params.get("positive", True),
            params.get("topic", "general"),
            params.get("style", ""),
        )
        return "Feedback registrado"
    elif action == "stats":
        from core.user_feedback_learner import get_feedback_stats
        return json.dumps(get_feedback_stats(), ensure_ascii=False, indent=2)
    elif action == "style":
        from core.user_feedback_learner import get_preferred_style
        return json.dumps(get_preferred_style(), ensure_ascii=False, indent=2)
    elif action == "report":
        from core.user_feedback_learner import format_feedback_report
        return format_feedback_report()
    return "Acción desconocida"


def self_explainer(parameters: dict = None) -> str:
    """Explica decisiones del agente."""
    params = parameters or {}
    action = params.get("action", "explain")

    if action == "explain":
        from core.self_explainer import explain_decision
        alts = [a.strip() for a in params.get("alternatives", "").split(",") if a.strip()]
        return explain_decision(params.get("decision", ""), alts)
    elif action == "tool_choice":
        from core.self_explainer import explain_tool_choice
        return explain_tool_choice(params.get("task", ""), params.get("tool_name", ""))
    elif action == "error":
        from core.self_explainer import explain_error_handling
        return explain_error_handling(params.get("error", ""), params.get("task", ""))
    return "Acción desconocida"


def meta_reasoner(parameters: dict = None) -> str:
    """Analiza calidad del razonamiento."""
    params = parameters or {}
    action = params.get("action", "analyze")

    if action == "analyze":
        from core.meta_reasoner import meta_analyze
        result = meta_analyze(
            params.get("reasoning", ""),
            params.get("decision", ""),
            params.get("context", ""),
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "quick":
        from core.meta_reasoner import quick_meta_check
        return quick_meta_check(params.get("reasoning", ""))
    return "Acción desconocida"


def multi_agent(parameters: dict = None) -> str:
    """Orquestación multi-agente."""
    params = parameters or {}
    action = params.get("action", "run")
    roles = [r.strip() for r in params.get("roles", "researcher,reviewer").split(",") if r.strip()]
    workflow_raw = params.get("workflow", "")

    from core.multi_agent_orchestrator import orchestrate_task

    if action == "run":
        result = orchestrate_task(params.get("task", ""), roles, None, params.get("context", ""))
        return result
    elif action == "workflow":
        workflow = None
        if workflow_raw:
            try:
                workflow = json.loads(workflow_raw)
            except Exception:
                workflow = None
        result = orchestrate_task(params.get("task", ""), roles, workflow, params.get("context", ""))
        return result
    elif action == "status":
        from core.multi_agent_orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        return json.dumps(orchestrator.get_status(), ensure_ascii=False, indent=2) if hasattr(orchestrator, "get_status") else "Orquestador inicializado"
    return "Acción desconocida"


def learning_curriculum(parameters: dict = None) -> str:
    """Currículum de auto-mejora."""
    params = parameters or {}
    action = params.get("action", "next")

    if action == "next":
        from core.learning_curriculum import get_next_exercise, initialize_curriculum
        initialize_curriculum()
        result = get_next_exercise(params.get("category"))
        return json.dumps(result or {"message": "Todos los ejercicios completados"}, ensure_ascii=False, indent=2)
    elif action == "complete":
        from core.learning_curriculum import complete_exercise
        complete_exercise(
            params.get("category", "coding"),
            params.get("exercise", ""),
            params.get("success", True),
        )
        return "Ejercicio registrado"
    elif action == "progress":
        from core.learning_curriculum import initialize_curriculum, format_curriculum
        initialize_curriculum()
        return format_curriculum()
    elif action == "focus":
        from core.learning_curriculum import initialize_curriculum, suggest_focus
        initialize_curriculum()
        focus = suggest_focus()
        return "Enfocarse en: %s" % (focus or "todas las categorías están al 100%%")
    return "Acción desconocida"


def session_analytics(parameters: dict = None) -> str:
    """Analítica de sesiones."""
    params = parameters or {}
    action = params.get("action", "patterns")

    if action == "patterns":
        from core.session_analytics import format_analytics
        return format_analytics()
    elif action == "daily":
        from core.session_analytics import get_daily_report
        return json.dumps(get_daily_report(), ensure_ascii=False, indent=2)
    elif action == "record":
        from core.session_analytics import record_session
        tools = [t.strip() for t in params.get("tools", "").split(",") if t.strip()]
        topics = [t.strip() for t in params.get("topics", "").split(",") if t.strip()]
        record_session(
            params.get("session_id", ""),
            params.get("duration", 0),
            params.get("messages", 0),
            tools,
            topics,
        )
        return "Sesión registrada"
    return "Acción desconocida"


def knowledge_verifier(parameters: dict = None) -> str:
    """Verificación de hechos."""
    params = parameters or {}
    action = params.get("action", "verify")

    if action == "verify":
        from core.knowledge_verifier import verify_claim, format_verdict
        result = verify_claim(params.get("claim", ""), params.get("context", ""))
        return format_verdict(result)
    elif action == "batch":
        from core.knowledge_verifier import batch_verify
        claims = [c.strip() for c in params.get("claims", "").split("\n") if c.strip()]
        results = batch_verify(claims)
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif action == "safe":
        from core.knowledge_verifier import verify_before_stating
        result = verify_before_stating(params.get("claim", ""))
        return "SEGURO afirmar" if result.get("safe_to_state") else (
            "RIESGO de alucinación: %s" % result.get("verdict", "unverifiable")
        )
    return "Acción desconocida"


def resource_optimizer(parameters: dict = None) -> str:
    """Optimización de recursos."""
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        from core.resource_optimizer import format_resources, get_system_resources
        return format_resources(get_system_resources())
    elif action == "clean":
        from core.resource_optimizer import clean_temp_files
        dry = params.get("dry_run", True)
        result = clean_temp_files(dry_run=dry)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "optimize":
        from core.resource_optimizer import optimize_memory
        result = optimize_memory()
        return result.get("message", "Optimizado")
    elif action == "suggest":
        from core.resource_optimizer import get_optimization_suggestions
        suggestions = get_optimization_suggestions()
        if not suggestions:
            return "Sistema optimizado, sin sugerencias"
        return json.dumps(suggestions, ensure_ascii=False, indent=2)
    return "Acción desconocida"


def dream_consolidator(parameters: dict = None) -> str:
    """Consolidación tipo sueño."""
    params = parameters or {}
    action = params.get("action", "consolidate")

    if action == "consolidate":
        from core.dream_consolidation import consolidate_memories, format_dream_report
        result = consolidate_memories()
        return format_dream_report(result)
    elif action == "log":
        from core.dream_consolidation import get_dream_log
        log = get_dream_log()
        return json.dumps(log[-5:] if log else [], ensure_ascii=False, indent=2)
    return "Acción desconocida"


# ── Batch 3: Features #46-#53 ──


def goal_tracker(parameters: dict = None) -> str:
    """Seguimiento de objetivos a largo plazo."""
    params = parameters or {}
    action = params.get("action", "summary")
    goal_id = params.get("goal_id", "")

    if action == "create":
        from core.goal_tracker import create_goal
        subtasks = [s for s in params.get("subtasks", "").split("\n") if s.strip()]
        milestones = [m for m in params.get("milestones", "").split("\n") if m.strip()]
        goal = create_goal(
            params.get("title", ""),
            params.get("description", ""),
            params.get("priority", "medium"),
            subtasks,
            milestones,
        )
        return json.dumps(goal, ensure_ascii=False, indent=2)
    elif action == "update":
        from core.goal_tracker import update_goal
        result = update_goal(goal_id, params.get("state"), params.get("progress"), params.get("note", ""))
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "complete_st":
        from core.goal_tracker import complete_subtask
        result = complete_subtask(goal_id, params.get("subtask_index", 0))
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "milestone":
        from core.goal_tracker import reach_milestone
        result = reach_milestone(goal_id, params.get("milestone_index", 0))
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "active":
        from core.goal_tracker import get_active_goals
        return json.dumps(get_active_goals(), ensure_ascii=False, indent=2)
    elif action == "stalled":
        from core.goal_tracker import get_stalled_goals
        return json.dumps(get_stalled_goals(), ensure_ascii=False, indent=2)
    elif action == "next":
        from core.goal_tracker import get_next_step
        result = get_next_step(goal_id)
        return json.dumps(result or {"message": "No hay más sub-tareas"}, ensure_ascii=False, indent=2)
    elif action == "summary":
        from core.goal_tracker import format_goals
        return format_goals()
    return "Acción desconocida"


def anomaly_detector(parameters: dict = None) -> str:
    """Detección de patrones inusuales."""
    params = parameters or {}
    action = params.get("action", "code")

    if action == "snapshot":
        from core.anomaly_detector import take_snapshot, format_anomalies
        result = take_snapshot()
        if result.get("anomalies_found", 0) == 0:
            return "Snapshot tomado: %d archivos, sin anomalías" % result.get("files_tracked", 0)
        return format_anomalies(result.get("anomalies", []))
    elif action == "code":
        from core.anomaly_detector import detect_code_anomalies, format_anomalies
        anomalies = detect_code_anomalies(params.get("directory"))
        return format_anomalies(anomalies)
    elif action == "logs":
        from core.anomaly_detector import detect_log_anomalies
        result = detect_log_anomalies(params.get("log_file", ""))
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif action == "sizes":
        from core.anomaly_detector import get_file_size_anomalies
        anomalies = get_file_size_anomalies(params.get("threshold_mb", 5.0))
        if not anomalies:
            return "Sin archivos grandes detectados"
        from core.anomaly_detector import format_anomalies
        return format_anomalies(anomalies)
    return "Acción desconocida"


def confidence_scorer(parameters: dict = None) -> str:
    """Cuantifica confianza en respuestas."""
    params = parameters or {}
    action = params.get("action", "score")

    if action == "score":
        from core.confidence_scorer import score_confidence, format_confidence
        evidence = [e for e in params.get("evidence", "").split("\n") if e.strip()]
        result = score_confidence(
            params.get("claim", ""),
            evidence,
            params.get("topic", ""),
            params.get("context", ""),
        )
        return format_confidence(result)
    elif action == "batch":
        from core.confidence_scorer import score_multiple, format_confidence
        claims = [c for c in params.get("claims", "").split("\n") if c.strip()]
        results = score_multiple(claims)
        return "\n\n".join(format_confidence(r) for r in results)
    elif action == "batch_ev":
        from core.confidence_scorer import batch_score_with_evidence, format_confidence
        try:
            claims = json.loads(params.get("claims_json", "[]"))
        except Exception:
            return "claims_json inválido"
        results = batch_score_with_evidence(claims)
        return "\n\n".join(format_confidence(r) for r in results)
    return "Acción desconocida"


def knowledge_graph(parameters: dict = None) -> str:
    """Grafo de conocimiento."""
    params = parameters or {}
    action = params.get("action", "query")

    if action == "add_node":
        from core.knowledge_graph import add_node
        try:
            props = json.loads(params.get("properties", "{}"))
        except Exception:
            props = {}
        node = add_node(params.get("name", ""), params.get("node_type", "concept"), props)
        return json.dumps(node, ensure_ascii=False, indent=2)
    elif action == "add_edge":
        from core.knowledge_graph import add_edge
        try:
            props = json.loads(params.get("properties", "{}"))
        except Exception:
            props = {}
        edge = add_edge(params.get("source", ""), params.get("target", ""), params.get("relation", ""), props)
        return json.dumps(edge, ensure_ascii=False, indent=2)
    elif action == "query":
        from core.knowledge_graph import format_graph_node
        return format_graph_node(params.get("name", ""))
    elif action == "path":
        from core.knowledge_graph import find_path
        paths = find_path(params.get("source", ""), params.get("target", ""))
        if not paths:
            return "No se encontró camino entre %s y %s" % (params.get("source", ""), params.get("target", ""))
        lines = ["%d camino(s) encontrado(s):" % len(paths)]
        for p in paths[:3]:
            segs = " → ".join(step["node"] for step in p)
            lines.append("  %s" % segs)
        return "\n".join(lines)
    elif action == "related":
        from core.knowledge_graph import related_concepts
        related = related_concepts(params.get("name", ""), params.get("depth", 2))
        if not related:
            return "Sin conceptos relacionados"
        return json.dumps(related[:20], ensure_ascii=False, indent=2)
    elif action == "impact":
        from core.knowledge_graph import impact_analysis
        return json.dumps(impact_analysis(params.get("name", "")), ensure_ascii=False, indent=2)
    elif action == "stats":
        from core.knowledge_graph import get_stats
        return json.dumps(get_stats(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def mistake_learner(parameters: dict = None) -> str:
    """Aprende de errores propios."""
    params = parameters or {}
    action = params.get("action", "analysis")

    if action == "record":
        from core.mistake_learner import record_mistake
        mistake = record_mistake(
            params.get("pattern", ""),
            params.get("cause", ""),
            params.get("solution", ""),
            params.get("context", ""),
            params.get("severity", "medium"),
            params.get("category", "general"),
        )
        return json.dumps(mistake, ensure_ascii=False, indent=2)
    elif action == "rule":
        from core.mistake_learner import create_rule
        rule = create_rule(
            params.get("trigger", ""),
            params.get("action", ""),
            params.get("reason", ""),
            params.get("category", "general"),
        )
        return json.dumps(rule, ensure_ascii=False, indent=2)
    elif action == "check":
        from core.mistake_learner import check_before_acting
        violations = check_before_acting(params.get("action_desc", ""))
        if not violations:
            return "Ninguna regla violada"
        return json.dumps(violations, ensure_ascii=False, indent=2)
    elif action == "related":
        from core.mistake_learner import get_related_mistakes
        related = get_related_mistakes(params.get("current_error", ""))
        if not related:
            return "Sin mistakes similares encontrados"
        return json.dumps(related, ensure_ascii=False, indent=2)
    elif action == "unresolved":
        from core.mistake_learner import get_unresolved
        unresolved = get_unresolved()
        if not unresolved:
            return "Sin mistakes pendientes"
        return json.dumps(unresolved, ensure_ascii=False, indent=2)
    elif action == "resolve":
        from core.mistake_learner import mark_resolved
        ok = mark_resolved(params.get("mistake_id", ""), params.get("solution", ""))
        return "Mistake resuelto" if ok else "Mistake no encontrado"
    elif action == "analysis":
        from core.mistake_learner import format_mistakes
        return format_mistakes()
    return "Acción desconocida"


def task_scheduler(parameters: dict = None) -> str:
    """Programación de tareas y recordatorios."""
    params = parameters or {}
    action = params.get("action", "active")

    if action == "create":
        from core.scheduler import create_task
        task = create_task(
            params.get("description", ""),
            params.get("task_type", "once"),
        )
        return json.dumps(task, ensure_ascii=False, indent=2)
    elif action == "reminder":
        from core.scheduler import create_reminder
        task = create_reminder(params.get("description", ""), params.get("minutes", 60))
        return "Recordatorio creado: %s (en %d min)" % (params.get("description", "")[:40], params.get("minutes", 60))
    elif action == "recurring":
        from core.scheduler import create_recurring
        task = create_recurring(
            params.get("description", ""),
            params.get("interval_seconds", 3600),
            params.get("max_runs", 10),
        )
        return json.dumps(task, ensure_ascii=False, indent=2)
    elif action == "due":
        from core.scheduler import get_due_tasks
        due = get_due_tasks()
        if not due:
            return "Sin tareas pendientes de ejecutar"
        return json.dumps(due, ensure_ascii=False, indent=2)
    elif action == "active":
        from core.scheduler import format_schedule
        return format_schedule()
    elif action == "cancel":
        from core.scheduler import cancel_task
        ok = cancel_task(params.get("task_id", ""))
        return "Tarea cancelada" if ok else "Tarea no encontrada"
    elif action == "delete":
        from core.scheduler import delete_task
        ok = delete_task(params.get("task_id", ""))
        return "Tarea eliminada" if ok else "Tarea no encontrada"
    elif action == "mark_done":
        from core.scheduler import mark_executed
        ok = mark_executed(params.get("task_id", ""))
        return "Tarea marcada como ejecutada" if ok else "Tarea no encontrada"
    elif action == "history":
        from core.scheduler import get_history
        return json.dumps(get_history(), ensure_ascii=False, indent=2)
    return "Acción desconocida"


def context_bridge(parameters: dict = None) -> str:
    """Puente de contexto entre sesiones."""
    params = parameters or {}
    action = params.get("action", "resume")

    if action == "save":
        from core.context_bridge import save_session_context
        tasks = [t for t in params.get("tasks_in_progress", "").split("\n") if t.strip()]
        questions = [q for q in params.get("open_questions", "").split("\n") if q.strip()]
        decisions = [d for d in params.get("key_decisions", "").split("\n") if d.strip()]
        save_session_context(
            params.get("session_id", ""),
            params.get("user_intent", ""),
            tasks, questions, decisions,
        )
        return "Contexto de sesión guardado"
    elif action == "resume":
        from core.context_bridge import format_bridge
        return format_bridge()
    elif action == "link":
        from core.context_bridge import link_sessions
        link_sessions(params.get("session_id", ""), params.get("related_session", ""), params.get("reason", ""))
        return "Sesiones vinculadas"
    elif action == "related":
        from core.context_bridge import get_related_sessions
        related = get_related_sessions(params.get("session_id", ""))
        if not related:
            return "Sin sesiones relacionadas"
        return json.dumps(related, ensure_ascii=False, indent=2)
    elif action == "complete_task":
        from core.context_bridge import complete_task
        ok = complete_task(params.get("task_text", ""))
        return "Tarea marcada como completada" if ok else "Tarea no encontrada"
    elif action == "answer_q":
        from core.context_bridge import answer_question
        ok = answer_question(params.get("question_text", ""))
        return "Pregunta marcada como respondida" if ok else "Pregunta no encontrada"
    return "Acción desconocida"


def file_profiler(parameters: dict = None) -> str:
    """Perfil completo de archivos."""
    params = parameters or {}
    action = params.get("action", "file")

    if action == "file":
        from core.file_profiler import profile_file, format_profile
        profile = profile_file(params.get("file_path", ""))
        return format_profile(profile)
    elif action == "project":
        from core.file_profiler import profile_project
        dirs = [d for d in params.get("directories", "").split("\n") if d.strip()]
        result = profile_project(dirs or None)
        lines = [
            "Perfil del proyecto:",
            "  Archivos: %d, Líneas: %d" % (result["total_files"], result["total_lines"]),
            "  Funciones: %d, Clases: %d" % (result["total_functions"], result["total_classes"]),
            "  Complejidad total: %d" % result["total_complexity"],
            "  Quality score promedio: %.1f/100" % result["avg_quality_score"],
        ]
        if result["complex_files"]:
            lines.append("\nArchivos más complejos:")
            for f in result["complex_files"]:
                lines.append("  ⚠ %s (complejidad: %d)" % (f["file"][:50], f["complexity"]))
        return "\n".join(lines)
    return "Acción desconocida"
