import json
import subprocess
from pathlib import Path

DATA_PATH = Path("data/containers.json")


def run_command(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_active_containers():
    output = run_command(["docker", "ps", "--format", "{{.Names}}"])
    return output.splitlines() if output else []


def inspect_container(name):
    output = run_command(["docker", "inspect", name])
    if not output:
        return None

    info = json.loads(output)[0]

    ports_data = info.get("NetworkSettings", {}).get("Ports", {})
    ports = {}
    for container_port, bindings in ports_data.items():
        if bindings:
            ports[container_port] = int(bindings[0]["HostPort"])

    networks = info.get("NetworkSettings", {}).get("Networks", {})
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

        return {
            "name": name,
            "ports": ports,
            "ip": ip_address,
            "subnet": subnet
        }

    return None


def load_existing_containers():
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def infer_container_path(name):
    return f"/srv/apps/{name}"


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
            container_info["path"] = infer_container_path(name)
            new_entries.append(container_info)
            existing_map[name] = container_info
        else:
            existing_entry = existing_map[name]
            if "path" in existing_entry:
                container_info["path"] = existing_entry["path"]
            else:
                container_info["path"] = infer_container_path(name)
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
