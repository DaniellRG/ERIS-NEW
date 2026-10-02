
## 2026-09-06 00:40 — eris_git_test
- `[main (commit-raíz) 62926fb] fix(eris): bug.py (+1)
 2 files changed, 2 insertions(+)
 create mode 100644 bug.py
 create mode 100644 hola.py
→ fix(eris): bug.py (+1)`

## 2026-09-06 00:40 — eris_git_test
- 62926fb fix(eris): bug.py (+1)

## 2026-09-06 08:10 — ERIS-NEW
- `[main 1f0a8c8] docs(core): AGENTS.md (+30)
 31 files changed, 731 insertions(+), 147 deletions(-)
 create mode 100644 agents/agenlix_agent.py
→ docs(core): AGENTS.md (+30)`

## 2026-09-15 10:39 — ERIS-NEW
- `[main ae3c87b] docs(actions): AGENTS.md (+88)
 89 files changed, 2319 insertions(+), 124 deletions(-)
 create mode 100644 assets/vrm/_three_test.html
 create mode 100644 assets/vrm/_webgl_test.html
 create mode 100644 assets/vrm/viewer_debug.html
 create mode 100644 core/truth_audit.py
 delete mode 100644 data/charts/bar_20260726_113606.png
 delete mode 100644 data/charts/bar_20260726_113751.png
 delete mode 100644 data/charts/bar_20260726_113752.png
 delete mode 100644 data/charts/bar_20260726_114100.png
 delete mode 100644 data/charts/bar_20260726_114101.png
 delete mode 100644 data/charts/bar_20260726_114419.png
 delete mode 100644 data/charts/bar_20260726_114420.png
 delete mode 100644 data/charts/bar_20260726_120019.png
 delete mode 100644 data/charts/bar_20260726_120020.png
 delete mode 100644 data/charts/bar_20260726_120350.png
 delete mode 100644 data/charts/bar_20260726_120351.png
 delete mode 100644 data/charts/bar_20260726_120725.png
 delete mode 100644 data/charts/bar_20260726_120726.png
 delete mode 100644 data/charts/bar_20260729_224321.png
 delete mode 100644 data/charts/bar_20260729_224423.png
 delete mode 100644 data/charts/hist_20260729_224424.png
 delete mode 100644 data/charts/line_20260726_113751.png
 delete mode 100644 data/charts/line_20260726_114100.png
 delete mode 100644 data/charts/line_20260726_114419.png
 delete mode 100644 data/charts/line_20260726_120019.png
 delete mode 100644 data/charts/line_20260726_120350.png
 delete mode 100644 data/charts/line_20260726_120725.png
 delete mode 100644 data/charts/line_20260729_224423.png
 delete mode 100644 data/charts/pie_20260726_113751.png
 delete mode 100644 data/charts/pie_20260726_114100.png
 delete mode 100644 data/charts/pie_20260726_114419.png
 delete mode 100644 data/charts/pie_20260726_120019.png
 delete mode 100644 data/charts/pie_20260726_120350.png
 delete mode 100644 data/charts/pie_20260726_120725.png
 delete mode 100644 data/charts/pie_20260729_224423.png
 delete mode 100644 data/charts/scatter_20260729_224423.png
 create mode 100644 data/daily_reports/2026-09-14.md
 create mode 100644 data/daily_reports/2026-09-15.md
 create mode 100644 memory/eris_fabrica_backups/test_params_tool/20260915_102147/meta.json
 create mode 100644 memory/eris_fabrica_backups/test_params_tool/20260915_102147/test_params_tool.py
 create mode 100644 memory/eris_fabrica_backups/test_rota_tool/20260915_102147/meta.json
 create mode 100644 memory/eris_fabrica_backups/test_rota_tool/20260915_102147/test_rota_tool.py
 create mode 100644 memory/eris_fabrica_backups/test_smoke_tool/20260915_102049/meta.json
 create mode 100644 memory/eris_fabrica_backups/test_smoke_tool/20260915_102049/test_smoke_tool.py
 create mode 100644 memory/eris_fabrica_backups/test_smoke_tool/20260915_102147/meta.json
 create mode 100644 memory/eris_fabrica_backups/test_smoke_tool/20260915_102147/test_smoke_tool.py
 create mode 100755 run_eris.sh
 create mode 100644 "vault/Logs/Evoluci\303\263n - 2026-09-14.md"
 create mode 100644 "vault/Logs/Evoluci\303\263n - 2026-09-15.md"
→ docs(actions): AGENTS.md (+88)`

## 2026-09-18 12:12 — ERIS-NEW
- `[main 119cb8b] docs(actions): AGENTS.md (+75)
 76 files changed, 4440 insertions(+), 34 deletions(-)
 create mode 100644 actions/custom/eris_omarecorder_bridge.py
 create mode 100644 actions/sub_agent_manager.py
 create mode 100644 core/opencode_bridge.py
 create mode 100644 core/repetition_guard.py
 create mode 100644 core/sub_agent_crew.py
 create mode 100644 core/sub_agent_registry.json
 create mode 100644 core/sub_agents.py
 create mode 100644 core/telegram_bridge.py
 create mode 100644 data/daily_reports/2026-09-18.md
 create mode 100644 data/opencode/estado_real.json
 create mode 100644 data/opencode/inbox_conocimiento/20260918-115200-tripulacion-19-subagentes.md
 create mode 100644 data/opencode/inbox_conocimiento/20260918-115900-tripulacion-agencial-proyectar.md
 create mode 100644 memory/sub_agent_plans/plan_1789747634.json
 create mode 100644 memory/sub_agent_plans/plan_1789747710.json
 create mode 100644 memory/sub_agent_plans/plan_1789748649.json
 create mode 100644 memory/sub_agent_plans/plan_1789749185.json
 create mode 100644 memory/sub_agent_plans/plan_1789750018.json
 create mode 100644 memory/sub_agent_plans/plan_1789750049.json
 create mode 100644 memory/sub_agent_plans/plan_1789750080.json
 create mode 100644 memory/sub_agent_plans/plan_1789750087.json
 create mode 100644 memory/sub_agent_plans/plan_1789750138.json
 create mode 100644 memory/sub_agent_plans/plan_1789750199.json
 create mode 100644 memory/sub_agent_plans/plan_1789750260.json
 create mode 100644 memory/sub_agent_plans/plan_1789750291.json
 create mode 100644 memory/sub_agent_plans/plan_1789750447.json
 create mode 100644 memory/sub_agent_plans/plan_1789750473.json
 create mode 100644 memory/sub_agent_plans/plan_1789750525.json
 create mode 100644 memory/sub_agent_plans/plan_1789750556.json
 create mode 100644 memory/sub_agent_plans/plan_1789750588.json
 create mode 100644 memory/sub_agent_plans/plan_1789750619.json
 create mode 100644 memory/sub_agent_plans/plan_1789750651.json
 create mode 100644 memory/sub_agent_plans/plan_1789750683.json
 create mode 100644 memory/sub_agent_plans/plan_1789750714.json
 create mode 100644 memory/sub_agent_plans/plan_1789750745.json
 create mode 100644 memory/sub_agent_plans/plan_1789750777.json
 create mode 100644 memory/sub_agent_plans/plan_1789750809.json
 create mode 100644 memory/sub_agent_plans/plan_1789750841.json
 create mode 100644 memory/sub_agent_plans/plan_1789750872.json
 create mode 100644 memory/sub_agent_plans/plan_1789750903.json
 create mode 100644 memory/sub_agent_plans/plan_1789750935.json
 create mode 100644 memory/sub_agent_plans/plan_1789750966.json
 create mode 100644 memory/sub_agent_plans/plan_1789750997.json
 create mode 100644 memory/sub_agent_plans/plan_1789751028.json
 create mode 100644 memory/sub_agent_plans/plan_1789751060.json
 create mode 100644 memory/sub_agent_plans/plan_1789751091.json
 create mode 100644 memory/sub_agent_plans/plan_1789751122.json
 create mode 100644 memory/sub_agent_plans/plan_1789751153.json
 create mode 100644 memory/sub_agent_plans/plan_1789751184.json
 create mode 100644 memory/sub_agent_plans/plan_1789751216.json
 create mode 100644 memory/sub_agent_plans/plan_1789751247.json
 create mode 100644 memory/sub_agent_plans/plan_1789751278.json
 create mode 100644 memory/sub_agent_plans/plan_1789751309.json
 create mode 100644 memory/sub_agent_plans/plan_1789751341.json
 create mode 100644 memory/sub_agent_plans/plan_1789751372.json
 create mode 100644 memory/sub_agent_plans/plan_1789751403.json
 create mode 100644 memory/sub_agent_plans/plan_1789751435.json
 create mode 100644 memory/sub_agent_plans/plan_1789751466.json
 create mode 100644 memory/sub_agent_plans/plan_1789751498.json
 create mode 100644 tools/opencode_helper.py
 create mode 100644 "vault/Logs/Evoluci\303\263n - 2026-09-18.md"
→ docs(actions): AGENTS.md (+75)`
