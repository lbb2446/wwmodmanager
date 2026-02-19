#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import subprocess

def main():
    # Read config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    app_name = config.get('app_name', 'ModManager')
    icon_path = config.get('icon_path', 'icon.png')
    
    print(f"App Name: {app_name}")
    print(f"Icon: {icon_path}")
    
    # Read spec file
    spec_path = os.path.join(os.path.dirname(__file__), 'mod_manager.spec')
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec_content = f.read()
    
    # Replace name in EXE section
    spec_content = spec_content.replace("name='ModManager'", f"name='{app_name}'")
    
    # Add icon if file exists and icon not already in spec
    if os.path.exists(icon_path) and 'icon=' not in spec_content:
        # Find the line with name='app_name' and add icon on next line
        lines = spec_content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if f"name='{app_name}'" in line:
                new_lines.append(f"    icon='{icon_path}',")
        spec_content = '\n'.join(new_lines)
    
    # Write modified spec
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("Spec file updated.")
    
    # Build
    print("Starting PyInstaller...")
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', 'mod_manager.spec', '--clean'],
        capture_output=False
    )
    
    if result.returncode == 0:
        print(f"\nBuild successful!")
        print(f"Output: dist/{app_name}.exe")
    else:
        print("Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
