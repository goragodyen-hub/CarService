@echo off
chcp 65001 > nul
echo ================================================================
echo กำลังสร้างไฟล์โปรแกรม .exe พร้อมไอคอน (Standalone ไม่ต้องลง Python)
echo ================================================================
python -m PyInstaller --noconfirm --onefile --name "CarService_RepairOrder" --icon "icon.ico" ^
  --add-data "index.html;." ^
  --add-data "style.css;." ^
  --add-data "app.js;." ^
  --add-data "icon.png;." ^
  --add-data "master_template.docx;." ^
  --add-data "fonts;fonts" ^
  server.py
echo ================================================================
echo เสร็จเรียบร้อย! ไฟล์ .exe อยู่ในโฟลเดอร์ dist\CarService_RepairOrder.exe
echo ================================================================
pause
