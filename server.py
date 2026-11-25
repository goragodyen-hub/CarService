# -*- coding: utf-8 -*-
"""
Local Server สำหรับระบบออกใบส่งซ่อมรถยนต์เช่า (Authorized Service Center)
รองรับฐานข้อมูล SQLite (car_service.db), ส่งออก Excel (.csv), สร้าง Word (.docx) และแบบ Standalone .exe
"""
import http.server
import socketserver
import json
import os
import sys
import time
import threading
import webbrowser
import base64
import traceback
from urllib.parse import urlparse, parse_qs
from generator import create_official_docx, save_base64_as_jpeg
import database

PORT = 8085


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
PHOTOS_DIR = os.path.join(DATA_DIR, "saved_photos")

# เริ่มต้นฐานข้อมูล SQLite (car_service.db)
database.init_db(DATA_DIR)


def persist_record(data):
    """บันทึกข้อมูลการส่งซ่อมลง SQLite (car_service.db) พร้อมเก็บรูปแนบใน saved_photos/"""
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    record_id = data.get("id") or str(int(time.time() * 1000))

    saved_photos = []
    for idx, item in enumerate(data.get("photos") or [], start=1):
        data_url = item.get("dataUrl", "") if isinstance(item, dict) else ""
        caption = item.get("caption", "") if isinstance(item, dict) else ""
        if data_url.startswith("data:image"):
            fname = f"{record_id}_{idx}.jpeg"
            fpath = os.path.join(PHOTOS_DIR, fname)
            save_base64_as_jpeg(data_url, fpath)
            saved_photos.append({"url": f"/saved_photos/{fname}", "caption": caption})
        elif item.get("url"):
            saved_photos.append({"url": item["url"], "caption": caption})

    record = {
        "id": record_id,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date_iso": data.get("date_iso", ""),
        "day": data.get("day", ""),
        "month": data.get("month", ""),
        "year": data.get("year", ""),
        "carType": data.get("carType", ""),
        "brand": data.get("brand", ""),
        "model": data.get("model", ""),
        "license": data.get("license", ""),
        "mileage": data.get("mileage", ""),
        "garage": data.get("garage", ""),
        "department": data.get("department", ""),
        "phone": data.get("phone", ""),
        "items": data.get("items", []),
        "hasReplacement": data.get("hasReplacement", False),
        "rep_brand": data.get("rep_brand", ""),
        "rep_model": data.get("rep_model", ""),
        "rep_license": data.get("rep_license", ""),
        "rep_mileage": data.get("rep_mileage", ""),
        "rep_garage": data.get("rep_garage", ""),
        "sender_name": data.get("sender_name", ""),
        "send_date_iso": data.get("send_date_iso", ""),
        "send_date": data.get("send_date", ""),
        "receive_date": data.get("receive_date", ""),
        "status": data.get("status", "กำลังซ่อม"),
        "note1": data.get("note1", ""),
        "note2": data.get("note2", ""),
        "includePage2": data.get("includePage2", True),
        "photos": saved_photos
    }

    database.upsert_record(record)
    return record


def resolve_photos_for_docx(data):
    resolved = []
    for item in data.get("photos") or []:
        if not isinstance(item, dict):
            continue
        if item.get("dataUrl") and item["dataUrl"].startswith("data:image"):
            resolved.append(item)
        elif item.get("url"):
            rel_path = item["url"].lstrip("/").replace("/", os.sep)
            full_path = os.path.join(DATA_DIR, rel_path)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                resolved.append({
                    "dataUrl": f"data:image/jpeg;base64,{b64}",
                    "caption": item.get("caption", "")
                })
    new_data = dict(data)
    new_data["photos"] = resolved
    return new_data


class CarServiceHandler(http.server.SimpleHTTPRequestHandler):
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

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/history':
            qs = parse_qs(parsed.query)
            lic = qs.get('license', [''])[0].strip() or None
            st = qs.get('status', [''])[0].strip() or None
            q = qs.get('q', [''])[0].strip() or None
            records = database.list_records(license_filter=lic, status_filter=st, search=q)
            body = json.dumps(records, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == '/api/export-csv':
            csv_bytes = database.export_csv_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="car_service_history.csv"')
            self.send_header('Content-Length', str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        if parsed.path.startswith('/saved_photos/'):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(PHOTOS_DIR, fname)
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
            remaining = len(database.list_records())
            body = json.dumps({"status": "ok", "remaining": remaining}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
            print(f"[OK] Deleted record from SQLite: {rec_id}", flush=True)
            return
        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if self.path == '/api/history':
                record = persist_record(data)
                body = json.dumps({"status": "ok", "record": record}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(body)
                print(f"[OK] Saved to SQLite: {record['id']} ({record['license']})", flush=True)
                return

            if self.path == '/api/history/status':
                rec_id = data.get("id", "")
                status = data.get("status", "กำลังซ่อม")
                receive_date = data.get("receive_date")
                database.update_status(rec_id, status, receive_date)
                body = json.dumps({"status": "ok"}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(body)
                print(f"[OK] Updated status {rec_id} -> {status}", flush=True)
                return

            if self.path == '/api/generate':
                persist_record(data)
                docx_data = resolve_photos_for_docx(data)
                output_file = os.path.join(DATA_DIR, "car_repair_order.docx")
                create_official_docx(docx_data, output_file)
                
                with open(output_file, 'rb') as f:
                    file_bytes = f.read()
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                self.send_header('Content-Disposition', 'attachment; filename="car_repair_order.docx"')
                self.send_header('Content-Length', str(len(file_bytes)))
                self.end_headers()
                self.wfile.write(file_bytes)
                print("[OK] Generated, saved to SQLite, and sent car_repair_order.docx", flush=True)
                return

            elif self.path == '/api/open-word':
                persist_record(data)
                docx_data = resolve_photos_for_docx(data)
                filename = "แบบฟอร์มนำรถเช่าเข้าซ่อมบำรุง_ล่าสุด.docx"
                output_file = os.path.join(DATA_DIR, filename)
                create_official_docx(docx_data, output_file)
                
                try:
                    os.startfile(output_file)
                    response = {"status": "ok", "message": "บันทึกฐานข้อมูลและเปิดใน Microsoft Word เรียบร้อยแล้ว", "path": output_file}
                    print(f"[OK] Saved to SQLite & opened in Word: {output_file}", flush=True)
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
                    print(f"[ERR] Failed to open in Word: {e}", flush=True)
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                return
                
            self.send_error(404, "Endpoint not found")
        except Exception as e:
            traceback.print_exc()
            self.send_error(500, str(e))


def open_browser_later(url):
    time.sleep(1.0)
    webbrowser.open(url)


def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    url = f"http://localhost:{PORT}"
    print("================================================================", flush=True)
    print("🚗 ระบบออกใบส่งซ่อมรถยนต์เช่า + ฐานข้อมูล SQLite (car_service.db)", flush=True)
    print(f"👉 กำลังเปิดใช้งานที่: {url}", flush=True)
    print(f"🗄️  ฐานข้อมูล: {database.DB_PATH}", flush=True)
    print("ℹ️  ห้ามปิดหน้าต่างนี้ขณะใช้งานโปรแกรม (ปิดได้เมื่อใช้งานเสร็จแล้ว)", flush=True)
    print("================================================================", flush=True)

    if getattr(sys, 'frozen', False):
        threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()

    with socketserver.TCPServer(("0.0.0.0", PORT), CarServiceHandler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    start_server()
