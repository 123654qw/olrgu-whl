# -*- coding: utf-8 -*-
"""
olrgu - 局域网文件分享工具
简洁、高效的本地文件服务器，支持文件预览和密码保护
"""

import os
import sys
import socket
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import mimetypes
import urllib.parse
import json

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# 全局变量：跟踪活动服务器数量（限制为2个）
_active_servers = 0
_MAX_SERVERS = 2


def get_resource_path(filename):
    """获取包内资源文件的路径（兼容 wheel 安装和开发模式）"""
    try:
        from importlib import resources
        if hasattr(resources, 'files'):
            ref = resources.files("olrgu").joinpath("resources", filename)
            return str(ref)
    except Exception:
        pass

    try:
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        resource_path = os.path.join(pkg_dir, "resources", filename)
        if os.path.exists(resource_path):
            return resource_path
    except Exception:
        pass

    return filename


class FileServer(HTTPServer):
    """自定义HTTP服务器，支持密码保护和文件预览"""

    def __init__(self, server_address, handler_class, share_path, password=None):
        super().__init__(server_address, handler_class)
        self.share_path = share_path
        self.is_file = os.path.isfile(share_path)
        self.password = password
        self.authenticated = set()


class FileHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        server = self.server
        client_ip = self.client_address[0]
        if server.password and client_ip not in server.authenticated:
            self.send_auth_required()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed_path.path)

        if path == '/':
            self.serve_index()
        elif path == '/auth':
            self.handle_auth(parsed_path.query)
        else:
            self.serve_file(path[1:])

    def do_POST(self):
        server = self.server
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json_response({'success': False, 'error': '请求格式错误'})
            return
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(post_data)
            if data.get('password') == server.password:
                client_ip = self.client_address[0]
                server.authenticated.add(client_ip)
                self.send_json_response({'success': True})
            else:
                self.send_json_response({'success': False, 'error': '密码错误'})
        except Exception:
            self.send_json_response({'success': False, 'error': '请求格式错误'})

    def handle_auth(self, query):
        try:
            params = urllib.parse.parse_qs(query)
            password = params.get('password', [''])[0]
            server = self.server
            if password == server.password:
                client_ip = self.client_address[0]
                server.authenticated.add(client_ip)
                self.send_json_response({'success': True})
            else:
                self.send_json_response({'success': False, 'error': '密码错误'})
        except Exception:
            self.send_json_response({'success': False, 'error': '请求格式错误'})

    def serve_index(self):
        server = self.server
        share_path = Path(server.share_path)
        html = self.generate_html(share_path)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def generate_html(self, share_path):
        files = []
        server = self.server

        if server.is_file:
            share_path_obj = Path(server.share_path)
            files.append({
                'name': share_path_obj.name,
                'is_dir': False,
                'size': share_path_obj.stat().st_size,
                'path': share_path_obj.name
            })
        else:
            for item in share_path.iterdir():
                if item.name.startswith('.'):
                    continue
                files.append({
                    'name': item.name,
                    'is_dir': item.is_dir(),
                    'size': item.stat().st_size if item.is_file() else 0,
                    'path': item.name
                })
            files.sort(key=lambda x: (x['is_dir'], x['name']))

        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>olrgu - 文件分享</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            font-size: 24px;
            font-weight: 400;
            margin-bottom: 30px;
            color: #fff;
            border-bottom: 1px solid #333;
            padding-bottom: 15px;
        }
        .file-list {
            background: #141414;
            border: 1px solid #2a2a2a;
        }
        .file-item {
            padding: 12px 20px;
            border-bottom: 1px solid #1f1f1f;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: background 0.15s;
        }
        .file-item:hover { background: #1a1a1a; }
        .file-item:last-child { border-bottom: none; }
        .file-info {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }
        .file-icon { font-size: 20px; width: 30px; text-align: center; }
        .file-name {
            color: #e0e0e0;
            text-decoration: none;
            font-size: 14px;
        }
        .file-name:hover { color: #4a9eff; }
        .file-size { color: #666; font-size: 12px; margin-left: 10px; }
        .file-actions { display: flex; gap: 10px; }
        .btn {
            padding: 6px 14px;
            font-size: 12px;
            border: 1px solid #333;
            background: transparent;
            color: #e0e0e0;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
        }
        .btn:hover {
            background: #2a2a2a;
            border-color: #4a9eff;
            color: #4a9eff;
        }
        .preview-modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .preview-content {
            max-width: 90%;
            max-height: 90%;
            background: #141414;
            border: 1px solid #333;
            padding: 20px;
            overflow: auto;
        }
        .preview-close {
            position: absolute;
            top: 20px; right: 30px;
            color: #fff;
            font-size: 30px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>olrgu 文件分享</h1>
    <div class="file-list">
"""

        if not files:
            html += '<div class="file-item" style="color:#666;">暂无共享文件</div>'
        else:
            for f in files:
                icon = '\U0001f4c1' if f['is_dir'] else self.get_file_icon(f['name'])
                size_str = self.format_size(f['size']) if not f['is_dir'] else ''
                preview_btn = ''
                if not f['is_dir'] and self.can_preview(f['name']):
                    preview_btn = f'<a href="#" class="btn" onclick="previewFile(\'{f["name"]}\');return false;">预览</a>'
                html += f'''
        <div class="file-item">
            <div class="file-info">
                <span class="file-icon">{icon}</span>
                <a href="/{urllib.parse.quote(f['name'])}" class="file-name">{f['name']}</a>
                <span class="file-size">{size_str}</span>
            </div>
            <div class="file-actions">
                {preview_btn}
                <a href="/{urllib.parse.quote(f['name'])}" download class="btn">下载</a>
            </div>
        </div>
'''

        html += '''
    </div>
    <div id="previewModal" class="preview-modal">
        <span class="preview-close" onclick="closePreview()">&times;</span>
        <div class="preview-content" id="previewContent"></div>
    </div>
    <script>
        function previewFile(filename) {
            const modal = document.getElementById('previewModal');
            const content = document.getElementById('previewContent');
            modal.style.display = 'flex';
            const ext = filename.split('.').pop().toLowerCase();
            if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
                content.innerHTML = `<img src="/${filename}" style="max-width:100%;">`;
            } else if (['txt','md','json','xml','html','css','js','py'].includes(ext)) {
                fetch('/' + filename)
                    .then(r => r.text())
                    .then(t => {
                        content.innerHTML = `<pre style="color:#e0e0e0;white-space:pre-wrap;">${t}</pre>`;
                    });
            } else if (['pdf'].includes(ext)) {
                content.innerHTML = `<iframe src="/${filename}" style="width:100%;height:80vh;"></iframe>`;
            } else {
                content.innerHTML = '<p style="color:#666;">该文件类型不支持预览</p>';
            }
        }
        function closePreview() {
            document.getElementById('previewModal').style.display = 'none';
        }
    </script>
</body>
</html>
'''
        return html

    def can_preview(self, filename):
        ext = filename.split('.')[-1].lower()
        return ext in ['jpg','jpeg','png','gif','webp','txt','md','json','xml','html','css','js','py','pdf']

    def get_file_icon(self, filename):
        ext = filename.split('.')[-1].lower()
        icons = {
            'jpg':'\U0001f5bc','jpeg':'\U0001f5bc','png':'\U0001f5bc','gif':'\U0001f5bc','webp':'\U0001f5bc',
            'pdf':'\U0001f4c4','txt':'\U0001f4dd','md':'\U0001f4dd','doc':'\U0001f4c4','docx':'\U0001f4c4',
            'xls':'\U0001f4ca','xlsx':'\U0001f4ca','zip':'\U0001f4e6','rar':'\U0001f4e6',
            'mp4':'\U0001f3ac','mp3':'\U0001f3b5','wav':'\U0001f3b5',
            'py':'\U0001f40d','js':'\U0001f4dc','html':'\U0001f310','css':'\U0001f3a8'
        }
        return icons.get(ext, '\U0001f4c4')

    def format_size(self, size):
        for unit in ['B','KB','MB','GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def serve_file(self, filename):
        server = self.server
        if server.is_file:
            file_path = Path(server.share_path)
        else:
            share_path = Path(server.share_path)
            file_path = share_path / filename
            try:
                file_path_resolved = file_path.resolve()
                share_path_resolved = share_path.resolve()
                if not str(file_path_resolved).startswith(str(share_path_resolved)):
                    self.send_error(403, "禁止访问")
                    return
            except Exception:
                self.send_error(404, "文件不存在")
                return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, '文件不存在')
            return

        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = 'application/octet-stream'

            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.send_header('Content-Disposition', f'inline; filename="{urllib.parse.quote(file_path.name)}"')
            self.send_header('Content-Length', str(file_path.stat().st_size))
            self.end_headers()

            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f'服务器错误: {str(e)}')

    def send_auth_required(self):
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>olrgu - 需要密码</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-box {
            background: #141414;
            border: 1px solid #333;
            padding: 40px;
            min-width: 320px;
        }
        .login-box h2 {
            font-size: 18px;
            font-weight: 400;
            margin-bottom: 25px;
            color: #fff;
        }
        .login-box input {
            width: 100%;
            padding: 12px;
            background: #0a0a0a;
            border: 1px solid #333;
            color: #e0e0e0;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .login-box button {
            width: 100%;
            padding: 12px;
            background: #4a9eff;
            border: none;
            color: #fff;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.15s;
        }
        .login-box button:hover { background: #3a8eef; }
        .error-msg {
            color: #ff4a4a;
            font-size: 12px;
            margin-bottom: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>olrgu 文件分享</h2>
        <div class="error-msg" id="errorMsg">密码错误</div>
        <input type="password" id="password" placeholder="请输入访问密码" autofocus>
        <button onclick="login()">访问</button>
    </div>
    <script>
        function login() {
            const pwd = document.getElementById('password').value;
            fetch('/api/auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: pwd})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    document.getElementById('errorMsg').style.display = 'block';
                    document.getElementById('password').value = '';
                }
            });
        }
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') login();
        });
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        pass


class OlrguApp:
    """olrgu GUI 应用程序"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("olrgu")
        self.root.geometry("650x500")
        self.root.configure(bg="#0a0a0a")
        self.root.after(100, self.set_icon)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.share_path = None
        self.server = None
        self.server_thread = None
        self.is_running = False
        self._icon_img = None

        self.setup_ui()

    def set_icon(self):
        try:
            png_path = get_resource_path('icon.png')
            if png_path and os.path.exists(png_path):
                img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, img)
                self._icon_img = img
        except Exception as e:
            print(f"设置图标失败: {e}")

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="#0a0a0a", border_width=0)
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        title_label = ctk.CTkLabel(
            main_frame, text="olrgu",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="normal"),
            text_color="#ffffff"
        )
        title_label.pack(pady=(0, 10))

        subtitle_label = ctk.CTkLabel(
            main_frame, text="局域网文件分享工具",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#666666"
        )
        subtitle_label.pack(pady=(0, 30))

        file_frame = ctk.CTkFrame(main_frame, fg_color="#141414", border_width=1, border_color="#2a2a2a")
        file_frame.pack(fill="x", pady=(0, 15))

        file_label = ctk.CTkLabel(
            file_frame, text="共享内容",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#999999", anchor="w"
        )
        file_label.pack(fill="x", padx=15, pady=(10, 5))

        select_btn_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
        select_btn_frame.pack(fill="x", padx=15, pady=(0, 5))

        self.select_dir_btn = ctk.CTkButton(
            select_btn_frame, text="选择文件夹", command=self.select_directory,
            height=28, fg_color="#2a2a2a", hover_color="#3a3a3a",
            text_color="#e0e0e0", font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=0, width=100
        )
        self.select_dir_btn.pack(side="left", padx=(0, 10))

        self.select_file_btn = ctk.CTkButton(
            select_btn_frame, text="选择文件", command=self.select_file,
            height=28, fg_color="#2a2a2a", hover_color="#3a3a3a",
            text_color="#e0e0e0", font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=0, width=100
        )
        self.select_file_btn.pack(side="left")

        self.file_path_var = ctk.StringVar(value="未选择")
        self.file_path_label = ctk.CTkLabel(
            file_frame, textvariable=self.file_path_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#4a9eff", anchor="w", height=30
        )
        self.file_path_label.pack(fill="x", padx=15, pady=(5, 10))

        settings_frame = ctk.CTkFrame(main_frame, fg_color="#141414", border_width=1, border_color="#2a2a2a")
        settings_frame.pack(fill="x", pady=(0, 15))

        port_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=15, pady=10)

        port_label = ctk.CTkLabel(
            port_frame, text="端口号",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#999999", width=80, anchor="w"
        )
        port_label.pack(side="left")

        self.port_entry = ctk.CTkEntry(
            port_frame, placeholder_text="四位端口号 (如: 8000)",
            width=120, height=30, border_width=1, border_color="#333333",
            fg_color="#0a0a0a", text_color="#e0e0e0",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.port_entry.pack(side="left", padx=(0, 10))
        self.port_entry.insert(0, "8000")

        pwd_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        pwd_frame.pack(fill="x", padx=15, pady=(0, 10))

        pwd_label = ctk.CTkLabel(
            pwd_frame, text="访问密码",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#999999", width=80, anchor="w"
        )
        pwd_label.pack(side="left")

        self.pwd_entry = ctk.CTkEntry(
            pwd_frame, placeholder_text="可选，六位以内",
            width=120, height=30, border_width=1, border_color="#333333",
            fg_color="#0a0a0a", text_color="#e0e0e0",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            show="\u2022"
        )
        self.pwd_entry.pack(side="left")

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 15))

        self.start_btn = ctk.CTkButton(
            button_frame, text="启动服务", command=self.start_server,
            height=35, fg_color="#4a9eff", hover_color="#3a8eef",
            text_color="#ffffff", font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=0
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = ctk.CTkButton(
            button_frame, text="停止服务", command=self.stop_server,
            height=35, fg_color="#333333", hover_color="#444444",
            text_color="#e0e0e0", font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=0, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        self.browser_btn = ctk.CTkButton(
            button_frame, text="打开浏览器", command=self.open_browser,
            height=35, fg_color="#333333", hover_color="#444444",
            text_color="#e0e0e0", font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=0, state="disabled"
        )
        self.browser_btn.pack(side="left")

        self.status_text = ctk.CTkTextbox(
            main_frame, height=100,
            fg_color="#141414", border_width=1, border_color="#2a2a2a",
            text_color="#999999", font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.status_text.pack(fill="x")
        self.status_text.insert("1.0", "\u5c31\u7eea\n")
        self.status_text.configure(state="disabled")

    def select_directory(self):
        directory = filedialog.askdirectory(title="\u9009\u62e9\u5171\u4eab\u76ee\u5f55")
        if directory:
            self.share_path = directory
            self.file_path_var.set(f"[\u6587\u4ef6\u5939] {directory}")

    def select_file(self):
        file = filedialog.askopenfilename(title="\u9009\u62e9\u6587\u4ef6")
        if file:
            self.share_path = file
            self.file_path_var.set(f"[\u6587\u4ef6] {file}")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def check_port(self, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except OSError:
            return False

    def start_server(self):
        global _active_servers
        if self.is_running:
            return
        if _active_servers >= _MAX_SERVERS:
            messagebox.showerror("\u63d0\u793a", "\u4f60\u9700\u8981\u8ba2\u9605\u624d\u53ef\u4ee5\u8fd0\u884c\u66f4\u591a\u7684olrgu")
            return

        port_str = self.port_entry.get().strip()
        if not port_str.isdigit() or len(port_str) != 4:
            messagebox.showerror("\u9519\u8bef", "\u8bf7\u8f93\u5165\u56db\u4f4d\u7aef\u53e3\u53f7")
            return
        port = int(port_str)

        if not self.check_port(port):
            messagebox.showerror("\u9519\u8bef", f"\u7aef\u53e3 {port} \u5df2\u88ab\u5380\u7528\uff0c\u8bf7\u9009\u62e9\u5176\u4ed6\u7aef\u53e3")
            return

        if not self.share_path or not os.path.exists(self.share_path):
            messagebox.showerror("\u9519\u8bef", "\u8bf7\u9009\u62e9\u6587\u4ef6\u6216\u76ee\u5f55")
            return

        password = self.pwd_entry.get().strip()
        if password and (len(password) > 6 or not password.isdigit()):
            messagebox.showerror("\u9519\u8bef", "\u5bc6\u7801\u5fc5\u987b\u662f\u516d\u4f4d\u4ee5\u5185\u7684\u6570\u5b57")
            return

        try:
            self.server = FileServer(
                ("0.0.0.0", port), FileHandler,
                self.share_path, password if password else None
            )
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.is_running = True
            _active_servers += 1

            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.browser_btn.configure(state="normal")

            local_ip = self.get_local_ip()
            self.update_status(f"\u670d\u52a1\u5df2\u542f\u52a8\n")
            self.update_status(f"\u672c\u5730\u8bbf\u95ee: http://localhost:{port}\n")
            self.update_status(f"\u5c40\u57df\u7f51\u8bbf\u95ee: http://{local_ip}:{port}\n")
            self.update_status(f"\u5171\u4eab\u76ee\u5f55: {self.share_path}\n")
            if password:
                self.update_status(f"\u8bbf\u95ee\u5bc6\u7801: {password}\n")
        except Exception as e:
            messagebox.showerror("\u9519\u8bef", f"\u542f\u52a8\u670d\u52a1\u5668\u5931\u8d25: {str(e)}")

    def stop_server(self):
        global _active_servers
        if not self.is_running:
            return
        try:
            self.server.shutdown()
            self.server.server_close()
            self.is_running = False
            _active_servers -= 1

            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.browser_btn.configure(state="disabled")
            self.update_status("\u670d\u52a1\u5df2\u505c\u6b62\n")
        except Exception as e:
            messagebox.showerror("\u9519\u8bef", f"\u505c\u6b62\u670d\u52a1\u5668\u5931\u8d25: {str(e)}")

    def open_browser(self):
        if not self.is_running:
            return
        port = self.port_entry.get().strip()
        webbrowser.open(f"http://localhost:{port}")

    def update_status(self, message):
        self.status_text.configure(state="normal")
        self.status_text.insert("end", message)
        self.status_text.see("end")
        self.status_text.configure(state="disabled")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        if self.is_running:
            self.stop_server()
        self.root.destroy()


# ========== 模块级工具函数 ==========

def check_port(port):
    """检查端口是否可用（模块级，供 Server 类使用）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError:
        return False


def get_local_ip():
    """获取本机局域网 IP（模块级）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ========== 纯代码 API（无 GUI）==========

class Server:
    """服务器控制对象，支持纯代码启动/停止

    Usage::
        >>> import olrgu
        >>> server = olrgu.share(path=r"E:\\共享", port=8000, block=False)
        >>> # ... do stuff ...
        >>> server.stop()
    """

    def __init__(self, path=".", port=8000, password=None):
        self.path = os.path.abspath(path)
        self.port = port
        self.password = password
        self._server = None
        self._thread = None

    def start(self, block=True):
        """启动服务器

        :param block: True=阻塞运行（按 Ctrl+C 停止），
                      False=后台运行，返回 self 可后续 stop()
        """
        if self._server is not None:
            print("olrgu: 服务器已在运行")
            return
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"路径不存在: {self.path}")
        if not check_port(self.port):
            raise OSError(f"端口 {self.port} 已被占用")
        global _active_servers
        if _active_servers >= _MAX_SERVERS:
            raise RuntimeError("已达最大服务实例数（2个）")

        self._server = FileServer(
            ("0.0.0.0", self.port),
            FileHandler,
            self.path,
            self.password
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        _active_servers += 1

        ip = get_local_ip()
        print("olrgu 服务已启动")
        print(f"  本地: http://localhost:{self.port}")
        print(f"  局域网: http://{ip}:{self.port}")
        if self.password:
            print(f"  密码: {self.password}")

        if block:
            try:
                while True:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """停止服务器"""
        global _active_servers
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        _active_servers -= 1
        self._server = None
        self._thread = None
        print("olrgu 服务已停止")

    @property
    def url(self):
        """本地访问地址"""
        return f"http://localhost:{self.port}"

    @property
    def lan_url(self):
        """局域网访问地址"""
        return f"http://{get_local_ip()}:{self.port}"


def share(path=".", port=8000, password=None, block=True):
    """快速启动文件分享服务（纯代码模式，无 GUI）

    :param path: 共享路径（文件或文件夹），默认当前目录
    :param port: 端口号，默认 8000
    :param password: 访问密码（可选，六位以内数字）
    :param block: True=阻塞运行，False=后台运行返回 Server 对象
    :return: block=False 时返回 Server 对象
    """
    s = Server(path, port, password)
    if block:
        s.start(block=True)
    else:
        s.start(block=False)
        return s


def main():
    """命令行入口点（GUI 模式）"""
    app = OlrguApp()
    app.run()


if __name__ == "__main__":
    main()
