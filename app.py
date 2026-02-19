#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import subprocess
import requests
import signal
import threading
import atexit
from flask import Flask, render_template, jsonify, request, send_file
from urllib.parse import unquote, quote


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.realpath(sys.executable))
    return os.getcwd()

def _resource_dir():
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return meipass
        return os.path.dirname(os.path.realpath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base_dir()
RESOURCE_DIR = _resource_dir()

def _exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.realpath(sys.executable))
    return BASE_DIR

def _enforce_single_app_py():
    base = BASE_DIR
    paths = []
    for root, dirs, files in os.walk(base):
        if 'app.py' in files:
            paths.append(os.path.join(root, 'app.py'))
    if len(paths) != 1 or os.path.basename(paths[0]) != 'app.py':
        print(f"Constraint violation: app.py must exist exactly once at repo root. Found: {paths}", file=sys.stderr)
        sys.exit(1)

def get_base_dir():
    return _base_dir()

def get_mods_root():
    base_dir = get_base_dir()
    return os.path.join(base_dir, 'mods')

def get_chars_img_dir():
    base_dir = get_base_dir()
    return os.path.join(base_dir, 'static', 'chars')

def get_resource_dir():
    return _resource_dir()

MODS_ROOT = get_mods_root()
CHARS_IMG_DIR = get_chars_img_dir()

if getattr(sys, 'frozen', False):
    os.chdir(BASE_DIR)

mods_root = get_mods_root()
chars_img_dir = get_chars_img_dir()
os.makedirs(mods_root, exist_ok=True)
os.makedirs(chars_img_dir, exist_ok=True)

app = Flask(__name__,
    template_folder=os.path.join(get_resource_dir(), 'templates'),
    static_folder=os.path.join(get_base_dir(), 'static'))

server_shutdown = False
server_thread = None

def signal_handler(signum, frame):
    global server_shutdown
    print("\nReceived shutdown signal, closing server gracefully...")
    server_shutdown = True

def cleanup_on_exit():
    global server_shutdown
    server_shutdown = True
    print("Cleaning up resources...")

if not getattr(sys, 'frozen', False):
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_on_exit)

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'unnamed'

PREVIEW_NAMES = ('preview.png', 'preview.jpg', 'preview.jpeg')
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico'}

def find_preview_path(dir_path):
    for name in PREVIEW_NAMES:
        p = os.path.join(dir_path, name)
        if os.path.isfile(p):
            return p
    try:
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            if os.path.isfile(item_path):
                _, ext = os.path.splitext(item.lower())
                if ext in IMAGE_EXTENSIONS and item.lower() not in PREVIEW_NAMES:
                    return item_path
    except OSError:
        pass
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chars', methods=['GET'])
def get_chars():
    mods_root = get_mods_root()
    chars_img_dir = get_chars_img_dir()
    if not os.path.exists(mods_root):
        return jsonify([])
    chars = []
    for name in os.listdir(mods_root):
        full = os.path.join(mods_root, name)
        if not os.path.isdir(full):
            continue
        safe = sanitize_filename(name)
        img_path = os.path.join(chars_img_dir, f"{safe}.png")
        image_url = f"/static/chars/{safe}.png" if os.path.exists(img_path) else None
        mod_count = sum(1 for x in os.listdir(full) if os.path.isdir(os.path.join(full, x)))
        chars.append({"name": name, "image_url": image_url, "mod_count": mod_count})
    chars.sort(key=lambda c: c["mod_count"], reverse=True)
    return jsonify(chars)

@app.route('/api/sync_chars', methods=['POST'])
def sync_chars():
    url = "https://api.kurobbs.com/wiki/core/catalogue/item/getPage"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "user-agent": "Mozilla/5.0",
    }
    data = "catalogueId=1105&page=1&limit=1000"
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        data_obj = body.get('data') or {}
        results = data_obj.get('results') if isinstance(data_obj, dict) else {}
        items = (results.get('records') if isinstance(results, dict) else None) or []
        if not items and isinstance(data_obj, dict):
            items = data_obj.get('list') or data_obj.get('items') or []
        if not items and isinstance(data_obj, list):
            items = data_obj

        saved_chars = []
        for item in items:
            name = item.get('name') or item.get('title') or ''
            if not name:
                continue
            safe_name = sanitize_filename(name)
            char_path = os.path.join(get_mods_root(), safe_name)
            if not os.path.exists(char_path):
                os.makedirs(char_path)
            content = item.get('content') or {}
            icon = content.get('contentUrl') or item.get('icon') or item.get('cover') or item.get('image')
            if icon:
                try:
                    img_resp = requests.get(icon, timeout=10)
                    img_resp.raise_for_status()
                    with open(os.path.join(get_chars_img_dir(), f"{safe_name}.png"), 'wb') as f:
                        f.write(img_resp.content)
                except Exception:
                    pass
            saved_chars.append(safe_name)
        return jsonify({"status": "success", "count": len(saved_chars), "chars": saved_chars})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/preview')
def mod_preview():
    char = request.args.get('char')
    mod = request.args.get('mod')
    if not char or not mod:
        return '', 404
    char = unquote(char)
    mod = unquote(mod)
    mod_dir = os.path.join(get_mods_root(), char, mod)
    preview_path = find_preview_path(mod_dir)
    if not preview_path:
        return '', 404
    ext = os.path.splitext(preview_path)[1].lower()
    mimetype = 'image/jpeg' if ext in ('.jpg', '.jpeg') else 'image/png'
    return send_file(preview_path, mimetype=mimetype)

@app.route('/api/get_mods', methods=['GET'])
def get_mods():
    char_name = request.args.get('char')
    if not char_name:
        return jsonify([])
    mods_root = get_mods_root()
    char_path = os.path.join(mods_root, char_name)
    if not os.path.exists(char_path) or not os.path.isdir(char_path):
        return jsonify([])
    mods = []
    for folder in os.listdir(char_path):
        full_path = os.path.join(char_path, folder)
        if not os.path.isdir(full_path):
            continue
        is_disabled = folder.startswith("DISABLED_")
        has_preview = find_preview_path(full_path) is not None
        preview_url = f"/api/preview?char={quote(char_name)}&mod={quote(folder)}" if has_preview else None
        clean_name = folder.replace("DISABLED_", "", 1) if is_disabled else folder
        mods.append({
            "name": folder,
            "clean_name": clean_name,
            "disabled": is_disabled,
            "path": folder,
            "preview_url": preview_url,
        })
    return jsonify(mods)

@app.route('/api/toggle', methods=['POST'])
def toggle_mod():
    data = request.json or {}
    char = data.get('char')
    mod_name = data.get('mod', '')
    action = data.get('action')
    if not char or not action:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400
    mods_root = get_mods_root()
    char_path = os.path.join(mods_root, char)
    if not os.path.isdir(char_path):
        return jsonify({"status": "error", "message": "Character directory not found"}), 404
    def rename_mod(current_name, target_state):
        src = os.path.join(char_path, current_name)
        if not os.path.isdir(src):
            return
        is_disabled = current_name.startswith("DISABLED_")
        if target_state == 'disable' and not is_disabled:
            dst = os.path.join(char_path, f"DISABLED_{current_name}")
            if not os.path.exists(dst):
                os.rename(src, dst)
        elif target_state == 'enable' and is_disabled:
            new_name = current_name.replace("DISABLED_", "", 1)
            dst = os.path.join(char_path, new_name)
            if not os.path.exists(dst):
                os.rename(src, dst)
    if action == 'enable':
        all_dirs = [d for d in os.listdir(char_path) if os.path.isdir(os.path.join(char_path, d))]
        for d in all_dirs:
            rename_mod(d, 'disable')
        rename_mod(mod_name, 'enable')
    elif action == 'disable':
        rename_mod(mod_name, action)
    elif action == 'enable_all':
        for m in os.listdir(char_path):
            rename_mod(m, 'enable')
    elif action == 'disable_all':
        for m in os.listdir(char_path):
            rename_mod(m, 'disable')
    return jsonify({"status": "success"})

@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    global server_shutdown
    if request.json and request.json.get('confirm') == True:
        server_shutdown = True
        return jsonify({"status": "shutting_down", "message": "Server is shutting down..."})
    else:
        return jsonify({"status": "error", "message": "Confirmation required"}), 400

@app.route('/api/open_exe_folder', methods=['POST'])
def open_exe_folder():
    try:
        target_dir = _exe_dir()
        if not os.path.isdir(target_dir):
            return jsonify({"status": "error", "message": "Directory not found"}), 404
        if sys.platform.startswith('win'):
            os.startfile(target_dir)
        else:
            import platform
            if platform.system() == 'Darwin':
                subprocess.Popen(['open', target_dir])
            else:
                subprocess.Popen(['xdg-open', target_dir])
        return jsonify({"status": "success", "path": target_dir})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if not getattr(sys, 'frozen', False):
    @app.route('/debug/info')
    def debug_info():
        import platform
        import flask
        return jsonify({
            "mode": "development",
            "python_version": platform.python_version(),
            "flask_version": getattr(flask, '__version__', 'unknown'),
            "debug": True,
            "base_dir": get_base_dir(),
            "mods_root": get_mods_root(),
            "static_dir": get_chars_img_dir(),
            "server": "Flask Development Server"
        })
    @app.route('/api/routes')
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            methods = list(rule.methods) if rule.methods else []
            routes.append({
                "endpoint": rule.endpoint,
                "methods": methods,
                "rule": str(rule)
            })
        return jsonify(routes)

if __name__ == '__main__':
    DEBUG = False
    port = 5000
    def run_server():
        global server_shutdown
        if getattr(sys, 'frozen', False):
            import waitress
            try:
                waitress.serve(app, host='127.0.0.1', port=port, threads=4)
            except KeyboardInterrupt:
                print("Server interrupted by user")
        else:
            if DEBUG:
                print("[DEV] Development mode enabled")
                print(f"[DEV] Server address: http://127.0.0.1:{port}")
                print("[DEV] Hot reload enabled")
                app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True)
            else:
                app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    def create_window():
        try:
            import time, webbrowser
            url = f'http://127.0.0.1:{port}'
            time.sleep(1)
            webbrowser.open(url)
        except Exception:
            pass
    if not getattr(sys, 'frozen', False) and DEBUG:
        run_server()
    else:
        server_thread = threading.Thread(target=run_server, daemon=False)
        server_thread.start()
        window_thread = threading.Thread(target=create_window, daemon=False)
        window_thread.start()
        try:
            while not server_shutdown:
                time.sleep(0.5)
                if server_thread and not server_thread.is_alive():
                    server_thread = threading.Thread(target=run_server, daemon=False)
                    server_thread.start()
                    time.sleep(2)
        except KeyboardInterrupt:
            print("Received interrupt signal, stopping server...")
        finally:
            print("Server stopped")
