import os
import platform
import subprocess

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False


class HardwareProfiler:
    @staticmethod
    def inspect_system() -> dict:
        if _HAS_PSUTIL:
            ram_info = psutil.virtual_memory()
            total_ram_gb = round(ram_info.total / (1024 ** 3), 2)
            available_ram_gb = round(ram_info.available / (1024 ** 3), 2)
            cpu_cores_physical = psutil.cpu_count(logical=False) or 1
            cpu_cores_logical = psutil.cpu_count(logical=True) or 1
        else:
            total_ram_gb = 0.0
            available_ram_gb = 0.0
            cpu_cores_physical = 1
            cpu_cores_logical = 1

        cpu_name = platform.processor() or "CPU Generica"

        gpu_info = HardwareProfiler._detect_gpu()

        tier, heavy_tasks_allowed = HardwareProfiler._calculate_tier(
            total_ram_gb, gpu_info
        )

        return {
            "ram": {
                "total_gb": total_ram_gb,
                "available_gb": available_ram_gb
            },
            "cpu": {
                "model": cpu_name,
                "cores_physical": cpu_cores_physical,
                "cores_logical": cpu_cores_logical
            },
            "gpu": gpu_info,
            "performance_profile": {
                "tier": tier,
                "allow_local_heavy_tasks": heavy_tasks_allowed,
                "recommended_action": HardwareProfiler._get_recommendation(tier, gpu_info)
            }
        }

    @staticmethod
    def _detect_gpu() -> dict:
        gpu_data = {
            "has_dedicated": False,
            "brand": "Desconocida / Integrada",
            "model": "No detectado",
            "vram_gb": 0.0
        }

        try:
            smi_out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=gpu_name,memory.total", "--format=csv,noheader,nounits"],
                encoding="utf-8", stderr=subprocess.DEVNULL
            ).strip()
            if smi_out:
                lines = smi_out.split("\n")[0].split(",")
                gpu_data["has_dedicated"] = True
                gpu_data["brand"] = "NVIDIA"
                gpu_data["model"] = lines[0].strip()
                gpu_data["vram_gb"] = round(float(lines[1].strip()) / 1024, 2)
                return gpu_data
        except Exception:
            pass

        if platform.system() == "Linux":
            try:
                lspci_out = subprocess.check_output(["lspci"], encoding="utf-8", stderr=subprocess.DEVNULL)
                for line in lspci_out.split("\n"):
                    if "VGA" in line or "3D" in line:
                        if "NVIDIA" in line.upper():
                            gpu_data["brand"] = "NVIDIA"
                            gpu_data["has_dedicated"] = True
                        elif "AMD" in line.upper() or "RADEON" in line.upper():
                            gpu_data["brand"] = "AMD"
                            gpu_data["has_dedicated"] = "RX" in line or "PRO" in line
                        elif "INTEL" in line.upper():
                            gpu_data["brand"] = "Intel"
                            gpu_data["has_dedicated"] = "ARC" in line.upper()
                        gpu_data["model"] = line.split(":")[-1].strip()
                        break
            except Exception:
                pass

        return gpu_data

    @staticmethod
    def _calculate_tier(ram_gb: float, gpu: dict) -> tuple:
        if gpu["has_dedicated"] and gpu["vram_gb"] >= 6.0 and ram_gb >= 16.0:
            return "HIGH", True
        elif gpu["has_dedicated"] or ram_gb >= 15.0:
            return "MEDIUM", False
        else:
            return "LOW", False

    @staticmethod
    def _get_recommendation(tier: str, gpu: dict) -> str:
        if tier == "HIGH":
            return "Equipo con GPU dedicada potente. Puedes procesar vision, embeddings y modelos locales pesados en este equipo."
        elif tier == "MEDIUM":
            return "Equipo de rendimiento medio. Renderizado ligero local; delega inferencias pesadas de LLM o vision a ZimaOS."
        else:
            return "Equipo limitado a CPU/Integrada. Mantiene la interfaz ligera. Toda la carga de IA, embeddings y scraping debe enviarse a ZimaOS."


def build_hardware_context(hw_profile: dict) -> str:
    tier = hw_profile["performance_profile"]["tier"]
    gpu = hw_profile["gpu"]
    ram = hw_profile["ram"]
    cpu = hw_profile["cpu"]
    recommendation = hw_profile["performance_profile"]["recommended_action"]

    hardware_context = f"""
=== CONCIENCIA DE HARDWARE LOCAL (PC ACTUAL) ===
- Perfil de rendimiento: {tier}
- Procesador (CPU): {cpu['model']} ({cpu['cores_logical']} hilos)
- Memoria RAM Total: {ram['total_gb']} GB (Disponible: {ram['available_gb']} GB)
- Grafica (GPU): {gpu['brand']} - {gpu['model']} (Dedicada: {gpu['has_dedicated']}, VRAM: {gpu['vram_gb']} GB)
- Regla de comportamiento: {recommendation}

REGLAS DE AUTOGESTION:
1. Si el perfil es 'LOW' o 'MEDIUM', NO intentes procesar modelos pesados, scraping en vivo con navegador visible o tareas de alta carga en esta laptop para evitar que la interfaz grafica se congele o se cierre.
2. Delega todas las tareas pesadas al servidor ZimaOS mediante la API remota.
3. Informa al usuario amablemente si te pide una tarea demasiado pesada y explicale que la procesaras a traves del servidor para proteger los recursos de su PC local.
================================================
"""
    return hardware_context
