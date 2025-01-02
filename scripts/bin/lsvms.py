#!/usr/bin/env python3
import os
import json
import sys
import argparse
from pathlib import Path

def read_json_file(file_path: str, key: str) -> str:
    """Read a value from a JSON file safely"""
    try:
        with open(file_path) as f:
            return json.load(f).get(key, "N/A")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "N/A"

def get_instance_ip(tproxy_state_file: str, instance_id: str) -> str:
    """Get instance IP from tproxy state file"""
    try:
        with open(tproxy_state_file) as f:
            data = json.load(f)
            return data.get('instances', {}).get(instance_id, {}).get('ip', 'N/A')
    except (FileNotFoundError, json.JSONDecodeError):
        return "N/A"

def parse_simple_toml(file_path: Path) -> dict:
    """Simple TOML parser for our specific needs"""
    config = {'gateway': {}}
    try:
        with open(file_path) as f:
            current_section = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    if current_section not in config:
                        config[current_section] = {}
                    continue

                if '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    value = value.strip('"').strip("'")
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    if current_section:
                        config[current_section][key] = value
                    else:
                        config[key] = value

            return config
    except (FileNotFoundError, IOError):
        return {'gateway': {}}

def get_dashboard_url(config: dict, app_id: str) -> str:
    """Generate dashboard URL from config and app_id"""
    try:
        gateway = config.get('gateway', {})
        base_domain = gateway.get('base_domain')
        tappd_port = gateway.get('tappd_port')
        gateway_port = gateway.get('port')

        if base_domain and tappd_port:
            url = f"https://{app_id}-{tappd_port}.{base_domain}"
            if gateway_port:
                url += f":{gateway_port}"
            return url + "/"
    except (KeyError, TypeError):
        pass
    return "N/A"

def print_vm_info(vm_data: dict, verbose: bool = False):
    """Pretty print VM information"""
    if verbose:
        print("=" * 100)
        for key, value in vm_data.items():
            # Right-align keys in a 15-character space, followed by a colon and value
            print(f"{key:>15}: {value}")
        print()
    else:
        print(f"{vm_data['name']:<25} {vm_data['ip']:<15} {vm_data['image']}")

def main():
    parser = argparse.ArgumentParser(description='List VMs information')
    parser.add_argument('stack_dir', help='Stack directory path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information')
    args = parser.parse_args()

    stack_dir = Path(args.stack_dir)
    vm_base_dir = stack_dir / "run" / "vm"
    tproxy_state_file = stack_dir / "tproxy-state.json"

    if not vm_base_dir.exists():
        print(f"Error: Directory not found: {vm_base_dir}")
        sys.exit(1)

    config = {}
    if args.verbose:
        config = parse_simple_toml(stack_dir / "teepod.toml")

    if not args.verbose:
        # Print simple header
        print(f"{'Name':<25} {'IP':<15} {'Image'}")
        print("-" * 60)

    # Process each VM directory
    for vm_dir in vm_base_dir.glob("*"):
        if not vm_dir.is_dir():
            continue

        vm_data = {
            'name': read_json_file(str(vm_dir / "vm-manifest.json"), "name"),
            'image': read_json_file(str(vm_dir / "vm-manifest.json"), "image"),
        }

        instance_info_file = vm_dir / "shared" / ".instance_info"
        if instance_info_file.exists():
            instance_id = read_json_file(str(instance_info_file), "instance_id")
            app_id = read_json_file(str(instance_info_file), "app_id")
            vm_data.update({
                'instance_id': instance_id,
                'app_id': app_id,
                'ip': get_instance_ip(str(tproxy_state_file), instance_id),
                'vm_dir': str(vm_dir),
            })

            if args.verbose:
                vm_data['dashboard_url'] = get_dashboard_url(config, app_id)

            print_vm_info(vm_data, args.verbose)

if __name__ == "__main__":
    main()
