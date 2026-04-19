// BIẾN TOÀN CỤC CHỨA STATE CỦA APP
let currentRubricData = [];
let currentAstData = {};
let currentReportData = {};
let activeElement = null;

// Biến currentSubject đã được khai báo ở file HTML (Ví dụ: 'word' hoặc 'excel')
console.log("Đang chạy ở chế độ môn học:", currentSubject);

// ==========================================
// 1. QUẢN LÝ DANH SÁCH FILE VÀ LOAD DATA (AJAX)
// ==========================================

// Quét thư mục backend theo môn học
async function loadFileList() {
    try {
        const response = await fetch(`/api/${currentSubject}/list_files`);
        const data = await response.json();

        if(data.error) {
            alert("Lỗi: " + data.error);
            return;
        }

        const selectRubric = document.getElementById('select-rubric');
        const selectStudent = document.getElementById('select-student');

        // Reset options
        selectRubric.innerHTML = '<option value="">-- Chọn file Rubric --</option>';
        selectStudent.innerHTML = '<option value="">-- Chọn file Bài làm --</option>';

        data.rubrics.forEach(f => selectRubric.add(new Option(f, f)));
        data.students.forEach(f => selectStudent.add(new Option(f, f)));
    } catch (error) {
        console.error("Lỗi khi load danh sách file:", error);
    }
}

// Nạp dữ liệu từ file được chọn
async function loadWorkspaceData() {
    const rubricName = document.getElementById('select-rubric').value;
    const studentName = document.getElementById('select-student').value;

    try {
        const response = await fetch(`/api/${currentSubject}/load_data?rubric=${rubricName}&student=${studentName}`);
        const data = await response.json();

        currentRubricData = data.rubric;
        currentAstData = data.ast;
        currentReportData = data.report;

        // Cập nhật lại toàn bộ UI
        renderReport();
        renderRubricEditor();

        const previewContainer = document.getElementById('document-preview');
        previewContainer.innerHTML = ''; // Clear bản vẽ cũ

        if (Object.keys(currentAstData).length > 0) {
            // LOGIC CHIA NHÁNH RENDER THEO MÔN HỌC
            if (currentSubject === 'word') {
                renderWordNode(currentAstData, previewContainer);
            } else if (currentSubject === 'excel') {
                renderExcelNode(currentAstData, previewContainer);
            } else if (currentSubject === 'powerpoint') {
                renderPptxNode(currentAstData, previewContainer);
            } else {
                previewContainer.innerHTML = `<div style="color: #666; text-align: center;">Chưa hỗ trợ Preview cho môn ${currentSubject}</div>`;
            }
        } else {
            previewContainer.innerHTML = '<div style="text-align:center; color:#999;">Không có dữ liệu bài làm.</div>';
        }
        document.getElementById('json-inspector').innerHTML = '<span style="color: #6b7280; font-style: italic;">Rê chuột & click vào Dữ liệu để xem cấu trúc JSON...</span>';

    } catch (error) {
        console.error("Lỗi nạp dữ liệu workspace:", error);
    }
}

// Lưu Rubric đang mở
function saveCurrentRubric() {
    const rubricName = document.getElementById('select-rubric').value;
    if (!rubricName) {
        alert("Vui lòng chọn một file Rubric trước khi lưu!");
        return;
    }

    // Lấy dữ liệu từ textarea nếu là giao diện RAW JSON
    const rawEditor = document.getElementById('raw-rubric-editor');
    let dataToSave = currentRubricData;

    if (rawEditor) {
        try {
            dataToSave = JSON.parse(rawEditor.value);
        } catch(e) {
            alert("Lỗi cú pháp JSON. Vui lòng kiểm tra lại trước khi lưu!");
            return;
        }
    }

    fetch(`/api/${currentSubject}/save_rubric`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: rubricName,
            data: dataToSave
        })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'success') {
            alert(`✅ Đã lưu thành công vào file: ${rubricName}`);
            currentRubricData = dataToSave; // Cập nhật state
        }
        else alert('❌ Lỗi: ' + data.message);
    })
    .catch(err => console.error("Lỗi:", err));
}

// ==========================================
// 2. UI NAVIGATION
// ==========================================
function switchTab(tabName) {
    document.getElementById('tab-report').classList.remove('active');
    document.getElementById('tab-editor').classList.remove('active');
    document.getElementById('content-report').classList.remove('active');
    document.getElementById('content-editor').classList.remove('active');

    document.getElementById('tab-' + tabName).classList.add('active');
    document.getElementById('content-' + tabName).classList.add('active');
}

// ==========================================
// 3. RENDER BÁO CÁO KẾT QUẢ CHẤM ĐIỂM
// ==========================================
function renderReport() {
    const scoreBoard = document.getElementById('final-score');
    const container = document.getElementById('report-container');
    const studentName = document.getElementById('select-student').value;

    if (!studentName) {
        scoreBoard.className = 'score-board';
        scoreBoard.innerHTML = "Vui lòng chọn bài làm sinh viên để xem điểm";
        container.innerHTML = "";
        return;
    }

    // Tương thích cả chuẩn mới (PPTX dùng "details") và chuẩn cũ (Word/Excel dùng "report")
    const reportList = currentReportData.details || currentReportData.report;

    if (!currentReportData || !reportList || reportList.length === 0) {
        scoreBoard.className = 'score-board danger';
        scoreBoard.innerHTML = "Lỗi: File chấm điểm rỗng hoặc không đúng định dạng!";
        container.innerHTML = `<p style="text-align:center; color:#666;">Hãy đảm bảo bạn đã chạy file Python để sinh ra kết quả cho <b>${studentName}</b>.</p>`;
        return;
    }

    let sbClass = 'score-board success';
    if (currentReportData.final_score < 5.0) sbClass = 'score-board danger';
    else if (currentReportData.final_score < 8.0) sbClass = 'score-board warning';

    // Lấy điểm tổng tối đa (fallback mặc định 10.0 nếu thiếu)
    const maxTotal = currentReportData.max_possible_score || 10.0;
    scoreBoard.className = sbClass;
    scoreBoard.innerHTML = `ĐIỂM: ${currentReportData.final_score} / ${maxTotal}`;

    let html = '';
    reportList.forEach(crit => {
        // Map linh hoạt các trường dữ liệu giữa chuẩn Cũ & Mới
        const status = crit.status || 'FAILED';
        const criteriaName = crit.description || crit.criteria || crit.criterion_id;
        const score = crit.awarded_points !== undefined ? crit.awarded_points : crit.score;
        const maxScore = crit.max_points || crit.max_score;
        const message = crit.message || "";

        let cardBorder = 'border-left: 5px solid #ef4444;'; // Đỏ (FAILED)
        let badgeColor = '#fee2e2'; let textColor = '#991b1b'; let icon = '❌ FAIL';

        if (status === 'PASSED' || status === 'SUCCESS') {
            cardBorder = 'border-left: 5px solid #10b981;'; // Xanh
            badgeColor = '#d1fae5'; textColor = '#065f46'; icon = '✅ PASS';
        } else if (status === 'PARTIAL') {
            cardBorder = 'border-left: 5px solid #f59e0b;'; // Cam
            badgeColor = '#fef3c7'; textColor = '#92400e'; icon = '⚠️ PARTIAL';
        }

        html += `<div style="background: #f9fafb; padding: 15px; margin-bottom: 15px; border-radius: 6px; ${cardBorder}">
                    <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:16px; margin-bottom:10px;">
                        <span>${criteriaName}</span>
                        <span style="background:${badgeColor}; color:${textColor}; padding: 2px 8px; border-radius: 12px; font-size: 14px;">
                            ${icon} : ${score} / ${maxScore}
                        </span>
                    </div>`;

        // Render message cho chuẩn mới (PPTX)
        if (message) {
            html += `<div style="color:#4b5563; font-size: 14px; padding: 8px 0; border-top:1px dashed #e5e7eb;">
                        💬 <i>${message}</i>
                     </div>`;
        }

        // Render details array cho chuẩn cũ (Word/Excel) nếu có
        if (crit.details && Array.isArray(crit.details)) {
            crit.details.forEach(det => {
                let actVal = det.actual;
                if(actVal !== null && typeof actVal === 'object') actVal = '[Object]';

                let detBadge = '';
                if (det.passed === true) detBadge = `<span style="color:#065f46; font-size:12px;">✅ PASS</span>`;
                else if (det.passed === 'PARTIAL') detBadge = `<span style="color:#92400e; font-size:12px;">⚠️ PART</span>`;
                else detBadge = `<span style="color:#991b1b; font-size:12px;">❌ FAIL</span>`;

                html += `<div style="display:flex; justify-content:space-between; padding: 6px 0; border-top:1px solid #f3f4f6;">
                            <span style="flex:1; padding-right:10px; font-size: 13px; color:#374151;">${det.desc} <br> <b style="color:#6b7280; font-weight:normal;">${actVal}</b></span>
                            <div style="text-align:right;">${detBadge}</div>
                         </div>`;
            });
        }

        html += `</div>`;
    });
    container.innerHTML = html;
}

// ==========================================
// 4. RENDER RUBRIC EDITOR
// ==========================================
function renderRubricEditor() {
    const container = document.getElementById('rubric-container');
    if (!currentRubricData || currentRubricData.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#999; margin-top:20px;">Vui lòng chọn file Rubric.</p>';
        return;
    }

    // Vì cấu trúc Rubric của Excel dùng các Action phức tạp (VERIFY_FUNCTION_NAME, col_index...)
    // thay vì GUI cứng nhắc, ta cung cấp một Textarea RAW JSON để GV sửa cho dễ dàng và linh hoạt
    container.innerHTML = `
        <div style="margin-bottom: 10px; color: #4b5563; font-size: 14px;">
            <b>Giao diện nâng cao:</b> Chỉnh sửa trực tiếp cấu trúc JSON của Rubric.
        </div>
        <textarea id="raw-rubric-editor" style="width: 100%; height: 600px; font-family: monospace; font-size: 13px; padding: 15px; border: 1px solid #d1d5db; border-radius: 6px; resize: vertical;">${JSON.stringify(currentRubricData, null, 4)}</textarea>
    `;
}

// ==========================================
// 5A. RENDER EXCEL PREVIEW (MỚI)
// ==========================================
function renderExcelNode(node, container) {
    if (!node || node.type !== 'workbook') return;

    // Lặp qua các thành phần của Workbook một cách an toàn
    (node.children || []).forEach(child => {
        // 1. Nếu là WORKSHEET (Vẽ bảng)
        if (child.type === 'worksheet') {
            const wrapper = document.createElement('div');
            wrapper.style.marginBottom = '30px';
            wrapper.style.background = '#fff';
            wrapper.style.padding = '15px';
            wrapper.style.borderRadius = '8px';
            wrapper.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

            // Tên Sheet
            const title = document.createElement('h3');
            title.innerText = `📄 Sheet: ${child.properties?.name || 'Unknown'}`;
            title.style.color = '#217346';
            title.style.borderBottom = '2px solid #217346';
            title.style.paddingBottom = '5px';
            wrapper.appendChild(title);

            // Bảng Excel
            const tableContainer = document.createElement('div');
            tableContainer.style.overflowX = 'auto'; // Cho phép cuộn ngang

            const table = document.createElement('table');
            table.style.borderCollapse = 'collapse';
            table.style.width = '100%';
            table.style.fontSize = '13px';

            (child.children || []).forEach(row => {
                if (row.type === 'row') {
                    const tr = document.createElement('tr');
                    (row.children || []).forEach(cell => {
                        if (cell.type === 'cell') {
                            const td = document.createElement('td');
                            td.style.border = '1px solid #d1d5db';
                            td.style.padding = '6px 10px';
                            td.style.minWidth = '60px';

                            // Highlight nếu có công thức động
                            if (cell.properties?.is_dynamic_formula) {
                                td.style.background = '#dcfce3'; // Nền xanh nhạt
                                td.title = 'Có công thức động';
                            }

                            // Lấy giá trị text
                            let textVal = '';
                            (cell.children || []).forEach(c => {
                                if (c.tag === 'v' || c.tag === 'is') textVal += (c.text || '');
                            });
                            td.innerText = textVal;

                            // Event xem JSON
                            td.style.cursor = 'pointer';
                            td.addEventListener('click', function(e) {
                                e.stopPropagation();
                                if (activeElement) activeElement.style.outline = 'none';
                                activeElement = td;
                                td.style.outline = '2px solid #ef4444';
                                document.getElementById('json-inspector').innerText = JSON.stringify(cell, null, 2);
                            });

                            tr.appendChild(td);
                        }
                    });
                    table.appendChild(tr);
                }
            });
            tableContainer.appendChild(table);
            wrapper.appendChild(tableContainer);
            container.appendChild(wrapper);
        }

        // 2. Nếu là CHART (Biểu đồ)
        else if (child.type === 'chart') {
            const chartDiv = document.createElement('div');
            chartDiv.style.background = '#eef2ff';
            chartDiv.style.padding = '10px 15px';
            chartDiv.style.borderLeft = '4px solid #3b82f6';
            chartDiv.style.marginBottom = '15px';
            chartDiv.style.cursor = 'pointer';
            chartDiv.innerHTML = `<b>📊 Biểu đồ:</b> Trục Y: ${child.properties?.chart_types?.join(', ') || 'Không rõ'}`;

            chartDiv.addEventListener('click', function(e) {
                e.stopPropagation();
                if (activeElement) activeElement.style.outline = 'none';
                activeElement = chartDiv;
                chartDiv.style.outline = '2px solid #ef4444';
                document.getElementById('json-inspector').innerText = JSON.stringify(child, null, 2);
            });
            container.appendChild(chartDiv);
        }

        // 3. Nếu là PIVOT TABLE
        else if (child.type === 'pivotTable') {
            const pivotDiv = document.createElement('div');
            pivotDiv.style.background = '#fef3c7';
            pivotDiv.style.padding = '10px 15px';
            pivotDiv.style.borderLeft = '4px solid #d97706';
            pivotDiv.style.marginBottom = '15px';
            pivotDiv.style.cursor = 'pointer';
            pivotDiv.innerHTML = `<b>🧮 Pivot Table:</b> ${child.properties?.name || 'Unknown'} (Click để xem chi tiết trường dữ liệu)`;

            pivotDiv.addEventListener('click', function(e) {
                e.stopPropagation();
                if (activeElement) activeElement.style.outline = 'none';
                activeElement = pivotDiv;
                pivotDiv.style.outline = '2px solid #ef4444';
                document.getElementById('json-inspector').innerText = JSON.stringify(child, null, 2);
            });
            container.appendChild(pivotDiv);
        }
    });
}

// ==========================================
// 5B. RENDER WORD PREVIEW (CŨ)
// ==========================================
function renderWordNode(node, container) {
    if (!node || typeof node !== 'object') return;
    let el = null;
    if (node.tag === 'w:document') { el = document.createElement('div'); }
    else if (node.tag === 'w:p') {
        el = document.createElement('div');
        el.style.minHeight = '1em';
        if (node.layout?.alignment) el.style.textAlign = node.layout.alignment;
        if (node.layout?.indent?.leftPt) el.style.paddingLeft = (node.layout.indent.leftPt) + 'px';
    }
    else if (node.tag === 'w:r') {
        el = document.createElement('span');
        if (node.text) el.innerText = node.text;
        if (node.properties?.bold || node.properties?.paragraphRunProperties?.bold) el.style.fontWeight = 'bold';
        if (node.properties?.italic || node.properties?.paragraphRunProperties?.italic) el.style.fontStyle = 'italic';
        if (node.properties?.fontSize || node.properties?.paragraphRunProperties?.fontSize) {
            let size = node.properties.fontSize || node.properties.paragraphRunProperties.fontSize;
            el.style.fontSize = (size) + 'px';
        }
    }
    else if (node.tag === 'w:tbl') { el = document.createElement('table'); el.style.width = '100%'; el.style.borderCollapse = 'collapse'; }
    else if (node.tag === 'w:tr') { el = document.createElement('tr'); }
    else if (node.tag === 'w:tc') {
        el = document.createElement('td');
        el.style.border = '1px solid #ccc';
        if (node.layout?.colspan) el.colSpan = node.layout.colspan;
        if (node.layout?.shading) el.style.backgroundColor = '#' + node.layout.shading;
    }

    if (!el && node.tag) {
        el = document.createElement('span');
        el.innerText = ` [${node.tag}] `;
        el.style.color = '#9ca3af';
        el.style.fontSize = '12px';
    }

    if (el) {
        el.className = 'word-node';
        el.addEventListener('click', function(e) {
            e.stopPropagation();
            if (activeElement) activeElement.style.outline = 'none';
            activeElement = el;
            el.style.outline = '2px solid #ef4444';
            document.getElementById('json-inspector').innerText = JSON.stringify(node, null, 2);
        });
        container.appendChild(el);
        if (node.children && Array.isArray(node.children)) {
            node.children.forEach(child => renderWordNode(child, el));
        }
    }
}
// ==========================================
// 5C. RENDER POWERPOINT PREVIEW (MỚI)
// ==========================================
function renderPptxNode(node, container) {
    if (!node || typeof node !== 'object') return;

    let el = document.createElement('div');

    // Style cơ bản mặc định
    el.style.margin = '5px 0';
    el.style.padding = '8px';
    el.style.borderRadius = '4px';
    el.className = 'pptx-node'; // Đặt class để dễ CSS nếu cần

    // Hàm helper gắn event click để xem JSON
    function attachClickEvent(element, astNode) {
        element.style.cursor = 'pointer';
        element.addEventListener('click', function(e) {
            e.stopPropagation();
            if (activeElement) activeElement.style.outline = 'none';
            activeElement = element;
            element.style.outline = '2px solid #ef4444';
            document.getElementById('json-inspector').innerText = JSON.stringify(astNode, null, 2);
        });
    }

    // ----------------------------------------------------
    // XỬ LÝ RENDER THEO TYPE CỦA NODE
    // ----------------------------------------------------
    if (node.type === 'presentation') {
        el.style.border = 'none';
        el.style.padding = '0';
    }
    else if (node.type === 'slide') {
        el.style.border = '2px solid #ea580c'; // Cam cho Slide thường
        el.style.background = '#fff';
        el.style.marginBottom = '20px';
        el.style.boxShadow = '0 2px 5px rgba(0,0,0,0.1)';

        let title = document.createElement('h3');
        title.innerText = `🎞️ Slide ${node.properties?.slide_index || ''}`;
        title.style.color = '#ea580c';
        title.style.borderBottom = '1px solid #ea580c';
        title.style.paddingBottom = '5px';
        title.style.marginTop = '0';
        el.appendChild(title);
    }
    else if (node.type === 'slide_master' || node.type === 'slide_layout') {
        el.style.border = '2px solid #8b5cf6'; // Tím cho Master/Layout
        el.style.background = '#f8fafc';
        el.style.marginBottom = '20px';

        let title = document.createElement('h4');
        let isMaster = node.type === 'slide_master';
        title.innerText = isMaster ? `👑 Slide Master (ID: ${node.properties?.master_id || ''})` : `📐 Slide Layout (ID: ${node.properties?.layout_id || ''})`;
        title.style.color = '#4f46e5';
        title.style.margin = '0 0 10px 0';
        el.appendChild(title);
    }
    else if (node.type === 'shape') {
        el.style.border = '1px solid #d1d5db';
        el.style.background = '#f3f4f6';

        let label = document.createElement('div');
        label.style.fontSize = '12px';
        label.style.color = '#6b7280';
        label.style.marginBottom = '5px';

        let shapeName = node.attributes?.name || 'Shape';
        if (node.properties?.is_action_button) {
            shapeName = `🔘 Action Button (${node.properties.geometry_type})`;
        } else if (node.properties?.is_placeholder) {
            shapeName += ` [Placeholder: ${node.properties.placeholder?.type || ''}]`;
        }

        // Cảnh báo nếu có Animation
        let hasAnim = node.properties?.animations?.length > 0 ? ' ✨(Có Animation)' : '';

        label.innerText = `🟦 ${shapeName}${hasAnim}`;
        el.appendChild(label);
    }
    else if (node.type === 'graphic_frame') {
        el.style.border = '2px dashed #3b82f6';
        el.style.background = '#eff6ff';
        let label = document.createElement('div');
        label.innerHTML = `<b>📊 Graphic Frame:</b> ${node.properties?.frame_type || 'Unknown'}`;
        label.style.color = '#1d4ed8';
        label.style.marginBottom = '5px';
        el.appendChild(label);
    }
    else if (node.type === 'table') {
        el = document.createElement('table'); // Thay div bằng table
        el.style.width = '100%';
        el.style.borderCollapse = 'collapse';
        el.style.margin = '10px 0';
    }
    else if (node.type === 'table_row') {
        el = document.createElement('tr'); // Thay div bằng tr
    }
    else if (node.type === 'table_cell') {
        el = document.createElement('td'); // Thay div bằng td
        el.style.border = '1px solid #9ca3af';
        el.style.padding = '8px';
        if (node.attributes?.gridSpan) el.colSpan = node.attributes.gridSpan; // Khớp với PPTX AST
        if (node.attributes?.rowSpan) el.rowSpan = node.attributes.rowSpan;
    }
    else if (node.type === 'picture') {
        el.style.border = '1px solid #9ca3af';
        el.style.background = '#e5e7eb';
        el.innerHTML = `🖼️ <b>Picture:</b> ${node.properties?.filename || 'Unknown'}`;
    }
    else if (node.type === 'transition') {
        el.style.border = '1px solid #f0abfc';
        el.style.background = '#fdf4ff';
        el.innerHTML = `✨ <b>Transition:</b> ${node.properties?.effect_type || 'None'} (Speed: ${node.attributes?.spd || 'N/A'})`;
    }
    else if (node.type === 'paragraph') {
        el.style.border = 'none';
        el.style.padding = '2px 0';
        el.style.margin = '2px 0';
        if (node.style?.align) el.style.textAlign = node.style.align;
    }
    else if (node.type === 'text_run') {
        el = document.createElement('span'); // Thay div bằng span để text liền mạch
        if (node.text) el.innerText = node.text;

        // CSS Style cơ bản cho text
        if (node.style?.b === '1') el.style.fontWeight = 'bold';
        if (node.style?.i === '1') el.style.fontStyle = 'italic';
        if (node.style?.sz) el.style.fontSize = (parseInt(node.style.sz) / 100) + 'px'; // AST lưu sz theo định dạng pt*100
    }
    else {
        // Fallback cho các node lạ
        el.style.border = '1px dashed #ccc';
        el.innerHTML = `<span style="color:#999; font-size:12px;">[${node.type || node.tag || 'Unknown'}]</span>`;
    }

    // Gắn Event Click cho element hiện tại
    attachClickEvent(el, node);
    container.appendChild(el);

    // Đệ quy render các node con
    if (node.children && Array.isArray(node.children)) {
        node.children.forEach(child => renderPptxNode(child, el));
    }
}
// Khởi chạy lần đầu: nạp danh sách file vào dropdown
window.onload = () => {
    switchTab('report');
    loadFileList();
};