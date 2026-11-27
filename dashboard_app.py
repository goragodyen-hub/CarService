# -*- coding: utf-8 -*-
"""
CarService Dashboard — โปรแกรม Dashboard แยกสำหรับแผนกยานพาหนะ (โรงเรียนจิตรลดา)
อ่านฐานข้อมูล SQLite (car_service.db) แบบออฟไลน์ 100% พร้อมระบบ Login แยกสิทธิ์ Admin / ดูรายงาน
"""
import http.server
import socketserver
import json
import os
import sys
import time
import threading
import webbrowser
import traceback
from urllib.parse import urlparse
import database

PORT = 8086


def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


RESOURCE_DIR = get_resource_dir()
DATA_DIR = get_data_dir()
ACTIVE_PHOTOS_DIR = os.path.join(DATA_DIR, "saved_photos")

database.init_db(DATA_DIR)


def pick_db_file_dialog():
    """เปิดหน้าต่างเลือกไฟล์ car_service.db ของ Windows"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ฐานข้อมูล car_service.db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        root.destroy()
        return path
    except Exception as e:
        print(f"[ERR] File dialog error: {e}", flush=True)
        return ""


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=RESOURCE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ('/', '/index.html'):
            self.path = '/dashboard.html'
            return super().do_GET()

        if parsed.path == '/api/info':
            self._send_json({
                "db_path": database.DB_PATH,
                "photos_dir": ACTIVE_PHOTOS_DIR
            })
            return

        if parsed.path == '/api/history':
            self._send_json(database.list_records())
            return

        if parsed.path == '/api/export-csv':
            csv_bytes = database.export_csv_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="car_service_report.csv"')
            self.send_header('Content-Length', str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        if parsed.path.startswith('/saved_photos/'):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(ACTIVE_PHOTOS_DIR, fname)
            if os.path.isfile(fpath):
                with open(fpath, 'rb') as f:
                    img_bytes = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(img_bytes)))
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            self.send_error(404, "Photo not found")
            return

        super().do_GET()

    def do_DELETE(self):
        if self.path.startswith('/api/history/'):
            rec_id = self.path.split('/api/history/', 1)[1].strip()
            database.delete_record(rec_id)
            self._send_json({"status": "ok"})
            return
        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        global ACTIVE_PHOTOS_DIR
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length) if content_length else b'{}'
            data = json.loads(raw.decode('utf-8'))

            if self.path == '/api/login':
                user = database.verify_user(data.get('username', ''), data.get('password', ''))
                if user:
                    self._send_json({"status": "ok", "user": user})
                else:
                    self._send_json({"status": "error", "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, 401)
                return

            if self.path == '/api/change-password':
                ok = database.change_password(
                    data.get('username', 'admin'),
                    data.get('old_password', ''),
                    data.get('new_password', '')
                )
                if ok:
                    self._send_json({"status": "ok", "message": "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว"})
                else:
                    self._send_json({"status": "error", "message": "รหัสผ่านเดิมไม่ถูกต้อง"}, 400)
                return

            if self.path == '/api/pick-db':
                chosen = pick_db_file_dialog()
                if chosen and os.path.isfile(chosen):
                    database.init_db(os.path.dirname(chosen), custom_db_path=chosen)
                    ACTIVE_PHOTOS_DIR = os.path.join(os.path.dirname(chosen), "saved_photos")
                    self._send_json({"status": "ok", "db_path": database.DB_PATH})
                else:
                    self._send_json({"status": "cancelled"})
                return

            if self.path == '/api/history/status':
                database.update_status(data.get('id', ''), data.get('status', 'กำลังซ่อม'), data.get('receive_date'))
                self._send_json({"status": "ok"})
                return

            self.send_error(404, "Endpoint not found")
        except Exception as e:
            traceback.print_exc()
            self.send_error(500, str(e))


def open_browser_later(url):
    time.sleep(1.0)
    webbrowser.open(url)


def start_dashboard():
    socketserver.TCPServer.allow_reuse_address = True
    url = f"http://localhost:{PORT}"
    print("================================================================", flush=True)
    print("📊 CarService Dashboard — แผนกยานพาหนะ (โรงเรียนจิตรลดา)", flush=True)
    print(f"👉 กำลังเปิดใช้งานที่: {url}", flush=True)
    print(f"🗄️  ฐานข้อมูล: {database.DB_PATH}", flush=True)
    print("🔑 บัญชีเริ่มต้น: admin / รหัสผ่าน: 1234", flush=True)
    print("ℹ️  ห้ามปิดหน้าต่างนี้ขณะใช้งานโปรแกรม", flush=True)
    print("================================================================", flush=True)

    if getattr(sys, 'frozen', False):
        threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()

    with socketserver.TCPServer(("0.0.0.0", PORT), DashboardHandler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    start_dashboard()

