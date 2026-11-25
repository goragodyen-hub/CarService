// State
const state = {
    carFuel: 'none',
    repFuel: 'none',
    hasReplacement: false,
    paperSize: 'f4', // Default: 'f4' (8.5x13)
    photos: [] // Array of { dataUrl, caption }
};

function setPaperSize(size) {
    state.paperSize = size;
    let styleEl = document.getElementById('dynamic-page-size');
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'dynamic-page-size';
        document.head.appendChild(styleEl);
    }
    if (size === 'f4') {
        styleEl.textContent = '@media print { @page { size: 8.5in 13in; margin: 14mm 12mm 8mm 12mm; } }';
        document.querySelectorAll('.official-paper').forEach(el => el.style.minHeight = '1248px');
    } else {
        styleEl.textContent = '@media print { @page { size: 8.5in 14in; margin: 16mm 12mm 10mm 12mm; } }';
        document.querySelectorAll('.official-paper').forEach(el => el.style.minHeight = '1344px');
    }
}

// ข้อมูลคนขับประจำรถแต่ละทะเบียน (ส.น.ว. 1816 ผลัดกันตามวันที่ 1-15 และ 16-31)
const DRIVER_MAP = {
    'ส.น.ว. 1817': 'สุรินทร์ เพชรแท้',
    'ส.น.ว. 1818': 'แกม โสนาพูน',
    'ส.น.ว. 1819': 'จุมพล ดุษฎีพฤฒิพันธุ์',
    'ส.น.ว. 1820': 'อดิเรก จันทร์โฮ้วมณี'
};

function getDriverForLicense(license, isoDateStr) {
    if (license === 'ส.น.ว. 1816') {
        let day = new Date().getDate();
        if (isoDateStr && isoDateStr.includes('-')) {
            const parsedDay = parseInt(isoDateStr.split('-')[2], 10);
            if (!isNaN(parsedDay)) day = parsedDay;
        }
        return day <= 15 ? 'นันทกา เสาวรส' : 'จินฑาทิพทย์ สว่างเมฆ';
    }
    return DRIVER_MAP[license] || '';
}

function autoSelectDriver() {
    const lic = document.getElementById('inp-license')?.value || '';
    const sendDate = document.getElementById('inp-send-date')?.value || document.getElementById('inp-date')?.value || '';
    const driver = getDriverForLicense(lic, sendDate);
    if (driver) {
        const senderEl = document.getElementById('inp-sender-name');
        if (senderEl) senderEl.value = driver;
    }
}

function formatThaiDate(isoStr) {
    if (!isoStr) return '';
    const parts = isoStr.split('-');
    if (parts.length !== 3) return isoStr;
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    if (isNaN(year) || isNaN(month) || isNaN(day) || !thaiMonths[month]) return isoStr;
    return `${day} ${thaiMonths[month]} ${year + 543}`;
}

const thaiMonths = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
    "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
    "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
];

// Fuel gauge rendering function (matching official VML vector layout)
function createFuelSvg(level) {
    const cx = 36;
    const cy = 30;
    const r = 24;
    const strokeColor = "#d32f2f";

    const angleMap = {
        'E': 180,
        '1/4': 135,
        '1/2': 90,
        '3/4': 45,
        'F': 0
    };

    const hasNeedle = angleMap[level] !== undefined;
    let needleSvg = '';
    if (hasNeedle) {
        const rad = angleMap[level] * Math.PI / 180;
        const nx = cx + (r - 2) * Math.cos(rad);
        const ny = cy - (r - 2) * Math.sin(rad);
        needleSvg = `
        <line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="#000000" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="${cx}" cy="${cy}" r="2.5" fill="#000000"/>`;
    }

    function tick(deg) {
        const a = deg * Math.PI / 180;
        const tx = cx + r * Math.cos(a);
        const ty = cy - r * Math.sin(a);
        return `<line x1="${cx}" y1="${cy}" x2="${tx.toFixed(1)}" y2="${ty.toFixed(1)}" stroke="${strokeColor}" stroke-width="1.2"/>`;
    }

    return `
    <svg width="72" height="34" viewBox="0 0 78 36" style="overflow: visible; display: inline-block; vertical-align: middle;">
        <!-- Base Line -->
        <line x1="${cx - r}" y1="${cy}" x2="${cx + r}" y2="${cy}" stroke="${strokeColor}" stroke-width="1.4"/>
        <!-- Arc -->
        <path d="M ${cx - r},${cy} A ${r},${r} 0 0,1 ${cx + r},${cy}" fill="none" stroke="${strokeColor}" stroke-width="1.4"/>
        <!-- Ticks -->
        ${tick(135)}
        ${tick(90)}
        ${tick(45)}
        <!-- Fuel Needle -->
        ${needleSvg}
        <!-- F Letter -->
        <text x="${cx + r + 4}" y="${cy + 4}" fill="${strokeColor}" font-size="13" font-family="'Browallia New', 'Sarabun', sans-serif" font-weight="bold">F</text>
    </svg>
    `;
}

function setFuel(type, level) {
    if (type === 'car') {
        state.carFuel = level;
        document.querySelectorAll('[data-fuel]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-fuel') === level);
        });
    } else {
        state.repFuel = level;
        document.querySelectorAll('[data-rep-fuel]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-rep-fuel') === level);
        });
    }
    updatePreview();
}

function toggleReplacementCar() {
    const chk = document.getElementById('chk-has-replacement');
    const fields = document.getElementById('replacement-fields');
    state.hasReplacement = chk.checked;
    
    if (chk.checked) {
        fields.classList.remove('hidden');
    } else {
        fields.classList.add('hidden');
        document.getElementById('inp-rep-brand').value = '';
        document.getElementById('inp-rep-model').value = '';
        document.getElementById('inp-rep-license').value = '';
        document.getElementById('inp-rep-mileage').value = '';
    }
    updatePreview();
}

function addQuickItem(text) {
    for (let i = 1; i <= 5; i++) {
        const inp = document.getElementById(`inp-item-${i}`);
        if (!inp.value.trim()) {
            inp.value = text;
            updatePreview();
            return;
        }
    }
    document.getElementById('inp-item-5').value = text;
    updatePreview();
}

function loadPreset(name) {
    document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
    
    if (name === 'jitlada') {
        document.querySelector("button[onclick=\"loadPreset('jitlada')\"]")?.classList.add('active');
        document.querySelector('input[name="carType"][value="รถตู้"]').checked = true;
        document.getElementById('inp-brand').value = 'TOYOTA';
        document.getElementById('inp-model').value = 'COMMUTER';
        document.getElementById('inp-license').value = 'ส.น.ว. 1816';
        document.getElementById('inp-mileage').value = '19,838';
        document.getElementById('inp-garage').value = 'ศูนย์โตโยต้าวรจักรยนต์ สาขาวิสุทธิกษัตริย์';
        document.getElementById('inp-department').value = 'โรงเรียนจิตรลดา';
        document.getElementById('inp-phone').value = '092-225-4529';
        document.getElementById('inp-sender-name').value = getDriverForLicense('ส.น.ว. 1816', '2026-04-10');
        document.getElementById('inp-send-date').value = '2026-04-10';
        
        document.getElementById('inp-item-1').value = 'เปลี่ยนน้ำมันเครื่อง';
        document.getElementById('inp-item-2').value = 'เปลี่ยนกรองน้ำมันเครื่อง';
        document.getElementById('inp-item-3').value = 'สลับยาง จำนวน 4 เส้น';
        document.getElementById('inp-item-4').value = '';
        document.getElementById('inp-item-5').value = '';

        setFuel('car', 'none');
    } else if (name === 'empty') {
        document.querySelector("button[onclick=\"loadPreset('empty')\"]")?.classList.add('active');
        document.querySelectorAll('input[name="carType"]').forEach(r => r.checked = false);
        document.getElementById('inp-date').value = '';
        document.getElementById('inp-brand').value = '';
        document.getElementById('inp-model').value = '';
        document.getElementById('inp-license').value = '';
        document.getElementById('inp-mileage').value = '';
        document.getElementById('inp-garage').value = '';
        document.getElementById('inp-department').value = 'โรงเรียนจิตรลดา';
        document.getElementById('inp-phone').value = '092-225-4529';
        document.getElementById('inp-sender-name').value = '';
        document.getElementById('inp-send-date').value = '';
        document.getElementById('inp-note1').value = '';
        document.getElementById('inp-note2').value = '';
        
        for (let i = 1; i <= 5; i++) {
            document.getElementById(`inp-item-${i}`).value = '';
        }

        // Clear replacement car
        const repChk = document.getElementById('chk-has-replacement');
        if (repChk) {
            repChk.checked = false;
            toggleReplacementCar();
        }

        // Clear fuel needles to blank master gauges
        setFuel('car', 'none');
        setFuel('rep', 'none');

        // Clear all attached photos
        state.photos = [];
        renderPhotoList();
    }
    updatePreview();
}

function getFormData() {
    return {
        date_iso: document.getElementById('inp-date').value,
        day: document.getElementById('view-day').textContent,
        month: document.getElementById('view-month').textContent,
        year: document.getElementById('view-year').textContent,
        carType: document.querySelector('input[name="carType"]:checked')?.value || '',
        brand: document.getElementById('inp-brand').value,
        model: document.getElementById('inp-model').value,
        license: document.getElementById('inp-license').value,
        mileage: document.getElementById('inp-mileage').value,
        garage: document.getElementById('inp-garage').value,
        department: document.getElementById('inp-department').value,
        phone: document.getElementById('inp-phone').value,
        items: [
            document.getElementById('inp-item-1').value,
            document.getElementById('inp-item-2').value,
            document.getElementById('inp-item-3').value,
            document.getElementById('inp-item-4').value,
            document.getElementById('inp-item-5').value
        ],
        hasReplacement: state.hasReplacement,
        rep_brand: document.getElementById('inp-rep-brand')?.value || '',
        rep_model: document.getElementById('inp-rep-model')?.value || '',
        rep_license: document.getElementById('inp-rep-license')?.value || '',
        rep_mileage: document.getElementById('inp-rep-mileage')?.value || '',
        rep_garage: state.hasReplacement ? document.getElementById('inp-garage').value : '',
        sender_name: document.getElementById('inp-sender-name').value,
        send_date_iso: document.getElementById('inp-send-date').value,
        send_date: formatThaiDate(document.getElementById('inp-send-date').value),
        note1: document.getElementById('inp-note1').value,
        note2: document.getElementById('inp-note2').value,
        includePage2: document.getElementById('chk-include-page2')?.checked ?? true,
        paperSize: state.paperSize,
        photos: state.photos
    };
}

// ========================================================
// HISTORY STORAGE (Persistent via server history.json)
// ========================================================
let historyRecords = [];

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        if (res.ok) {
            historyRecords = await res.json();
            renderHistoryList();
        }
    } catch (e) {
        console.warn('Cannot load history from server:', e);
    }
}

async function saveCurrentRecord(showAlert = false) {
    const payload = getFormData();
    try {
        const res = await fetch(`${API_BASE}/api/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            await fetchHistory();
            if (showAlert) {
                alert('บันทึกข้อมูลเก็บไว้ในประวัติเรียบร้อยแล้วครับ! (ไฟล์ history.json)');
            }
        }
    } catch (e) {
        if (showAlert) alert('ไม่สามารถเชื่อมต่อ Local Server เพื่อบันทึกได้');
    }
}

async function printAndSave() {
    await saveCurrentRecord(false);
    window.print();
}

function loadHistoryRecord(recId) {
    const rec = historyRecords.find(r => r.id === recId);
    if (!rec) return;

    document.querySelectorAll('input[name="carType"]').forEach(r => {
        r.checked = (r.value === rec.carType);
    });
    document.getElementById('inp-date').value = rec.date_iso || '';
    document.getElementById('inp-brand').value = rec.brand || '';
    document.getElementById('inp-model').value = rec.model || '';
    document.getElementById('inp-license').value = rec.license || '';
    document.getElementById('inp-mileage').value = rec.mileage || '';
    document.getElementById('inp-garage').value = rec.garage || '';
    document.getElementById('inp-department').value = rec.department || '';
    document.getElementById('inp-phone').value = rec.phone || '';
    document.getElementById('inp-sender-name').value = rec.sender_name || '';
    document.getElementById('inp-send-date').value = rec.send_date_iso || '';
    document.getElementById('inp-note1').value = rec.note1 || '';
    document.getElementById('inp-note2').value = rec.note2 || '';

    const items = rec.items || [];
    for (let i = 1; i <= 5; i++) {
        document.getElementById(`inp-item-${i}`).value = items[i - 1] || '';
    }

    const repChk = document.getElementById('chk-has-replacement');
    if (repChk) {
        repChk.checked = !!rec.hasReplacement;
        toggleReplacementCar();
    }
    if (rec.hasReplacement) {
        document.getElementById('inp-rep-brand').value = rec.rep_brand || '';
        document.getElementById('inp-rep-model').value = rec.rep_model || '';
        document.getElementById('inp-rep-license').value = rec.rep_license || '';
        document.getElementById('inp-rep-mileage').value = rec.rep_mileage || '';
    }

    if (rec.paperSize) {
        const psRadio = document.querySelector(`input[name="paperSize"][value="${rec.paperSize}"]`);
        if (psRadio) psRadio.checked = true;
        setPaperSize(rec.paperSize);
    }

    // Restore photos (use saved URLs)
    state.photos = (rec.photos || []).map(p => ({
        url: p.url,
        dataUrl: p.url ? `${API_BASE}${p.url}` : (p.dataUrl || ''),
        caption: p.caption || ''
    }));
    renderPhotoList();
    updatePreview();
}

async function deleteHistoryRecord(recId) {
    if (!confirm('ต้องการลบประวัติรายการนี้หรือไม่?')) return;
    try {
        const res = await fetch(`${API_BASE}/api/history/${recId}`, { method: 'DELETE' });
        if (res.ok) {
            await fetchHistory();
        }
    } catch (e) {
        console.error(e);
    }
}

function renderHistoryList() {
    const listEl = document.getElementById('history-list');
    const badgeEl = document.getElementById('history-count-badge');
    if (badgeEl) badgeEl.textContent = `${historyRecords.length} รายการ`;
    if (!listEl) return;

    if (!historyRecords.length) {
        listEl.innerHTML = '<div class="history-empty">ยังไม่มีข้อมูลที่บันทึกไว้</div>';
        return;
    }

    listEl.innerHTML = historyRecords.map(rec => {
        const dateLabel = rec.day ? `${rec.day} ${rec.month} ${rec.year}` : (rec.saved_at || '');
        const itemCount = (rec.items || []).filter(x => x && x.trim()).length;
        const photoCount = (rec.photos || []).length;
        const stBadge = rec.status === 'รับรถแล้ว' ? '✅' : (rec.status === 'รอส่งซ่อม' ? '🟡' : '🔧');
        return `
            <div class="history-card">
                <div class="history-card-top">
                    <span class="history-card-title">${stBadge} ${rec.license || 'ไม่ระบุทะเบียน'}</span>
                    <span style="font-size:0.72rem; color:#64748b;">${dateLabel}</span>
                </div>
                <div class="history-card-meta">
                    ${rec.garage || '-'}<br>
                    ไมล์: ${rec.mileage || '-'} • ซ่อม ${itemCount} รายการ • รูปแนบ ${photoCount} รูป
                </div>
                <div class="history-card-actions">
                    <button type="button" class="btn-load-rec" onclick="loadHistoryRecord('${rec.id}')">📂 โหลดข้อมูลกลับมาใช้</button>
                    <button type="button" class="btn-clear-photo" onclick="deleteHistoryRecord('${rec.id}')" title="ลบ">✕</button>
                </div>
            </div>
        `;
    }).join('');

    // อัปเดตตารางใน Modal ด้วยถ้าเปิดอยู่
    const modal = document.getElementById('db-modal');
    if (modal && !modal.classList.contains('hidden')) {
        renderDbTable();
    }
}

// ========================================================
// DATABASE DASHBOARD MODAL (Filter, Status, Excel Export)
// ========================================================
async function openDbModal() {
    await fetchHistory();
    document.getElementById('db-modal').classList.remove('hidden');
    renderDbTable();
}

function closeDbModal() {
    document.getElementById('db-modal').classList.add('hidden');
}

function renderDbTable() {
    const licFilter = document.getElementById('db-filter-license')?.value || '';
    const stFilter = document.getElementById('db-filter-status')?.value || '';
    const q = (document.getElementById('db-search-input')?.value || '').trim().toLowerCase();

    // Update summary stats (from all records)
    const total = historyRecords.length;
    const done = historyRecords.filter(r => r.status === 'รับรถแล้ว').length;
    const active = total - done;
    const elTotal = document.getElementById('stat-total');
    const elActive = document.getElementById('stat-active');
    const elDone = document.getElementById('stat-done');
    if (elTotal) elTotal.textContent = total;
    if (elActive) elActive.textContent = active;
    if (elDone) elDone.textContent = done;

    // Filter
    const filtered = historyRecords.filter(r => {
        if (licFilter && r.license !== licFilter) return false;
        if (stFilter && (r.status || 'กำลังซ่อม') !== stFilter) return false;
        if (q) {
            const hay = [
                r.license, r.garage, r.sender_name, r.note1, r.note2,
                ...(r.items || [])
            ].join(' ').toLowerCase();
            if (!hay.includes(q)) return false;
        }
        return true;
    });

    const tbody = document.getElementById('db-table-body');
    if (!tbody) return;

    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 2rem; color:#64748b;">ไม่พบข้อมูลตามเงื่อนไขที่เลือก</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(r => {
        const dateStr = r.day ? `${r.day} ${r.month} ${r.year}` : (r.saved_at || '-');
        const itemsHtml = (r.items || []).filter(x => x && x.trim()).map((x, i) => `${i + 1}. ${x}`).join('<br>') || '-';
        const st = r.status || 'กำลังซ่อม';
        const stClass = st === 'รับรถแล้ว' ? 'st-done' : (st === 'รอส่งซ่อม' ? 'st-wait' : 'st-active');
        return `
            <tr>
                <td><strong>${dateStr}</strong><br><span style="font-size:0.72rem; color:#64748b;">ส่ง: ${r.send_date || '-'}</span></td>
                <td><strong style="color:#1e3a8a;">${r.license || '-'}</strong><br><span style="font-size:0.72rem; color:#64748b;">รูป ${(r.photos || []).length} รูป</span></td>
                <td>${r.mileage || '-'}</td>
                <td>${r.garage || '-'}</td>
                <td>${itemsHtml}</td>
                <td>${r.sender_name || '-'}</td>
                <td>
                    <select class="status-select ${stClass}" onchange="changeRecordStatus('${r.id}', this.value)">
                        <option value="รอส่งซ่อม" ${st === 'รอส่งซ่อม' ? 'selected' : ''}>🟡 รอส่งซ่อม</option>
                        <option value="กำลังซ่อม" ${st === 'กำลังซ่อม' ? 'selected' : ''}>🔧 กำลังซ่อม</option>
                        <option value="รับรถแล้ว" ${st === 'รับรถแล้ว' ? 'selected' : ''}>✅ รับรถแล้ว</option>
                    </select>
                </td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <button type="button" class="btn-load-rec" onclick="loadHistoryRecord('${r.id}'); closeDbModal();" title="โหลดลงฟอร์ม">📂</button>
                        <button type="button" class="btn-clear-photo" onclick="deleteHistoryRecord('${r.id}')" title="ลบ">✕</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

async function changeRecordStatus(recId, newStatus) {
    try {
        let receiveDate = undefined;
        if (newStatus === 'รับรถแล้ว') {
            const now = new Date();
            receiveDate = `${now.getDate()} ${thaiMonths[now.getMonth()]} ${now.getFullYear() + 543}`;
        }
        const res = await fetch(`${API_BASE}/api/history/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: recId, status: newStatus, receive_date: receiveDate })
        });
        if (res.ok) {
            await fetchHistory();
            renderDbTable();
        }
    } catch (e) {
        console.error(e);
    }
}

function exportExcelCsv() {
    window.location.href = `${API_BASE}/api/export-csv`;
}

// Multi-Photo upload handlers (Page 2+)
function handleMultiPhotoUpload(input) {
    const files = Array.from(input.files || []);
    if (!files.length) return;

    let loaded = 0;
    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = function(e) {
            state.photos.push({
                dataUrl: e.target.result,
                caption: ''
            });
            loaded++;
            if (loaded === files.length) {
                renderPhotoList();
                renderPhotoPages();
            }
        };
        reader.readAsDataURL(file);
    });
    input.value = '';
}

function updatePhotoCaption(index, val) {
    if (state.photos[index]) {
        state.photos[index].caption = val;
        renderPhotoPages();
    }
}

function removePhoto(index) {
    state.photos.splice(index, 1);
    renderPhotoList();
    renderPhotoPages();
}

function clearAllPhotos() {
    state.photos = [];
    renderPhotoList();
    renderPhotoPages();
}

function renderPhotoList() {
    const listEl = document.getElementById('photo-list');
    const badgeEl = document.getElementById('photo-count-badge');
    if (badgeEl) badgeEl.textContent = `แนบแล้ว ${state.photos.length} รูป`;
    if (!listEl) return;

    listEl.innerHTML = state.photos.map((p, idx) => `
        <div class="photo-list-item">
            <img src="${p.dataUrl}" class="photo-thumb" alt="รูปที่ ${idx + 1}">
            <div class="photo-item-meta">
                <span class="photo-num">รูปที่ ${idx + 1}</span>
                <input type="text" value="${(p.caption || '').replace(/"/g, '&quot;')}" placeholder="คำอธิบายใต้ภาพ (ถ้ามี)" oninput="updatePhotoCaption(${idx}, this.value)">
            </div>
            <button type="button" class="btn-clear-photo" onclick="removePhoto(${idx})" title="ลบรูป">✕</button>
        </div>
    `).join('');
}

function renderPhotoPages() {
    const container = document.getElementById('photo-pages-container');
    const chk = document.getElementById('chk-include-page2');
    const controls = document.getElementById('photo-upload-controls');
    if (!container) return;

    const show = chk ? chk.checked : true;
    if (controls) controls.classList.toggle('hidden', !show);
    if (!show) {
        container.innerHTML = '';
        return;
    }

    const brand = document.getElementById('inp-brand')?.value || '';
    const model = document.getElementById('inp-model')?.value || '';
    const license = document.getElementById('inp-license')?.value || '';

    const headerHtml = `
        <div class="page2-header">
            <div>รถยนต์เช่า ยี่ห้อ <span class="blue-val">${brand}</span> รุ่น <span class="blue-val">${model}</span></div>
            <div>ทะเบียน <span class="blue-val">${license}</span></div>
        </div>
    `;

    if (state.photos.length === 0) {
        container.innerHTML = `
            <div class="official-paper page-2">
                ${headerHtml}
                <div class="photo-placeholder no-print">
                    <span>📸 พื้นที่แนบรูปภาพหน้า 2 (รองรับ 1–6+ รูป)</span>
                    <small>คลิก "เลือกรูปภาพ" ที่แถบด้านซ้าย สามารถเลือกหลายรูปพร้อมกันได้เลย</small>
                </div>
            </div>
        `;
        return;
    }

    // Paginate: up to 6 photos per US Legal page
    const PER_PAGE = 6;
    let html = '';
    for (let start = 0; start < state.photos.length; start += PER_PAGE) {
        const chunk = state.photos.slice(start, start + PER_PAGE);
        const isGrid = state.photos.length >= 3;
        const wrapClass = isGrid ? 'page2-photos-grid' : 'page2-photos-single';
        const cards = chunk.map((p, i) => `
            <div class="photo-card">
                <img src="${p.dataUrl}" class="attached-img" alt="รูปที่ ${start + i + 1}">
                ${p.caption ? `<div class="photo-caption-text">${p.caption}</div>` : ''}
            </div>
        `).join('');

        html += `
            <div class="official-paper page-2">
                ${headerHtml}
                <div class="${wrapClass}">
                    ${cards}
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

const API_BASE = window.location.origin.startsWith('http') ? window.location.origin : 'http://localhost:8085';

// Open In Microsoft Word directly via API
async function openInWord() {
    const payload = getFormData();
    try {
        const res = await fetch(`${API_BASE}/api/open-word`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            fetchHistory();
            alert('บันทึกประวัติและเปิดเอกสารในโปรแกรม Microsoft Word เรียบร้อยแล้ว!');
        } else {
            fallbackDirectDownload(payload);
        }
    } catch (e) {
        fallbackDirectDownload(payload);
    }
}

// Download official DOCX
async function downloadDocx() {
    const payload = getFormData();
    try {
        const res = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `แบบฟอร์มนำรถเช่าเข้าซ่อมบำรุง_${payload.license || 'รถ'}.docx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            fetchHistory();
        } else {
            fallbackDirectDownload(payload);
        }
    } catch (e) {
        fallbackDirectDownload(payload);
    }
}

function fallbackDirectDownload(payload) {
    alert('คำแนะนำ: หากเปิดไฟล์ HTML โดยตรงโดยไม่ได้รัน Start_App.bat สามารถกดพิมพ์หน้าเว็บด้วยปุ่ม "พิมพ์ผ่านเบราว์เซอร์" หรือรัน Start_App.bat เพื่อเปิดและบันทึกไฟล์ Word อัตโนมัติได้ทันทีครับ!');
}

function updatePreview() {
    // 1. Date
    const dateInput = document.getElementById('inp-date').value;
    if (dateInput) {
        const d = new Date(dateInput);
        document.getElementById('view-day').textContent = d.getDate();
        document.getElementById('view-month').textContent = thaiMonths[d.getMonth()];
        document.getElementById('view-year').textContent = d.getFullYear() + 543;
    } else {
        document.getElementById('view-day').textContent = '';
        document.getElementById('view-month').textContent = '';
        document.getElementById('view-year').textContent = '';
    }

    // 2. Car Type Checkboxes
    const carType = document.querySelector('input[name="carType"]:checked')?.value || '';
    ['เก๋ง', 'ปิคอัพ', 'ตู้', 'บรรทุก'].forEach(t => {
        const el = document.getElementById(`chk-v-${t}`);
        if (el) el.classList.toggle('checked', carType === (t === 'เก๋ง' ? 'รถเก๋ง' : t === 'ปิคอัพ' ? 'รถปิคอัพ' : t === 'ตู้' ? 'รถตู้' : 'บรรทุก'));
    });

    // 3. Fuel Gauges
    document.getElementById('car-fuel-gauge').innerHTML = createFuelSvg(state.carFuel);
    document.getElementById('rep-fuel-gauge').innerHTML = createFuelSvg(state.repFuel);

    // 4. Car info
    const brandVal = document.getElementById('inp-brand').value;
    const modelVal = document.getElementById('inp-model').value;
    const licenseVal = document.getElementById('inp-license').value;

    document.getElementById('view-brand').textContent = brandVal;
    document.getElementById('view-model').textContent = modelVal;
    document.getElementById('view-license').textContent = licenseVal;
    document.getElementById('view-garage').textContent = document.getElementById('inp-garage').value;
    document.getElementById('view-mileage').textContent = document.getElementById('inp-mileage').value;
    document.getElementById('view-department').textContent = document.getElementById('inp-department').value;
    document.getElementById('view-phone').textContent = document.getElementById('inp-phone').value;

    // Footer / Page 2+ Car info
    renderPhotoPages();

    // 5. Repair items
    for (let i = 1; i <= 5; i++) {
        const val = document.getElementById(`inp-item-${i}`).value;
        document.getElementById(`view-item-${i}`).textContent = val;
    }

    // 6. Replacement car
    const repType = document.querySelector('input[name="repCarType"]:checked')?.value || '';
    ['เก๋ง', 'ปิคอัพ', 'ตู้', 'บรรทุก'].forEach(t => {
        const el = document.getElementById(`chk-rep-${t}`);
        if (el) {
            const isMatch = state.hasReplacement && repType === (t === 'เก๋ง' ? 'รถเก๋ง' : t === 'ปิคอัพ' ? 'รถปิคอัพ' : t === 'ตู้' ? 'รถตู้' : 'บรรทุก');
            el.classList.toggle('checked', isMatch);
        }
    });

    document.getElementById('view-rep-brand').textContent = document.getElementById('inp-rep-brand')?.value || '';
    document.getElementById('view-rep-model').textContent = document.getElementById('inp-rep-model')?.value || '';
    document.getElementById('view-rep-license').textContent = document.getElementById('inp-rep-license')?.value || '';
    document.getElementById('view-rep-garage').textContent = state.hasReplacement ? document.getElementById('inp-garage')?.value || '' : '';
    document.getElementById('view-rep-mileage').textContent = document.getElementById('inp-rep-mileage')?.value || '';

    // 7. Notes & Signatures
    document.getElementById('view-note1').textContent = document.getElementById('inp-note1').value;
    document.getElementById('view-note2').textContent = document.getElementById('inp-note2').value;
    document.getElementById('view-sender-name').textContent = document.getElementById('inp-sender-name').value;
    document.getElementById('view-send-date').textContent = formatThaiDate(document.getElementById('inp-send-date').value);
}

// ========================================================
// ADAPTIVE ZOOM & HIGH-RES SCREEN SCALING (Screen Only)
// ========================================================
let currentUiZoom = 1.0;
let currentPaperZoom = 1.0;

function applyUiZoom(val, persist = true) {
    currentUiZoom = Math.min(1.5, Math.max(0.8, Math.round(val * 100) / 100));
    document.documentElement.style.setProperty('--ui-zoom', currentUiZoom);
    const el = document.getElementById('ui-zoom-readout');
    if (el) el.textContent = `${Math.round(currentUiZoom * 100)}%`;
    if (persist) localStorage.setItem('carservice_ui_zoom', String(currentUiZoom));
}

function stepUiZoom(delta) {
    applyUiZoom(currentUiZoom + delta, true);
}

function applyPaperZoom(val, persist = true) {
    currentPaperZoom = Math.min(1.8, Math.max(0.55, Math.round(val * 100) / 100));
    document.documentElement.style.setProperty('--paper-zoom', currentPaperZoom);
    const el = document.getElementById('paper-zoom-readout');
    if (el) el.textContent = `${Math.round(currentPaperZoom * 100)}%`;
    if (persist) localStorage.setItem('carservice_paper_zoom', String(currentPaperZoom));
}

function stepPaperZoom(delta) {
    applyPaperZoom(currentPaperZoom + delta, true);
}

function fitPaperToScreen(persist = true) {
    const scroller = document.querySelector('.sheet-scroller');
    if (!scroller) return;
    const availW = scroller.clientWidth - 64;
    if (availW <= 0) return;
    const ideal = Math.min(1.5, Math.max(0.65, availW / 816));
    applyPaperZoom(ideal, persist);
}

function initAdaptiveZoom() {
    const savedUi = parseFloat(localStorage.getItem('carservice_ui_zoom'));
    const savedPaper = parseFloat(localStorage.getItem('carservice_paper_zoom'));

    if (!isNaN(savedUi)) {
        applyUiZoom(savedUi, false);
    } else {
        // Auto-scale for high-resolution monitors on first visit
        const w = window.innerWidth;
        if (w >= 2400) applyUiZoom(1.25, false);
        else if (w >= 1800) applyUiZoom(1.1, false);
        else applyUiZoom(1.0, false);
    }

    if (!isNaN(savedPaper)) {
        applyPaperZoom(savedPaper, false);
    } else {
        const w = window.innerWidth;
        if (w >= 2400) fitPaperToScreen(false);
        else if (w >= 1800) applyPaperZoom(1.1, false);
        else applyPaperZoom(1.0, false);
    }
}

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    document.getElementById('inp-date').value = `${yyyy}-${mm}-${dd}`;
    
    document.getElementById('view-day').textContent = now.getDate();
    document.getElementById('view-month').textContent = thaiMonths[now.getMonth()];
    document.getElementById('view-year').textContent = now.getFullYear() + 543;

    updatePreview();
    fetchHistory();
    initAdaptiveZoom();
});