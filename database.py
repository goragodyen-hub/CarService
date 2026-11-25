# -*- coding: utf-8 -*-
"""
ฐานข้อมูล SQLite (car_service.db) สำหรับเก็บประวัติการส่งซ่อมรถยนต์เช่า
พกพาไปใช้ได้ทุกเครื่องในรูปแบบไฟล์เดียว (ไม่ต้องติดตั้ง Database Server)
"""
import csv
import io
import json
import os
import sqlite3

DB_PATH = None


def init_db(data_dir):
    global DB_PATH
    os.makedirs(data_dir, exist_ok=True)
    DB_PATH = os.path.join(data_dir, "car_service.db")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repair_records (
                id TEXT PRIMARY KEY,
                saved_at TEXT,
                date_iso TEXT,
                day TEXT,
                month TEXT,
                year TEXT,
                car_type TEXT,
                brand TEXT,
                model TEXT,
                license TEXT,
                mileage TEXT,
                garage TEXT,
                department TEXT,
                phone TEXT,
                items_json TEXT,
                has_replacement INTEGER DEFAULT 0,
                rep_brand TEXT,
                rep_model TEXT,
                rep_license TEXT,
                rep_mileage TEXT,
                rep_garage TEXT,
                sender_name TEXT,
                send_date_iso TEXT,
                send_date TEXT,
                receive_date TEXT DEFAULT '',
                status TEXT DEFAULT 'กำลังซ่อม',
                note1 TEXT,
                note2 TEXT,
                include_page2 INTEGER DEFAULT 1,
                photos_json TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()

    # ย้ายข้อมูลเก่าจาก history.json (ถ้ามีและฐานข้อมูลยังว่างอยู่)
    legacy_json = os.path.join(data_dir, "history.json")
    if os.path.exists(legacy_json) and len(list_records()) == 0:
        try:
            with open(legacy_json, "r", encoding="utf-8") as f:
                old_records = json.load(f)
            for rec in old_records:
                if isinstance(rec, dict) and rec.get("id"):
                    upsert_record(rec)
        except Exception:
            pass


def _row_to_dict(row):
    return {
        "id": row[0],
        "saved_at": row[1] or "",
        "date_iso": row[2] or "",
        "day": row[3] or "",
        "month": row[4] or "",
        "year": row[5] or "",
        "carType": row[6] or "",
        "brand": row[7] or "",
        "model": row[8] or "",
        "license": row[9] or "",
        "mileage": row[10] or "",
        "garage": row[11] or "",
        "department": row[12] or "",
        "phone": row[13] or "",
        "items": json.loads(row[14]) if row[14] else [],
        "hasReplacement": bool(row[15]),
        "rep_brand": row[16] or "",
        "rep_model": row[17] or "",
        "rep_license": row[18] or "",
        "rep_mileage": row[19] or "",
        "rep_garage": row[20] or "",
        "sender_name": row[21] or "",
        "send_date_iso": row[22] or "",
        "send_date": row[23] or "",
        "receive_date": row[24] or "",
        "status": row[25] or "กำลังซ่อม",
        "note1": row[26] or "",
        "note2": row[27] or "",
        "includePage2": bool(row[28]),
        "photos": json.loads(row[29]) if row[29] else []
    }


def upsert_record(record):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO repair_records (
                id, saved_at, date_iso, day, month, year,
                car_type, brand, model, license, mileage,
                garage, department, phone, items_json,
                has_replacement, rep_brand, rep_model, rep_license, rep_mileage, rep_garage,
                sender_name, send_date_iso, send_date, receive_date, status,
                note1, note2, include_page2, photos_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("id", ""),
            record.get("saved_at", ""),
            record.get("date_iso", ""),
            record.get("day", ""),
            record.get("month", ""),
            record.get("year", ""),
            record.get("carType", ""),
            record.get("brand", ""),
            record.get("model", ""),
            record.get("license", ""),
            record.get("mileage", ""),
            record.get("garage", ""),
            record.get("department", ""),
            record.get("phone", ""),
            json.dumps(record.get("items") or [], ensure_ascii=False),
            1 if record.get("hasReplacement") else 0,
            record.get("rep_brand", ""),
            record.get("rep_model", ""),
            record.get("rep_license", ""),
            record.get("rep_mileage", ""),
            record.get("rep_garage", ""),
            record.get("sender_name", ""),
            record.get("send_date_iso", ""),
            record.get("send_date", ""),
            record.get("receive_date", ""),
            record.get("status", "กำลังซ่อม"),
            record.get("note1", ""),
            record.get("note2", ""),
            1 if record.get("includePage2", True) else 0,
            json.dumps(record.get("photos") or [], ensure_ascii=False)
        ))
        conn.commit()
    finally:
        conn.close()


def list_records(license_filter=None, status_filter=None, search=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        sql = "SELECT * FROM repair_records WHERE 1=1"
        params = []
        if license_filter:
            sql += " AND license = ?"
            params.append(license_filter)
        if status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        if search:
            like = f"%{search}%"
            sql += " AND (license LIKE ? OR garage LIKE ? OR items_json LIKE ? OR sender_name LIKE ? OR note1 LIKE ?)"
            params.extend([like, like, like, like, like])
        sql += " ORDER BY saved_at DESC, id DESC"
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def update_status(record_id, status, receive_date=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        if receive_date is not None:
            conn.execute(
                "UPDATE repair_records SET status = ?, receive_date = ? WHERE id = ?",
                (status, receive_date, record_id)
            )
        else:
            conn.execute(
                "UPDATE repair_records SET status = ? WHERE id = ?",
                (status, record_id)
            )
        conn.commit()
    finally:
        conn.close()


def delete_record(record_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM repair_records WHERE id = ?", (record_id,))
        conn.commit()
    finally:
        conn.close()


def export_csv_bytes():
    """ส่งออกประวัติทั้งหมดเป็น CSV (UTF-8 with BOM) เปิดใน Microsoft Excel ภาษาไทยตรง 100%"""
    records = list_records()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ลำดับ", "วันที่แจ้งซ่อม", "ทะเบียนรถ", "ยี่ห้อ/รุ่น", "เลขไมล์",
        "ศูนย์บริการ/อู่", "รายการแจ้งซ่อม", "จนท.นำรถเข้าซ่อม",
        "วันที่ส่งรถเข้าซ่อม", "วันที่รับรถคืน", "สถานะ", "หมายเหตุ", "เวลาที่บันทึก"
    ])
    for idx, r in enumerate(records, start=1):
        date_str = f"{r['day']} {r['month']} {r['year']}".strip()
        items_str = " | ".join([x.strip() for x in (r.get("items") or []) if x and x.strip()])
        notes = " / ".join([x.strip() for x in [r.get("note1", ""), r.get("note2", "")] if x and x.strip()])
        writer.writerow([
            idx, date_str, r.get("license", ""), f"{r.get('brand', '')} {r.get('model', '')}".strip(),
            r.get("mileage", ""), r.get("garage", ""), items_str, r.get("sender_name", ""),
            r.get("send_date", ""), r.get("receive_date", ""), r.get("status", ""), notes, r.get("saved_at", "")
        ])
    return ("\ufeff" + out.getvalue()).encode("utf-8")

