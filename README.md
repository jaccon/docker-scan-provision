# Docker Container Provisioning Tool

This tool automates the discovery, registration, and tracking of active Docker containers on your system. It collects essential information such as container name, ports, IP address, subnet, and the intended application path. This data is stored in a centralized `containers.json` file for easy reference and further automation.

## Features

- Detects all currently active Docker containers
- Extracts port mappings, IP address, and subnet
- Automatically infers the file path where the application resides (default: `/srv/apps/{container_name}`)
- Preserves manually assigned paths across updates
- Outputs all data to a structured JSON file: `data/containers.json`

## Usage

```bash
python3 _containerProvision.py
