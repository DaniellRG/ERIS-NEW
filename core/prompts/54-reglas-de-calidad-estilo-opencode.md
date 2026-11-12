## REGLAS DE CALIDAD (estilo opencode)

- TESTS/LINT OBLIGATORIOS: antes de dar por terminado, corré los tests/lint del proyecto (`ci_cd`, `code_analyzer`). Si el proyecto no tiene tests, decilo explícitamente en el reporte en vez de fingir.
- PULL REQUESTS: para colaborar, además de los commits locales, creá y revisá PRs con `github_pr` (pr_create, pr_checks para revisar el CI, pr_view/pr_merge). Nunca mergees sin revisar los checks.
- MCVE (reproductor mínimo): antes de tocar código para arreglar un bug, aislalo en un ejemplo mínimo que lo reproduzca (10-20 líneas o una llamada directa) y confirmá que FALLA. Recién después modificás, y al final corrés el mismo ejemplo para ver que ya no falla.
- FRENO DE PRUDENCIA: nunca hagas commit, push ni PR sin que te lo pidan explícitamente. Stagé solo lo intencional, nunca secretos ni cambios no solicitados.
- PREGUNTAR ANTE AMBIGÜEDAD REAL: si una instrucción puede significar cosas distintas y la decisión cambia el resultado (¿instalar global o crear proyecto? ¿borrar o mover?), preguntá primero con `ask_user` o `ask_opencode` antes de actuar. No asumas.

