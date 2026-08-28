import math
import re
from datetime import datetime, timedelta

def calculator(parameters: dict, player=None) -> str:
    expression = parameters.get("expression") or parameters.get("query") or parameters.get("text") or ""
    action = (parameters.get("action") or "calculate").lower()

    if player:
        player.write_log(f"🧮 Calculadora: {expression}")

    if action in ("calculate", "calcular", "resolver"):
        return _calculate(expression)
    elif action in ("convert", "convertir"):
        return _convert(expression)
    elif action in ("date", "fecha", "tiempo"):
        return _date_calc(expression)
    elif action in ("random", "aleatorio"):
        return _random_number(expression)
    else:
        return _calculate(expression)

def _calculate(expr):
    if not expr:
        return "¿Qué querés calcular?"

    expr = expr.lower().strip()
    expr = expr.replace("x", "*").replace("×", "*").replace("÷", "/")
    expr = expr.replace("^", "**").replace("elevado a", "**")

    # Porcentajes: "15 por ciento de 800" -> "(15/100)*800", "15%" -> "(15/100)"
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*por\s*ciento\s*de", r"(\1/100)*", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*porciento\s*de", r"(\1/100)*", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*de", r"(\1/100)*", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*por\s*ciento", r"(\1/100)", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*porciento", r"(\1/100)", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", expr)

    replacements = {
        "raiz cuadrada de": "math.sqrt",
        "raiz de": "math.sqrt",
        "sqrt de": "math.sqrt",
        "seno de": "math.sin",
        "sin de": "math.sin",
        "coseno de": "math.cos",
        "cos de": "math.cos",
        "tangente de": "math.tan",
        "tan de": "math.tan",
        "logaritmo de": "math.log10",
        "log de": "math.log10",
        "ln de": "math.log",
        "absoluto de": "abs",
        "factorial de": "math.factorial",
        "pi": "math.pi",
        "euler": "math.e",
    }

    processed = expr
    for key, val in replacements.items():
        processed = processed.replace(key, val)

    # "raiz cuadrada de 144" -> "math.sqrt(144)", "abs 5" -> "abs(5)"
    processed = re.sub(r"math\.(sqrt|sin|cos|tan|log10|log|factorial)\s+(\d+(?:\.\d+)?)", r"math.\1(\2)", processed)
    processed = re.sub(r"\babs\s+(\d+(?:\.\d+)?)", r"abs(\1)", processed)

    safe_chars = set("0123456789+-*/()., math.sqrtabsfloorceilroundlogsincoantPIE,")
    if not all(c in safe_chars for c in processed.replace("math.sqrt", "").replace("math.sin", "")):
        try:
            result = eval(processed, {"math": math, "__builtins__": {}}, {})
            return f"{expr} = {result}"
        except:
            pass

    try:
        result = eval(processed, {"math": math, "__builtins__": {}}, {})
        if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
            result = int(result)
        return f"{expr} = {result}"
    except Exception as e:
        return f"No pude calcular '{expr}'. Error: {e}"

def _convert(expr):
    conversions = {
        "km a millas": lambda x: f"{x * 0.621371:.2f} millas",
        "millas a km": lambda x: f"{x * 1.60934:.2f} km",
        "kg a libras": lambda x: f"{x * 2.20462:.2f} libras",
        "libras a kg": lambda x: f"{x * 0.453592:.2f} kg",
        "metros a pies": lambda x: f"{x * 3.28084:.2f} pies",
        "pies a metros": lambda x: f"{x * 0.3048:.2f} metros",
        "celsius a fahrenheit": lambda x: f"{x * 9/5 + 32:.1f}°F",
        "fahrenheit a celsius": lambda x: f"{(x - 32) * 5/9:.1f}°C",
        "litros a galones": lambda x: f"{x * 0.264172:.2f} galones",
        "galones a litros": lambda x: f"{x * 3.78541:.2f} litros",
        "gb a mb": lambda x: f"{x * 1024:.0f} MB",
        "mb a gb": lambda x: f"{x / 1024:.2f} GB",
        "segundos a minutos": lambda x: f"{x / 60:.2f} minutos",
        "minutos a segundos": lambda x: f"{x * 60:.0f} segundos",
        "horas a minutos": lambda x: f"{x * 60:.0f} minutos",
        "minutos a horas": lambda x: f"{x / 60:.2f} horas",
    }

    expr_lower = expr.lower().strip()
    numbers = re.findall(r"[\d.]+", expr_lower)
    if not numbers:
        return "No encontré números para convertir. Ej: '100 km a millas'"

    value = float(numbers[0])
    for pattern, func in conversions.items():
        if pattern in expr_lower:
            return f"{value} {pattern} = {func(value)}"

    return f"No sé convertir eso. Prueba con: km a millas, kg a libras, celsius a fahrenheit..."

def _date_calc(expr):
    now = datetime.now()
    expr_lower = expr.lower().strip()

    if not expr_lower or "hoy" in expr_lower:
        return f"Hoy es {now.strftime('%A %d de %B de %Y, %H:%M')}"

    if "mañana" in expr_lower:
        tomorrow = now + timedelta(days=1)
        return f"Mañana es {tomorrow.strftime('%A %d de %B de %Y')}"

    if "ayer" in expr_lower:
        yesterday = now - timedelta(days=1)
        return f"Ayer fue {yesterday.strftime('%A %d de %B de %Y')}"

    numbers = re.findall(r"\d+", expr_lower)
    if "días" in expr_lower or "dias" in expr_lower or "día" in expr_lower:
        if numbers:
            days = int(numbers[0])
            future = now + timedelta(days=days)
            return f"En {days} días será {future.strftime('%A %d de %B de %Y')}"

    if "hora" in expr_lower:
        return f"Son las {now.strftime('%H:%M')}"

    if "año" in expr_lower or "años" in expr_lower:
        if numbers:
            years = int(numbers[0])
            future = now + timedelta(days=years * 365)
            return f"En {years} años serán approximately {future.year}"

    days_of_week = {
        "lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3,
        "viernes": 4, "sábado": 5, "domingo": 6
    }
    for day_name, day_num in days_of_week.items():
        if day_name in expr_lower:
            days_ahead = (day_num - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target = now + timedelta(days=days_ahead)
            return f"El próximo {day_name} es {target.strftime('%d de %B')}"

    return f"Hoy es {now.strftime('%A %d de %B de %Y, %H:%M')}"

def _random_number(expr):
    import random
    numbers = re.findall(r"\d+", expr)
    if len(numbers) >= 2:
        a, b = int(numbers[0]), int(numbers[1])
        return f"Número aleatorio entre {a} y {b}: {random.randint(a, b)}"
    elif len(numbers) == 1:
        return f"Número aleatorio entre 1 y {int(numbers[0])}: {random.randint(1, int(numbers[0]))}"
    else:
        return f" número aleatorio: {random.randint(1, 100)}"
