import json
import subprocess
from pathlib import Path

CONFIG_PATH = Path("data/config.json")
CONTAINERS_PATH = Path("data/containers.json")


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    else:
        raise FileNotFoundError("Arquivo config.json não encontrado.")


def load_containers():
    if CONTAINERS_PATH.exists():
        with open(CONTAINERS_PATH) as f:
            return json.load(f)
    else:
        raise FileNotFoundError("Arquivo containers.json não encontrado.")


def run_rsync(src, dest):
    try:
        subprocess.check_call([
            "rsync", "-Cravz", f"{src}/", dest
        ])
        print(f"[✓] Backup concluído: {src} → {dest}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Erro ao copiar {src} → {dest}: {e}")


def perform_backups():
    config = load_config()
    containers = load_containers()

    destination_raw = config.get("destinationPath")
    if not destination_raw:
        raise ValueError("destinationPath não definido em config.json")

    # Resolvido em relação ao diretório do config.json
    destination_base = (CONFIG_PATH.parent / destination_raw).resolve()

    for container in containers:
        name = container.get("name")
        src_path = container.get("path")

        if not name or not src_path:
            print(f"[!] Container inválido ou sem caminho: {container}")
            continue

        src = Path(src_path).resolve()
        dest = destination_base / name

        if not src.exists():
            print(f"[!] Caminho de origem não existe: {src}")
            continue

        dest.mkdir(parents=True, exist_ok=True)
        run_rsync(str(src), str(dest))


if __name__ == "__main__":
    perform_backups()
