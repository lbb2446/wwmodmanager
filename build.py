#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import subprocess
import re

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
    spec_content = re.sub(r"name='ModManager'", f"name='{app_name}'", spec_content)
    
    # Add icon if file exists
    if os.path.exists(icon_path):
        # Find the EXE line with name and add icon after it
        pattern = r"(name='[^']+',)(\s*\n\s*)"
        replacement = r"\1\n    icon='" + icon_path + "',\2"
        if 'icon=' not in spec_content:
            spec_content = re.sub(pattern, replacement, spec_content)
    
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
