# -*- coding: utf-8 -*-
"""
ระบบสร้างเอกสารใบส่งซ่อมรถยนต์เช่าจากไฟล์แม่แบบ master_template.docx (มาตรฐานหน่วยงาน 100%)
"""
import os
import sys
import io
import base64
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps


def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


TEMPLATE_FILE = os.path.join(get_resource_dir(), "master_template.docx")

def save_base64_as_jpeg(data_url, target_path, max_dim=1400):
    """แปลงรูปภาพ Base64 (JPG/PNG/WebP) เป็น JPEG พร้อมปรับทิศทาง EXIF และคืนค่า (width, height)"""
    if not data_url:
        return None
    if ',' in data_url:
        _, b64data = data_url.split(',', 1)
    else:
        b64data = data_url
    raw = base64.b64decode(b64data)
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    img.save(target_path, format='JPEG', quality=88)
    return img.size


def build_inline_drawing_elem(r_id, cx_emu, cy_emu, doc_pr_id, name):
    """สร้าง XML <w:drawing> สำหรับแทรกรูปภาพแบบ Inline ใน Word"""
    xml = f'''
    <w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
               xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
               xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
               xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
               xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{cx_emu}" cy="{cy_emu}"/>
        <wp:effectExtent l="0" t="0" r="0" b="0"/>
        <wp:docPr id="{doc_pr_id}" name="{name}"/>
        <wp:cNvGraphicFramePr>
          <a:graphicFrameLocks noChangeAspect="1"/>
        </wp:cNvGraphicFramePr>
        <a:graphic>
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic>
              <pic:nvPicPr>
                <pic:cNvPr id="{doc_pr_id}" name="{name}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{r_id}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="{cx_emu}" cy="{cy_emu}"/>
                </a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
    '''
    return ET.fromstring(xml)


def fit_emu(w_px, h_px, max_w_in, max_h_in):
    """คำนวณขนาด EMU โดยรักษาอัตราส่วนภาพ (Aspect Ratio)"""
    EMU_PER_INCH = 914400
    ratio = min((max_w_in * EMU_PER_INCH) / max(w_px, 1), (max_h_in * EMU_PER_INCH) / max(h_px, 1))
    return int(w_px * ratio), int(h_px * ratio)


def replace_page2_photos(root, temp_dir, photos):
    """แทนที่รูปภาพหน้า 2 ด้วยรูปที่ผู้ใช้อัปโหลด (รองรับ 1 ถึงหลายรูป เช่น 5-6+ รูป)"""
    W = f'{{{NS["w"]}}}'
    body = root.find('w:body', NS)

    # หา index ของย่อหน้า "ทะเบียน ..." (หลัง "รถยนต์เช่า")
    reg_idx = None
    found_header = False
    for idx, elem in enumerate(list(body)):
        if elem.tag == f'{W}p':
            txt = ''.join(elem.itertext())
            if 'รถยนต์เช่า' in txt:
                found_header = True
            elif found_header and 'ทะเบียน' in txt:
                reg_idx = idx
                break

    if reg_idx is None:
        return

    # ลบย่อหน้ารูปเดิมทั้งหมดที่อยู่หลัง "ทะเบียน ..." (เก็บ sectPr ไว้)
    sect_pr = body.find('w:sectPr', NS)
    to_remove = [elem for idx, elem in enumerate(list(body)) if idx > reg_idx and elem is not sect_pr]
    for elem in to_remove:
        body.remove(elem)

    # อัปเดต word/_rels/document.xml.rels
    rels_path = os.path.join(temp_dir, "word", "_rels", "document.xml.rels")
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()
    REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

    media_dir = os.path.join(temp_dir, "word", "media")
    os.makedirs(media_dir, exist_ok=True)

    photo_entries = []
    for i, item in enumerate(photos, start=1):
        data_url = item.get('dataUrl') if isinstance(item, dict) else item
        caption = item.get('caption', '') if isinstance(item, dict) else ''
        fname = f"attached_photo_{i}.jpeg"
        fpath = os.path.join(media_dir, fname)
        size = save_base64_as_jpeg(data_url, fpath)
        if not size:
            continue
        r_id = f"rIdPhoto{i}"
        rel = ET.SubElement(rels_root, f'{{{REL_NS}}}Relationship')
        rel.set('Id', r_id)
        rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
        rel.set('Target', f'media/{fname}')
        photo_entries.append((r_id, size[0], size[1], caption, i))

    rels_tree.write(rels_path, encoding='utf-8', xml_declaration=True)

    if not photo_entries:
        return

    # จัดวาง: 1-2 รูป -> 1 คอลัมน์ใหญ่, 3 รูปขึ้นไป -> ตาราง 2 คอลัมน์ไร้เส้นขอบ (6 รูปพอดี 1 หน้า F4/Legal)
    cols = 2 if len(photo_entries) >= 3 else 1
    max_w_in = 3.55 if cols == 2 else 5.6
    max_h_in = 3.05 if cols == 2 else 4.3

    tbl = ET.Element(f'{W}tbl')
    tblPr = ET.SubElement(tbl, f'{W}tblPr')
    tblW = ET.SubElement(tblPr, f'{W}tblW')
    tblW.set(f'{W}w', '10800')
    tblW.set(f'{W}type', 'dxa')
    jc = ET.SubElement(tblPr, f'{W}jc')
    jc.set(f'{W}val', 'center')
    tblBorders = ET.SubElement(tblPr, f'{W}tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        b = ET.SubElement(tblBorders, f'{W}{side}')
        b.set(f'{W}val', 'none')

    for row_start in range(0, len(photo_entries), cols):
        row_items = photo_entries[row_start:row_start + cols]
        tr = ET.SubElement(tbl, f'{W}tr')
        for c_idx in range(cols):
            tc = ET.SubElement(tr, f'{W}tc')
            tcPr = ET.SubElement(tc, f'{W}tcPr')
            tcW = ET.SubElement(tcPr, f'{W}tcW')
            tcW.set(f'{W}w', str(10800 // cols))
            tcW.set(f'{W}type', 'dxa')

            p = ET.SubElement(tc, f'{W}p')
            pPr = ET.SubElement(p, f'{W}pPr')
            pJc = ET.SubElement(pPr, f'{W}jc')
            pJc.set(f'{W}val', 'center')
            spacing = ET.SubElement(pPr, f'{W}spacing')
            spacing.set(f'{W}before', '80')
            spacing.set(f'{W}after', '80')

            if c_idx < len(row_items):
                r_id, w_px, h_px, caption, num = row_items[c_idx]
                cx, cy = fit_emu(w_px, h_px, max_w_in, max_h_in)
                r = ET.SubElement(p, f'{W}r')
                r.append(build_inline_drawing_elem(r_id, cx, cy, 500 + num, f"Photo {num}"))

                if caption:
                    p_cap = ET.SubElement(tc, f'{W}p')
                    set_para_text(p_cap, caption, font_size="28", align="center")

    # แทรกตารางรูปก่อน sectPr
    insert_pos = list(body).index(sect_pr) if sect_pr is not None else len(body)
    body.insert(insert_pos, tbl)

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'v': 'urn:schemas-microsoft-com:vml'
}

def set_cell_value(cell, text, color="000099", font_name="TH Sarabun New", font_size="32", bold=False, align="center"):
    """กำหนดข้อความลงในเซลล์ตารางของ Word ให้เป็นฟอนต์และสีตามต้นฉบับ"""
    p = cell.find('w:p', NS)
    if p is None:
        p = ET.SubElement(cell, f'{{{NS["w"]}}}p')
    
    pPr = p.find('w:pPr', NS)
    if pPr is None:
        pPr = ET.SubElement(p, f'{{{NS["w"]}}}pPr')
    jc = pPr.find('w:jc', NS)
    if jc is None:
        jc = ET.SubElement(pPr, f'{{{NS["w"]}}}jc')
    jc.set(f'{{{NS["w"]}}}val', align)
    
    for r in list(p.findall('w:r', NS)):
        p.remove(r)
        
    if text is not None and str(text) != "":
        r = ET.SubElement(p, f'{{{NS["w"]}}}r')
        rPr = ET.SubElement(r, f'{{{NS["w"]}}}rPr')
        
        rFonts = ET.SubElement(rPr, f'{{{NS["w"]}}}rFonts')
        rFonts.set(f'{{{NS["w"]}}}ascii', font_name)
        rFonts.set(f'{{{NS["w"]}}}hAnsi', font_name)
        rFonts.set(f'{{{NS["w"]}}}cs', font_name)
        
        sz = ET.SubElement(rPr, f'{{{NS["w"]}}}sz')
        sz.set(f'{{{NS["w"]}}}val', font_size)
        szCs = ET.SubElement(rPr, f'{{{NS["w"]}}}szCs')
        szCs.set(f'{{{NS["w"]}}}val', font_size)
        
        if bold:
            ET.SubElement(rPr, f'{{{NS["w"]}}}b')
            ET.SubElement(rPr, f'{{{NS["w"]}}}bCs')
            
        if color:
            c_elem = ET.SubElement(rPr, f'{{{NS["w"]}}}color')
            c_elem.set(f'{{{NS["w"]}}}val', color)
            
        t = ET.SubElement(r, f'{{{NS["w"]}}}t')
        t.text = str(text)

def set_para_text(p, text, font_name="TH Sarabun New", font_size="32", bold=False, align="center", color=None):
    """กำหนดข้อความในย่อหน้าแบบ Paragraph"""
    pPr = p.find('w:pPr', NS)
    if pPr is None:
        pPr = ET.SubElement(p, f'{{{NS["w"]}}}pPr')
    jc = pPr.find('w:jc', NS)
    if jc is None:
        jc = ET.SubElement(pPr, f'{{{NS["w"]}}}jc')
    jc.set(f'{{{NS["w"]}}}val', align)
    
    for r in list(p.findall('w:r', NS)):
        p.remove(r)
        
    if text is not None:
        r = ET.SubElement(p, f'{{{NS["w"]}}}r')
        rPr = ET.SubElement(r, f'{{{NS["w"]}}}rPr')
        
        rFonts = ET.SubElement(rPr, f'{{{NS["w"]}}}rFonts')
        rFonts.set(f'{{{NS["w"]}}}ascii', font_name)
        rFonts.set(f'{{{NS["w"]}}}hAnsi', font_name)
        rFonts.set(f'{{{NS["w"]}}}cs', font_name)
        
        sz = ET.SubElement(rPr, f'{{{NS["w"]}}}sz')
        sz.set(f'{{{NS["w"]}}}val', font_size)
        szCs = ET.SubElement(rPr, f'{{{NS["w"]}}}szCs')
        szCs.set(f'{{{NS["w"]}}}val', font_size)
        
        if bold:
            ET.SubElement(rPr, f'{{{NS["w"]}}}b')
            ET.SubElement(rPr, f'{{{NS["w"]}}}bCs')
            
        if color:
            c_elem = ET.SubElement(rPr, f'{{{NS["w"]}}}color')
            c_elem.set(f'{{{NS["w"]}}}val', color)
            
        t = ET.SubElement(r, f'{{{NS["w"]}}}t')
        t.text = str(text)

def create_official_docx(data, output_path):
    """
    สร้างไฟล์ Word จาก master_template.docx ตามโครงสร้างที่กำหนด 100%
    """
    temp_dir = tempfile.mkdtemp(prefix="carservice_docx_")
    try:
        with zipfile.ZipFile(TEMPLATE_FILE, 'r') as z:
            z.extractall(temp_dir)
        
        doc_xml_path = os.path.join(temp_dir, "word", "document.xml")
        tree = ET.parse(doc_xml_path)
        root = tree.getroot()
        tables = root.findall('.//w:tbl', NS)
        
        # 1. วันที่ (Table 0, R1)
        t0_r1 = tables[0].findall('.//w:tr', NS)[1].findall('.//w:tc', NS)
        set_cell_value(t0_r1[2], data.get('day', ''), align="center")
        set_cell_value(t0_r1[4], data.get('month', ''), align="center")
        set_cell_value(t0_r1[6], data.get('year', ''), align="center")
        
        # 2. ข้อมูลรถส่งซ่อม (Table 2)
        t2_rows = tables[2].findall('.//w:tr', NS)
        brand = data.get('brand', 'TOYOTA')
        model = data.get('model', 'COMMUTER')
        license = data.get('license', '')
        
        set_cell_value(t2_rows[0].findall('.//w:tc', NS)[1], brand, align="center")
        set_cell_value(t2_rows[0].findall('.//w:tc', NS)[3], model, align="center")
        set_cell_value(t2_rows[0].findall('.//w:tc', NS)[5], license, align="center")
        
        set_cell_value(t2_rows[1].findall('.//w:tc', NS)[1], data.get('garage', ''), align="left")
        set_cell_value(t2_rows[1].findall('.//w:tc', NS)[3], data.get('mileage', ''), align="center")
        
        set_cell_value(t2_rows[2].findall('.//w:tc', NS)[1], data.get('department', 'โรงเรียนจิตรลดา'), align="center")
        set_cell_value(t2_rows[2].findall('.//w:tc', NS)[3], data.get('phone', '092-225-4529'), align="center")
        
        # 3. รายการแจ้งซ่อม (Table 3, R2-R6)
        t3_rows = tables[3].findall('.//w:tr', NS)
        items = data.get('items', [])
        for i in range(5):
            val = items[i] if i < len(items) else ''
            cell = t3_rows[2 + i].findall('.//w:tc', NS)[1]
            set_cell_value(cell, val, align="left")
            
        # 4. ข้อมูลรถทดแทน (Table 5)
        t5_rows = tables[5].findall('.//w:tr', NS)
        set_cell_value(t5_rows[0].findall('.//w:tc', NS)[1], data.get('rep_brand', ''), align="center")
        set_cell_value(t5_rows[0].findall('.//w:tc', NS)[3], data.get('rep_model', ''), align="center")
        set_cell_value(t5_rows[0].findall('.//w:tc', NS)[5], data.get('rep_license', ''), align="center")
        
        set_cell_value(t5_rows[1].findall('.//w:tc', NS)[1], data.get('rep_garage', ''), align="left")
        set_cell_value(t5_rows[1].findall('.//w:tc', NS)[4], data.get('rep_mileage', ''), align="center")
        
        # หมายเหตุ 1 (R3 C1)
        set_cell_value(t5_rows[3].findall('.//w:tc', NS)[1], data.get('note1', ''), align="left")
        
        # ส่วนลงนาม
        set_cell_value(t5_rows[5].findall('.//w:tc', NS)[1], data.get('sender_name', ''), align="center")
        set_cell_value(t5_rows[5].findall('.//w:tc', NS)[3], data.get('send_date', ''), align="center")
        
        # หมายเหตุ 2 (R8 C1)
        set_cell_value(t5_rows[8].findall('.//w:tc', NS)[1], data.get('note2', ''), align="left")
        
        # 5. ท้ายเอกสาร (Footer Section: รถยนต์เช่า ยี่ห้อ... ทะเบียน...)
        all_paras = root.findall('.//w:p', NS)
        for p in all_paras:
            txt = ''.join(p.itertext())
            if 'รถยนต์เช่า' in txt:
                set_para_text(p, f"รถยนต์เช่า ยี่ห้อ {brand} รุ่น {model}", align="center")
            elif 'ทะเบียน' in txt and ('รถยนต์เช่า' not in txt) and ('ยี่ห้อรถยนต์' not in txt) and ('รุ่นรถ' not in txt):
                p_text = f"ทะเบียน {license}" if license else "ทะเบียน "
                set_para_text(p, p_text, align="center")
        
        # 6. แทนที่รูปภาพแนบหน้า 2+ (รองรับหลายรูป เช่น 5-6+ รูป)
        photos = data.get('photos') or []
        if photos:
            replace_page2_photos(root, temp_dir, photos)

        # 7. ปรับขนาดกระดาษ (ค่าเริ่มต้น F4 8.5x13" หรือ Legal 8.5x14") และขอบบนปลอดภัยกันหัวขาด
        paper_size = data.get('paperSize', 'f4')
        sect_pr = root.find('.//w:sectPr', NS)
        if sect_pr is not None:
            pg_sz = sect_pr.find('w:pgSz', NS)
            if pg_sz is not None:
                pg_sz.set(f'{{{NS["w"]}}}w', '12240')  # 8.5 in
                if paper_size == 'f4':
                    pg_sz.set(f'{{{NS["w"]}}}h', '18720')  # 13 in
                    if f'{{{NS["w"]}}}code' in pg_sz.attrib:
                        del pg_sz.attrib[f'{{{NS["w"]}}}code']
                else:
                    pg_sz.set(f'{{{NS["w"]}}}h', '20160')  # 14 in
            pg_mar = sect_pr.find('w:pgMar', NS)
            if pg_mar is not None:
                pg_mar.set(f'{{{NS["w"]}}}top', '680')

        tree.write(doc_xml_path, encoding='utf-8', xml_declaration=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
            for foldername, subfolders, filenames in os.walk(temp_dir):
                for filename in filenames:
                    filepath = os.path.join(foldername, filename)
                    arcname = os.path.relpath(filepath, temp_dir)
                    z_out.write(filepath, arcname)
        return output_path
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_data = {
        'day': '21',
        'month': 'พฤศจิกายน',
        'year': '2569',
        'brand': 'TOYOTA',
        'model': 'COMMUTER',
        'license': 'ส.น.ว. 1816',
        'garage': 'ศูนย์โตโยต้าวรจักรยนต์ สาขาวิสุทธิกษัตริย์',
        'mileage': '19,838',
        'department': 'โรงเรียนจิตรลดา',
        'phone': '092-225-4529',
        'items': ['เปลี่ยนน้ำมันเครื่อง', 'เปลี่ยนกรองน้ำมันเครื่อง', 'สลับยาง จำนวน 4 เส้น'],
        'sender_name': 'นายนันทกา  เสาวรส',
        'send_date': '10 เมษายน 2569'
    }
    out = create_official_docx(test_data, "test_updated_form.docx")
    print(f"Generated: {out}")
