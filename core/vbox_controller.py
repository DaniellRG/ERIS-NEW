"""
vbox_controller.py — Wrapper de VBoxManage para controlar VMs de VirtualBox.

Proporciona una API pythonica para gestionar máquinas virtuales:
listar, levantar, apagar, snapshots,-red, execute commands dentro de la VM.
"""
import subprocess
import re
import json
from typing import Optional, Dict, List


def _run(cmd: list, timeout: int = 60) -> dict:
    """Ejecuta un comando VBoxManage y devuelve stdout/stderr/returncode."""
    try:
        r = subprocess.run(
            ["VBoxManage"] + cmd,
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "code": r.returncode}
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "VBoxManage no encontrado. Instalá VirtualBox.", "code": -1}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout tras {timeout}s", "code": -2}


def list_vms() -> list:
    """Lista todas las VMs registradas. Devuelve [{name, uuid, state}]."""
    r = _run(["list", "vms"])
    if not r["ok"]:
        return []
    vms = []
    for line in r["stdout"].splitlines():
        m = re.match(r'^"(.+?)"\s+\{(.+?)\}$', line)
        if m:
            name, uuid = m.group(1), m.group(2)
            info = _run(["showvminfo", uuid, "--machinereadable"])
            state = "unknown"
            if info["ok"]:
                for sl in info["stdout"].splitlines():
                    if sl.startswith("VMState="):
                        state = sl.split("=", 1)[1].strip('"')
                        break
            vms.append({"name": name, "uuid": uuid, "state": state})
    return vms


def get_vm_info(name_or_uuid: str) -> dict:
    """Obtiene info detallada de una VM (OS, RAM, CPUs, IPs, etc)."""
    r = _run(["showvminfo", name_or_uuid, "--machinereadable"], timeout=15)
    if not r["ok"]:
        return {"error": r["stderr"]}
    info = {}
    for line in r["stdout"].splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v.strip('"')
    return info


def start_vm(name: str, type: str = "headless") -> dict:
    """Enciende una VM. type: headless | gui | separate."""
    return _run(["startvm", name, "--type", type])


def stop_vm(name: str, mode: str = "acpipowerbutton") -> dict:
    """Apaga una VM. mode: acpipowerbutton | poweroff | savestate."""
    return _run(["controlvm", name, mode])


def pause_vm(name: str) -> dict:
    return _run(["controlvm", name, "pause"])


def resume_vm(name: str) -> dict:
    return _run(["controlvm", name, "resume"])


def reset_vm(name: str) -> dict:
    return _run(["controlvm", name, "reset"])


def get_vm_state(name: str) -> str:
    """Devuelve el estado actual: running | paused | poweroff | saved | unknown."""
    vms = list_vms()
    for vm in vms:
        if vm["name"] == name:
            return vm["state"]
    return "not_found"


def create_snapshot(name: str, snap_name: str) -> dict:
    return _run(["snapshot", name, "take", snap_name])


def restore_snapshot(name: str, snap_name: str) -> dict:
    return _run(["snapshot", name, "restore", snap_name])


def list_snapshots(name: str) -> list:
    """Lista snapshots de una VM."""
    r = _run(["snapshot", name, "list", "--machinereadable"], timeout=15)
    if not r["ok"]:
        return []
    snaps = []
    for line in r["stdout"].splitlines():
        if line.startswith("SnapshotName"):
            snaps.append(line.split("=", 1)[1].strip('"'))
    return snaps


def delete_snapshot(name: str, snap_name: str) -> dict:
    return _run(["snapshot", name, "delete", snap_name])


def get_vm_ip(name: str, iface: str = "eth0") -> Optional[str]:
    """Obtiene la IP de una VM via guestproperty (requiere Guest Additions)."""
    r = _run(["guestproperty", "get", name, f"/VirtualBox/GuestInfo/Net/0/V4/IP"], timeout=10)
    if r["ok"] and "Value:" in r["stdout"]:
        return r["stdout"].split("Value:", 1)[1].strip()
    return None


def list_running() -> list:
    """Lista VMs en estado running."""
    r = _run(["list", "runningvms"])
    if not r["ok"]:
        return []
    vms = []
    for line in r["stdout"].splitlines():
        m = re.match(r'^"(.+?)"\s+\{(.+?)\}$', line)
        if m:
            vms.append({"name": m.group(1), "uuid": m.group(2)})
    return vms


def set_network_nat(name: str, iface: str = "1") -> dict:
    """Configura adaptador NAT para una VM."""
    return _run(["modifyvm", name, f"--nic{iface}", "nat"])


def set_network_hostonly(name: str, iface: str = "1", hostonly: str = "vboxnet0") -> dict:
    """Configura adaptador Host-Only para una VM (red aislada)."""
    return _run(["modifyvm", name, f"--nic{iface}", "hostonly", f"--hostonlyadapter{iface}", hostonly])


def set_network_internal(name: str, iface: str = "1", netname: str = "pentest-lab") -> dict:
    """Configura red interna (solo VMs en la misma red interna se ven)."""
    return _run(["modifyvm", name, f"--nic{iface}", "intnet", f"--intnet{iface}", netname])


def shared_folder_add(name: str, host_path: str, guest_path: str) -> dict:
    return _run(["sharedfolder", "add", name, "--name", guest_path, "--hostpath", host_path, "--readonly"])


def exec_in_vm(name: str, user: str, password: str, command: str, timeout: int = 30) -> dict:
    """Ejecuta un comando dentro de la VM via guestcontrol (requiere Guest Additions)."""
    r = _run([
        "guestcontrol", name, "run",
        "--username", user, "--password", password,
        "--exe", "/bin/bash", "--",
        "-c", command
    ], timeout=timeout)
    return r


def get_hostonly_ifs() -> list:
    """Lista interfaces host-only disponibles."""
    r = _run(["list", "hostonlyifs"])
    if not r["ok"]:
        return []
    interfaces = []
    current = {}
    for line in r["stdout"].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            current[k.strip()] = v.strip()
        elif line == "" and current:
            interfaces.append(current)
            current = {}
    if current:
        interfaces.append(current)
    return interfaces


def get_natnets() -> list:
    """Lista redes NAT existentes."""
    r = _run(["list", "natnets"])
    if not r["ok"]:
        return []
    nets = []
    for line in r["stdout"].splitlines():
        m = re.match(r'^NetworkName:\s+(.+)$', line)
        if m:
            nets.append(m.group(1))
    return nets


def is_available() -> bool:
    """Verifica si VBoxManage está disponible y funcional."""
    r = _run(["--version"], timeout=10)
    return r["ok"] and bool(r["stdout"])
