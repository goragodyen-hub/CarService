@echo off
chcp 65001 > nul
echo ================================================================
echo กำลังสร้างไฟล์โปรแกรม Dashboard .exe สำหรับแผนกยานพาหนะ
echo ================================================================
python -m PyInstaller --noconfirm --onefile --name "CarService_Dashboard" --icon "icon.ico" ^
  --add-data "dashboard.html;." ^
  --add-data "icon.png;." ^
  --add-data "fonts;fonts" ^
  dashboard_app.py
echo ================================================================
echo เสร็จเรียบร้อย! ไฟล์ .exe อยู่ในโฟลเดอร์ dist\CarService_Dashboard.exe
echo ================================================================
pause

