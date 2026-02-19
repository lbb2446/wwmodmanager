#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import subprocess
import requests
import signal
import threading
import atexit
from flask import Flask, render_template, jsonify, request, send_file
from urllib.parse import unquote, quote


def is_frozen():
    return getattr(sys, 'frozen', False)


def get_exe_dir():
    if is_frozen():
        return os.path.dirname(os.path.realpath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_base_dir():
    return get_exe_dir()


DEFAULT_CONFIG = {
    "app_title": "Mod Manager",
    "app_name": "Mod Manager",
    "icon_path": "icon.png"
}

def load_config():
    config_path = os.path.join(get_base_dir(), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    config_path = os.path.join(get_base_dir(), 'config.json')
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save config: {e}")
        return False

CONFIG = load_config()

# Favorites storage
FAVORITES_FILE = os.path.join(get_base_dir(), 'favorites.json')

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_favorites(favorites):
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save favorites: {e}")
        return False


def get_mods_root():
    return os.path.join(get_base_dir(), 'mods')


def get_chars_img_dir():
    return os.path.join(get_base_dir(), 'static', 'chars')


def get_resource_dir():
    if is_frozen():
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return meipass
    return os.path.dirname(os.path.abspath(__file__))


def _enforce_single_app_py():
    if not is_frozen():
        base = get_base_dir()
        paths = []
        for root, dirs, files in os.walk(base):
            if 'app.py' in files:
                paths.append(os.path.join(root, 'app.py'))
        if len(paths) != 1 or os.path.basename(paths[0]) != 'app.py':
            print(f"Constraint violation: app.py must exist exactly once at repo root. Found: {paths}", file=sys.stderr)
            sys.exit(1)


if is_frozen():
    os.chdir(get_base_dir())

os.makedirs(get_mods_root(), exist_ok=True)
os.makedirs(get_chars_img_dir(), exist_ok=True)

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

if not is_frozen():
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
    return render_template('index.html', app_title=CONFIG.get('app_title', 'Mod Manager'))

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(CONFIG)

@app.route('/api/config', methods=['POST'])
def update_config():
    global CONFIG
    new_config = request.json or {}
    CONFIG.update(new_config)
    if save_config(CONFIG):
        return jsonify({"status": "success", "config": CONFIG})
    return jsonify({"status": "error", "message": "Failed to save config"}), 500

@app.route('/api/debug_info', methods=['GET'])
def debug_info():
    return jsonify({
        "is_frozen": is_frozen(),
        "exe_dir": get_exe_dir(),
        "base_dir": get_base_dir(),
        "mods_root": get_mods_root(),
        "chars_img_dir": get_chars_img_dir(),
        "resource_dir": get_resource_dir(),
        "cwd": os.getcwd(),
    })

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
    
    favorites = load_favorites()
    mods = []
    for folder in os.listdir(char_path):
        full_path = os.path.join(char_path, folder)
        if not os.path.isdir(full_path):
            continue
        is_disabled = folder.startswith("DISABLED_")
        has_preview = find_preview_path(full_path) is not None
        preview_url = f"/api/preview?char={quote(char_name)}&mod={quote(folder)}" if has_preview else None
        clean_name = folder.replace("DISABLED_", "", 1) if is_disabled else folder
        mod_key = f"{char_name}:{folder}"
        is_favorite = favorites.get(mod_key, False)
        mods.append({
            "name": folder,
            "clean_name": clean_name,
            "disabled": is_disabled,
            "path": folder,
            "preview_url": preview_url,
            "favorite": is_favorite,
        })
    return jsonify(mods)

@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.json or {}
    char = data.get('char')
    mod = data.get('mod')
    if not char or not mod:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400
    
    favorites = load_favorites()
    mod_key = f"{char}:{mod}"
    
    if mod_key in favorites:
        del favorites[mod_key]
        is_favorite = False
    else:
        favorites[mod_key] = True
        is_favorite = True
    
    save_favorites(favorites)
    return jsonify({"status": "success", "favorite": is_favorite})

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
        target_dir = get_exe_dir()
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

@app.route('/api/open_mods_folder', methods=['POST'])
def open_mods_folder():
    try:
        target_dir = get_mods_root()
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
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

if not is_frozen():
    @app.route('/debug/info')
    def debug_info_dev():
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

def create_app_window(url):
    edge_paths = [
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
    ]
    edge_exe = None
    for path in edge_paths:
        if os.path.exists(path):
            edge_exe = path
            break
    
    chrome_paths = [
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break

    CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0
    
    if edge_exe:
        subprocess.Popen([
            edge_exe,
            '--new-window',
            '--app=' + url,
            '--window-size=1400,900',
            '--disable-extensions',
            '--disable-infobars',
            '--disable-popup-blocking',
        ], creationflags=CREATE_NO_WINDOW)
        return True
    elif chrome_exe:
        subprocess.Popen([
            chrome_exe,
            '--new-window',
            '--app=' + url,
            '--window-size=1400,900',
            '--disable-extensions',
            '--disable-popup-blocking',
        ], creationflags=CREATE_NO_WINDOW)
        return True
    return False

if __name__ == '__main__':
    _enforce_single_app_py()
    
    DEBUG = not is_frozen()
    port = 5000
    
    def run_server():
        global server_shutdown
        if is_frozen():
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
        url = f'http://127.0.0.1:{port}'
        wait_time = 2.0 if is_frozen() else 1.0
        time.sleep(wait_time)
        
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    break
            except:
                if i == max_retries - 1:
                    import webbrowser
                    webbrowser.open(url)
                    return
                time.sleep(0.5)
        
        if is_frozen():
            if not create_app_window(url):
                import webbrowser
                webbrowser.open(url)
        else:
            import webbrowser
            webbrowser.open(url)
    
    if not is_frozen() and DEBUG:
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
