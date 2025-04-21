import os
import json
import socket
import argparse
from pathlib import Path

BASE_SUBNET = "172.16.{x}.0/24"
DATA_PATH = Path("data/containers.json")


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def load_existing_containers():
    if DATA_PATH.exists() and DATA_PATH.read_text().strip():
        with open(DATA_PATH, 'r') as f:
            return json.load(f)
    return []


def container_exists(containers, project_name=None, port=None, subnet=None):
    for container in containers:
        if (
            (project_name and container["name"] == project_name) or
            (port and str(port) in container.get("ports", {}).values()) or
            (subnet and container["subnet"] == subnet)
        ):
            return True
    return False


def find_available_port(containers, start=8001, end=9000):
    for port in range(start, end):
        if is_port_available(port) and not container_exists(containers, port=port):
            return port
    raise Exception("Nenhuma porta disponível encontrada entre 8000 e 9000.")


def find_available_subnet(containers):
    for x in range(0, 256):
        subnet = BASE_SUBNET.format(x=x)
        if not container_exists(containers, subnet=subnet):
            return subnet
    raise Exception("Nenhuma subnet disponível encontrada na faixa 172.16.x.0/24.")


def generate_compose(project_name, port, subnet):
    gateway = subnet.replace('0/24', '1')
    return f"""version: '2'

services:

  {project_name}:
    image: php:7.4-apache
    container_name: {project_name}
    ports:
      - "{port}:80"
    networks:
      - "hosting"
    restart: always
    volumes:
      - ./src:/var/www/html
      - ./scripts/:/scripts/
      - ./etc/php/php.ini:/usr/local/etc/php/php.ini
    command: >
      bash -c "a2enmod rewrite
      && apache2-foreground"

networks:
  hosting:
    ipam:
      config:
      - subnet: {subnet}
        gateway: {gateway}
"""


def save_container_info(project_name, port, subnet, path):
    containers = load_existing_containers()
    containers.append({
        "name": project_name,
        "ports": {
            "80/tcp": port
        },
        "ip": subnet.replace("0/24", "2"),
        "subnet": subnet,
        "path": str(path)
    })

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, 'w') as f:
        json.dump(containers, f, indent=2)


def generate_bash_scripts(project_name):
    start_script = f"""#!/bin/bash
docker-compose --project-name="{project_name}" up -d
"""
    stop_script = f"""#!/bin/bash
docker-compose --project-name="{project_name}" down
"""
    return start_script, stop_script


def main(project_name, container_path):
    container_path = Path(container_path)
    containers = load_existing_containers()

    if container_exists(containers, project_name=project_name):
        print(f"Erro: Projeto com nome '{project_name}' já existe.")
        return

    port = find_available_port(containers)
    subnet = find_available_subnet(containers)
    compose_content = generate_compose(project_name, port, subnet)
    start_script, stop_script = generate_bash_scripts(project_name)

    container_path.mkdir(parents=True, exist_ok=True)

    with open(container_path / "docker-compose.yml", 'w') as f:
        f.write(compose_content)

    with open(container_path / "start.sh", 'w') as f:
        f.write(start_script)
        os.chmod(container_path / "start.sh", 0o755)

    with open(container_path / "stop.sh", 'w') as f:
        f.write(stop_script)
        os.chmod(container_path / "stop.sh", 0o755)

    save_container_info(project_name, port, subnet, container_path)

    print(f"[✔] Arquivos gerados em '{container_path}'")
    print(f"[ℹ] Porta: {port}, Subnet: {subnet}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provisionador Docker")
    parser.add_argument("project_name", help="Nome do projeto")
    parser.add_argument("--container-path", required=True, help="Caminho onde será criada a aplicação")

    args = parser.parse_args()
    main(args.project_name, args.container_path)
