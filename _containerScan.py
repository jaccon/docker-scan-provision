import json
import subprocess
from pathlib import Path
from os.path import commonprefix, dirname

DATA_PATH = Path("data/containers.json")


def run_command(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Erro ao executar comando: {cmd} -> {e}")
        return None


def get_active_containers():
    output = run_command(["docker", "ps", "--format", "{{.Names}}"])
    return output.splitlines() if output else []


def extract_mount_base(mounts):
    sources = [
        mount.get("Source") for mount in mounts
        if mount.get("Type") == "bind" and mount.get("Source")
    ]
    if not sources:
        return None

    base = commonprefix(sources)
    return dirname(base)


def inspect_container(name):
    output = run_command(["docker", "inspect", name])
    if not output:
        return None

    try:
        info = json.loads(output)[0]

        ports_data = info.get("NetworkSettings", {}).get("Ports", {})
        ports = {}
        for container_port, bindings in ports_data.items():
            if bindings:
                ports[container_port] = int(bindings[0]["HostPort"])

        networks = info.get("NetworkSettings", {}).get("Networks", {})
        ip_address = None
        subnet = None

        for net_name, net_data in networks.items():
            ip_address = net_data.get("IPAddress")
            ipam_config = net_data.get("IPAMConfig")
            if ipam_config and ipam_config.get("Subnet"):
                subnet = ipam_config["Subnet"]
            else:
                subnet = run_command([
                    "docker", "network", "inspect", net_name,
                    "--format", "{{range .IPAM.Config}}{{.Subnet}}{{end}}"
                ])
            break  # Assume apenas a primeira rede é suficiente

        labels = info.get("Config", {}).get("Labels", {})
        compose_file = labels.get("com.docker.compose.project.config_files")

        if compose_file:
            path = str(Path(compose_file).parent)
        else:
            mounts = info.get("Mounts", [])
            path = extract_mount_base(mounts)

        return {
            "name": name,
            "ports": ports,
            "ip": ip_address,
            "subnet": subnet,
            "path": path if path else f"/srv/apps/{name}"
        }
    except Exception as e:
        print(f"Erro ao inspecionar container '{name}': {e}")
        return None


def load_existing_containers():
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def update_containers_json():
    existing = load_existing_containers()
    existing_map = {c["name"]: c for c in existing}

    active = get_active_containers()
    new_entries = []

    for name in active:
        container_info = inspect_container(name)
        if not container_info:
            continue

        if name not in existing_map:
            new_entries.append(container_info)
            existing_map[name] = container_info
        else:
            existing_entry = existing_map[name]
            if "path" in existing_entry and existing_entry["path"] != container_info["path"]:
                container_info["path"] = existing_entry["path"]
            existing_map[name] = container_info

    updated = list(existing_map.values())

    if new_entries:
        print(f"[+] Adicionando {len(new_entries)} container(s) ao containers.json")
    else:
        print("[✓] Nenhum novo container para adicionar.")

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(updated, f, indent=2)


if __name__ == "__main__":
    update_containers_json()
