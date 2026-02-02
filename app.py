import os
import re
import sys
import time
import requests
import signal
import threading
import atexit
from flask import Flask, render_template, jsonify, request, send_file
from urllib.parse import unquote, quote



def _base_dir():
    """打包成 exe 时固定为 exe 所在目录，否则为当前工作目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.realpath(sys.executable))
    return os.getcwd()

def _resource_dir():
    """打包后模板等资源在 _MEIPASS 内"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的临时目录
        try:
            return sys._MEIPASS
        except AttributeError:
            # 如果 _MEIPASS 不存在，使用 exe 所在目录
            return os.path.dirname(os.path.realpath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base_dir()
RESOURCE_DIR = _resource_dir()

# 动态获取路径的函数，确保每次运行都使用正确的 exe 位置
def get_base_dir():
    """动态获取基础目录"""
    return _base_dir()

def get_mods_root():
    """动态获取 MOD 根目录"""
    base_dir = get_base_dir()
    return os.path.join(base_dir, 'mods')

def get_chars_img_dir():
    """动态获取角色图片目录"""
    base_dir = get_base_dir()
    return os.path.join(base_dir, 'static', 'chars')

def get_resource_dir():
    """动态获取资源目录"""
    return _resource_dir()

# 为了向后兼容，保留这些变量但不推荐使用
MODS_ROOT = get_mods_root()
CHARS_IMG_DIR = get_chars_img_dir()

# 打包后把工作目录切到 exe 所在目录，避免其他代码用 getcwd() 时指向错误路径
if getattr(sys, 'frozen', False):
    os.chdir(BASE_DIR)

# 初始化时创建目录
mods_root = get_mods_root()
chars_img_dir = get_chars_img_dir()
os.makedirs(mods_root, exist_ok=True)
os.makedirs(chars_img_dir, exist_ok=True)

app = Flask(__name__,
    template_folder=os.path.join(get_resource_dir(), 'templates'),
    static_folder=os.path.join(get_base_dir(), 'static'))

# 全局变量用于服务器控制
server_shutdown = False
server_thread = None

def signal_handler(signum, frame):
    """处理关闭信号"""
    global server_shutdown
    print("\n收到关闭信号，正在优雅关闭服务器...")
    server_shutdown = True

def cleanup_on_exit():
    """退出时清理资源"""
    global server_shutdown
    server_shutdown = True
    print("正在清理资源...")

# 注册信号处理器和清理函数
if not getattr(sys, 'frozen', False):
    # 开发模式下注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_on_exit)

def sanitize_filename(name):
    """Windows 非法字符替换为下划线"""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'unnamed'


PREVIEW_NAMES = ('preview.png', 'preview.jpg', 'preview.jpeg')
# 支持的其他图片格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico'}


def find_preview_path(dir_path):
    """在目录下查找预览图，优先 preview.jpg/png/jpeg，如果没有则使用任何其他图片"""
    # 首先查找标准预览图
    for name in PREVIEW_NAMES:
        p = os.path.join(dir_path, name)
        if os.path.isfile(p):
            return p
    
    # 如果没有找到标准预览图，查找其他任何图片
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
    """返回本地已有角色列表（mods 下子文件夹 + 对应头像 + mod 数量），按 mod 数量降序"""
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
        "devcode": "Rsd3Gzn9vYJNp4EjcltoLSRD3u8V0rwx",
        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "source": "h5",
        "wiki_type": "9",
        "Referer": "https://wiki.kurobbs.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
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
            # 1. 创建角色文件夹（用安全名避免 Windows 非法字符）
            mods_root = get_mods_root()
            chars_img_dir = get_chars_img_dir()
            
            char_path = os.path.join(mods_root, safe_name)
            if not os.path.exists(char_path):
                os.makedirs(char_path)
            
            # 2. 保存头像到本地（头像在 content.contentUrl）
            content = item.get('content') or {}
            icon = content.get('contentUrl') or item.get('icon') or item.get('cover') or item.get('image')
            if icon:
                try:
                    img_resp = requests.get(icon, timeout=10)
                    img_resp.raise_for_status()
                    with open(os.path.join(chars_img_dir, f"{safe_name}.png"), 'wb') as f:
                        f.write(img_resp.content)
                except Exception:
                    pass
            saved_chars.append(safe_name)
        return jsonify({"status": "success", "count": len(saved_chars), "chars": saved_chars})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/preview')
def mod_preview():
    """返回某个 mod 下的 preview 图（支持 .png / .jpg / .jpeg）"""
    char = request.args.get('char')
    mod = request.args.get('mod')
    if not char or not mod:
        return '', 404
    char = unquote(char)
    mod = unquote(mod)
    mods_root = get_mods_root()
    mod_dir = os.path.join(mods_root, char, mod)
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
    action = data.get('action')  # 'enable', 'disable', 'enable_all', 'disable_all'
    if not char or not action:
        return jsonify({"status": "error", "message": "缺少参数"}), 400

    mods_root = get_mods_root()
    char_path = os.path.join(mods_root, char)
    if not os.path.isdir(char_path):
        return jsonify({"status": "error", "message": "角色目录不存在"}), 404

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
        # 启用当前 mod 时，先把该角色下其余 mod 全部禁用，再启用当前
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
    """优雅关闭服务器"""
    global server_shutdown
    if request.json and request.json.get('confirm') == True:
        server_shutdown = True
        return jsonify({"status": "shutting_down", "message": "服务器正在关闭..."})
    else:
        return jsonify({"status": "error", "message": "需要确认关闭操作"}), 400

# 开发模式专用路由
if not getattr(sys, 'frozen', False):
    @app.route('/debug/info')
    def debug_info():
        """开发模式调试信息"""
        import platform
        import flask
        
        return jsonify({
            "mode": "development",
            "python_version": platform.python_version(),
            "flask_version": getattr(flask, '__version__', 'unknown'),
            "debug": DEBUG,
            "base_dir": get_base_dir(),
            "mods_root": get_mods_root(),
            "static_dir": get_chars_img_dir(),
            "server": "Flask Development Server"
        })
    
    @app.route('/api/routes')
    def list_routes():
        """列出所有 API 路由"""
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
    # 开发模式配置
    DEBUG = True  # 设置为 False 进入生产模式
    port = 5000
    
    def run_server():
        global server_shutdown
        if getattr(sys, 'frozen', False):
            # 打包版本：使用 Waitress 生产服务器
            import waitress
            try:
                waitress.serve(app, host='127.0.0.1', port=port, threads=4)
            except KeyboardInterrupt:
                print("服务器被用户中断")
        else:
            # 开发版本：使用 Flask 开发服务器
            if DEBUG:
                print("🔧 开发模式已启用")
                print(f"📍 服务器地址: http://127.0.0.1:{port}")
                print("🔄 热重载已开启")
                app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True)
            else:
                app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    
    def create_window():
        import time
        import webbrowser
        import subprocess
        import os
        import sys
        
        url = f'http://127.0.0.1:{port}'
        
        # 等待服务器启动，生产模式需要更长时间
        wait_time = 2.0 if getattr(sys, 'frozen', False) else 1.0
        time.sleep(wait_time)  # 等待服务器启动
        
        # 检查服务器是否真的启动了
        import requests
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    break
            except:
                if i == max_retries - 1 and getattr(sys, 'frozen', False):
                    # 生产模式下如果服务器启动失败，回退到默认浏览器
                    webbrowser.open(url)
                    return
                time.sleep(0.5)
        
        # Edge 可能的安装路径
        edge_paths = [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
        ]
        
        edge_exe = None
        for path in edge_paths:
            if os.path.exists(path):
                edge_exe = path
                break
        
        try:
            if edge_exe:
                # 使用完整路径启动 Edge 应用模式
                subprocess.Popen([
                    edge_exe,
                    '--app=' + url,
                    '--window-size=1400,900',
                    '--disable-extensions',
                    '--disable-infobars',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ])
                if getattr(sys, 'frozen', False):
                    pass  # 生产模式不打印
                else:
                    print(f"已启动独立窗口: {edge_exe}")
            else:
                # 查找 Chrome
                chrome_paths = [
                    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe'
                ]
                
                chrome_exe = None
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_exe = path
                        break
                
                if chrome_exe:
                    subprocess.Popen([
                        chrome_exe,
                        '--app=' + url,
                        '--window-size=1400,900',
                        '--disable-extensions'
                    ])
                    print(f"已启动 Chrome 应用模式: {chrome_exe}")
                else:
                    raise FileNotFoundError("找不到 Chrome 或 Edge")
                    
        except Exception as e:
            if getattr(sys, 'frozen', False):
                # 生产模式静默处理
                webbrowser.open(url)
            else:
                # 开发模式显示详细错误
                print(f"无法创建独立窗口: {e}")
                print("使用默认浏览器")
                webbrowser.open(url)
    
    # 开发模式：直接运行服务器（包含自动打开浏览器）
    if not getattr(sys, 'frozen', False) and DEBUG:
        print("\n" + "="*50)
        print("MOD 管理器 - 开发模式")
        print("="*50)
        print("MOD 管理器 - 开发模式")
        print("="*50)
        print(f"主页: http://127.0.0.1:{port}")
        print(f"调试信息: http://127.0.0.1:{port}/debug/info")
        print(f"API 路由: http://127.0.0.1:{port}/api/routes")
        print(f"工作目录: {get_base_dir()}")
        print(f"MOD 目录: {get_mods_root()}")
        print("="*50)
        print("按 Ctrl+C 停止服务器\n")
        
        # 直接启动开发服务器
        app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True)
    else:
        # 生产模式或打包版本：使用多线程
        import threading
        
        # 服务器线程必须是非守护线程，这样主线程退出时服务才会停止
        server_thread = threading.Thread(target=run_server, daemon=False)
        server_thread.start()
        
        # 等待一下确保服务器开始监听
        time.sleep(0.5)
        
        # 窗口线程
        window_thread = threading.Thread(target=create_window, daemon=False)
        window_thread.start()
        
        # 无论是开发模式还是生产模式，都要保持主线程运行
        # 这样可以确保服务器持续运行
        try:
            while not server_shutdown:
                time.sleep(0.5)
                # 检查服务器线程是否还活着
                if server_thread and not server_thread.is_alive():
                    print("服务器线程意外退出，正在重启...")
                    server_thread = threading.Thread(target=run_server, daemon=False)
                    server_thread.start()
                    time.sleep(2)  # 给服务器启动时间
        except KeyboardInterrupt:
            print("收到中断信号，正在停止服务器...")
        finally:
            print("服务器已停止")