#!/usr/bin/env python3
"""Constraints validator for local development.
- Ensures there is exactly one app.py in the repository (at root).
- Ensures the business requirements document exists.
- Can be extended for more constraints in the future."""
import os
import sys


def _find_app_py_paths(root: str):
    paths = []
    for Dir, _, files in os.walk(root):
        if 'app.py' in files:
            paths.append(os.path.join(Dir, 'app.py'))
    return paths


def _ensure_single_app_py(repo_root: str) -> None:
    paths = _find_app_py_paths(repo_root)
    if len(paths) != 1 or os.path.basename(paths[0]) != 'app.py':
        print(
            f"Constraint violation: found {len(paths)} app.py files: {paths}",
            file=sys.stderr,
        )
        sys.exit(2)


def _check_required_doc(repo_root: str) -> None:
    requirement_path = os.path.join(repo_root, 'docs', '需求文档', '业务需求.md')
    if not os.path.isfile(requirement_path):
        print(
            f"Constraint violation: 业务需求.md not found at {requirement_path}",
            file=sys.stderr,
        )
        sys.exit(3)


def main():
    # 以脚本位置为仓库根（脚本通常放在仓库内）
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    _ensure_single_app_py(repo_root)
    _check_required_doc(repo_root)
    print("Constraints: OK")


if __name__ == '__main__':
    main()
