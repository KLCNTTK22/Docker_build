/**
 * EXCEL RUBRIC BUILDER - MANUAL + PICK MODE
 */
const ExcelRubricBuilder = (function () {
    let currentAST = null;
    let rubric = [];
    let pickingTargetInputId = null; // Lưu ID của thẻ Input đang chờ lấy dữ liệu

    // --- HELPER DỊCH ĐƯỜNG DẪN AST LẤY TEXT/FORMULA ---
    function getNodeByPath(path) {
        if (!currentAST || !path) return null;
        let parts = path.split('.');
        let node = currentAST;
        for (let i = 0; i < parts.length; i++) {
            let part = parts[i];
            if (node[part] !== undefined) {
                node = node[part];
            } else {
                return null;
            }
        }
        return node;
    }

    function extractNodeData(node) {
        let text = "";
        let formula = "";
        let isDynamic = false;

        if (node.type === 'row' || node.tag === 'row') {
            // Lấy toàn bộ chữ trong dòng (dùng làm mỏ neo Header)
            let cells = node.children ? node.children.filter(c => c.tag === 'c' || c.type === 'cell') : [];
            let vals = [];
            cells.forEach(c => {
                let cellData = extractNodeData(c);
                if (cellData.text) vals.push(cellData.text);
            });
            text = vals.join(", ");
        } else if (node.type === 'cell' || node.tag === 'c') {
            if (node.children) {
                node.children.forEach(v => {
                    if (v.tag === 'v' || v.type === 'value') text = v.text ?? v.value ?? "";
                    if (v.tag === 'f' || v.type === 'formula') formula = v.text ?? v.value ?? "";
                });
            }
            isDynamic = node.properties?.is_dynamic_formula || false;
        } else {
            // Các node khác
            if (node.text) text = node.text;
        }

        return { text: text.trim(), formula: formula.trim(), isDynamic };
    }

    // --- CORE BUILDER LOGIC ---
    function init(astData) {
        currentAST = astData;
        rubric = [];
        pickingTargetInputId = null;
        document.getElementById('excel-speed-tools').style.display = 'flex';
        renderBuilderUI();
    }

    function enablePickMode(inputId, typeHint) {
        pickingTargetInputId = inputId;
        if (typeof showToast === 'function') {
            showToast(`Hãy click vào một ${typeHint} trên bảng xem trước để lấy dữ liệu.`, 'warning');
        }
    }

    function handleNodeClick(astPath) {
        if (!pickingTargetInputId) {
            if (typeof showToast === 'function') showToast("Vui lòng bấm nút [Chọn] ở Form Tiêu chí trước khi click vào lưới.", "warning");
            return;
        }

        let targetPath = astPath;

        // =========================================================
        // THUẬT TOÁN BẮT DÒNG (ROW) KHI CLICK VÀO MỘT Ô (CELL)
        // =========================================================
        if (pickingTargetInputId.includes('_headers')) {
            // Đường dẫn của ô thường có dạng: children.0.children.5.children.2
            // Chúng ta sẽ cắt bỏ phần đuôi (.children.2) để lấy đường dẫn của Dòng: children.0.children.5
            let parts = astPath.split('.');
            if (parts.length >= 4) {
                targetPath = parts.slice(0, 4).join('.');
            }
        }

        const node = getNodeByPath(targetPath);
        if (!node) return;

        const data = extractNodeData(node);
        const inputEl = document.getElementById(pickingTargetInputId);

        if (inputEl) {
            // Nháy nền xanh để báo hiệu lấy dữ liệu thành công
            inputEl.style.transition = 'background-color 0.3s';
            inputEl.style.backgroundColor = '#d1e7dd';
            setTimeout(() => inputEl.style.backgroundColor = '', 500);

            // Phân loại xử lý dựa vào input đang yêu cầu gì
            if (inputEl.classList.contains('pick-formula') && data.formula) {
                // Tách lấy tên hàm (VD: =VLOOKUP(...) -> VLOOKUP)
                let funcMatch = data.formula.match(/^[=]?([A-Z]+)\(/i);
                inputEl.value = funcMatch ? funcMatch[1].toUpperCase() : data.formula;
            } else {
                // Ở đây data.text của Row sẽ tự động trả về: "STT, Số chứng từ, Tên vật tư..."
                // Xóa bỏ các giá trị rỗng thừa do các cột trống gây ra
                if (pickingTargetInputId.includes('_headers')) {
                    let cleanHeaders = data.text.split(',').map(s => s.trim()).filter(s => s !== "");
                    inputEl.value = cleanHeaders.join(", ");
                } else {
                    inputEl.value = data.text;
                }
            }

            // Kích hoạt sự kiện thay đổi để hệ thống lưu dữ liệu vào mảng JSON Rubric
            inputEl.dispatchEvent(new Event('change'));
        }

        pickingTargetInputId = null; // Tắt chế độ Pick sau khi hoàn thành
    }

    function renderBuilderUI() {
        const area = document.getElementById('rubric-builder-area');
        const emptyState = document.getElementById('rubric-empty-state');
        if (!area) return;

        if (rubric.length === 0) {
            emptyState.style.display = 'block';
            area.classList.add('d-none');
            area.innerHTML = '';
            return;
        }

        emptyState.style.display = 'none';
        area.classList.remove('d-none');
        area.innerHTML = '';

        rubric.forEach((crit, cIdx) => {
            const card = document.createElement('div');
            card.className = 'card shadow-sm mb-3 border-success';

            // KIỂM TRA XEM CÓ PHẢI LÀ TIÊU CHÍ TOÀN CỤC (GLOBAL) KHÔNG
            let isGlobal = false;
            let loc = crit.region_definition?.locator;
            if (loc && loc.type === 'global') isGlobal = true;
            if (crit.anchor_locator && crit.anchor_locator.type === 'global') isGlobal = true;

            let anchorHtml = '';
            if (isGlobal) {
                // NẾU LÀ GLOBAL -> ẨN MỎ NEO, HIỂN THỊ THÔNG BÁO
                anchorHtml = `
                    <div class="alert alert-info py-2 mb-2 small shadow-sm border-info">
                        <i class="bi bi-globe-americas"></i> <b>Phạm vi Toàn cục (Global):</b> Tiêu chí này không cần Mỏ neo. Hệ thống sẽ quét toàn bộ file để kiểm tra (Ví dụ: Biểu đồ, Pivot Table, Sheet Name).
                    </div>
                `;
            } else {
                // NẾU LÀ BẢNG BÌNH THƯỜNG -> HIỂN THỊ MỎ NEO
                let headersStr = (loc && loc.required_headers) ? loc.required_headers.join(", ") : "";
                anchorHtml = `
                    <div class="border rounded p-2 mb-2 bg-white border-warning">
                        <label class="form-label small fw-bold text-warning-emphasis mb-1"><i class="bi bi-geo-alt"></i> Mỏ neo (Nhận diện bảng): Các cột bắt buộc có</label>
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control" id="crit_${cIdx}_headers"
                                   placeholder="VD: STT, Mã hàng, Số lượng, Đơn giá..." value="${headersStr}"
                                   onchange="ExcelRubricBuilder.updateAnchor(${cIdx}, this.value)">
                            <button class="btn btn-outline-warning text-dark fw-bold" type="button" 
                                    onclick="ExcelRubricBuilder.enablePickMode('crit_${cIdx}_headers', 'Dòng tiêu đề')">
                                <i class="bi bi-cursor-fill"></i> Chọn dòng trên lưới
                            </button>
                        </div>
                        <small class="text-muted" style="font-size: 11px;">Hệ thống sẽ tự động quét file để tìm bảng chứa các cột này.</small>
                    </div>
                `;
            }

            let html = `
                <div class="card-header bg-success-subtle d-flex justify-content-between align-items-center p-2">
                    <input type="text" class="form-control form-control-sm fw-bold border-success w-50" 
                           value="${crit.criteria_name}" placeholder="Tên tiêu chí (VD: Câu 1...)" 
                           onchange="ExcelRubricBuilder.updateCrit(${cIdx}, 'criteria_name', this.value)">
                    
                    <div class="input-group input-group-sm w-25">
                        <span class="input-group-text bg-white">Điểm</span>
                        <input type="number" step="0.1" class="form-control text-center" 
                               value="${crit.allocated_points}" 
                               onchange="ExcelRubricBuilder.updateCrit(${cIdx}, 'allocated_points', parseFloat(this.value)||0)">
                    </div>
                    
                    <button class="btn btn-sm btn-danger" onclick="ExcelRubricBuilder.removeCrit(${cIdx})"><i class="bi bi-trash"></i></button>
                </div>
                
                <div class="card-body p-2 bg-light">
                    ${anchorHtml}

                    <div class="rules-container ps-3 border-start border-2 border-secondary" id="rules_container_${cIdx}">
                        ${renderRules(cIdx, crit.rules)}
                    </div>
                    
                    <div class="mt-3 text-end dropup">
                        <button class="btn btn-sm btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown">
                            <i class="bi bi-plus-circle"></i> Thêm Quy tắc chấm
                        </button>
                        <ul class="dropdown-menu shadow border-0">
                            <li><h6 class="dropdown-header text-primary"><i class="bi bi-table"></i> Hàm & Dữ liệu</h6></li>
                            <li><a class="dropdown-item small" href="#" onclick="ExcelRubricBuilder.addSpecificRule(${cIdx}, 'VERIFY_COLUMN_HYBRID')"><i class="bi bi-cpu"></i> Chấm Động Toàn Cột (Hybrid)</a></li>
                            <li><a class="dropdown-item small" href="#" onclick="ExcelRubricBuilder.addSpecificRule(${cIdx}, 'VERIFY_EXTRACTED_DATA')"><i class="bi bi-funnel"></i> Rút trích Dữ liệu (Advanced Filter)</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><h6 class="dropdown-header text-info"><i class="bi bi-pie-chart"></i> Đối tượng (Pivot/Chart)</h6></li>
                            <li><a class="dropdown-item small" href="#" onclick="ExcelRubricBuilder.addSpecificRule(${cIdx}, 'VERIFY_PIVOT_TABLE')"><i class="bi bi-layout-split"></i> Cấu trúc Pivot Table</a></li>
                            <li><a class="dropdown-item small" href="#" onclick="ExcelRubricBuilder.addSpecificRule(${cIdx}, 'VERIFY_CHART_TYPE')"><i class="bi bi-bar-chart"></i> Loại Biểu đồ</a></li>
                            <li><a class="dropdown-item small" href="#" onclick="ExcelRubricBuilder.addSpecificRule(${cIdx}, 'VERIFY_CHART_SERIES_KEYWORDS')"><i class="bi bi-list-columns-reverse"></i> Dữ liệu vẽ Biểu đồ</a></li>
                        </ul>
                    </div>
                </div>
            `;
            card.innerHTML = html;
            area.appendChild(card);
        });

        const btnSave = document.getElementById('btnSaveRubric');
        if (btnSave) btnSave.disabled = rubric.length === 0;
    }

    function renderRules(cIdx, rules) {
        if (!rules || rules.length === 0) return '<div class="text-muted small fst-italic">Chưa có quy tắc nào. Hệ thống sẽ bỏ qua tiêu chí này.</div>';

        let html = '';
        rules.forEach((rule, rIdx) => {
            const btnRemove = `<button class="btn btn-sm btn-outline-danger position-absolute top-0 end-0 m-1 border-0" onclick="ExcelRubricBuilder.removeRule(${cIdx}, ${rIdx})"><i class="bi bi-x-lg"></i></button>`;
            const scoreInput = `
                <div class="col-md-3 col-sm-4 d-flex">
                    <span class="input-group-text py-0 border-0 bg-transparent small fw-bold text-danger">Điểm</span>
                    <input type="number" step="0.1" class="form-control form-control-sm border-danger" value="${rule.points || 0}"
                           onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'points', parseFloat(this.value)||0)">
                </div>`;

            if (rule.action === "VERIFY_COLUMN_HYBRID") {
                let st = rule.strict_check || {};
                let expVals = (st.expected_values || []).join(", ");
                let funcs = (st.allowed_functions || []).join(", ");

                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card">
                        ${btnRemove}
                        <h6 class="text-primary small fw-bold mb-2"><i class="bi bi-cpu"></i> Chấm Động (Hybrid) Toàn Cột</h6>
                        
                        <div class="row g-2 align-items-center mb-2">
                            <div class="col-5">
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control" id="rule_${cIdx}_${rIdx}_col" placeholder="Tên cột (VD: Thành tiền)" value="${rule.target_column || ''}"
                                           onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'target_column', this.value)">
                                    <button class="btn btn-outline-secondary" onclick="ExcelRubricBuilder.enablePickMode('rule_${cIdx}_${rIdx}_col', 'Ô tiêu đề cột')"><i class="bi bi-cursor"></i> Pick</button>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text">Dòng tối đa</span>
                                    <input type="number" class="form-control" value="${rule.expected_total_rows || 10}" 
                                           onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'expected_total_rows', parseInt(this.value)||1)">
                                </div>
                            </div>
                            ${scoreInput}
                        </div>

                        <div class="row g-2 mb-1 bg-danger-subtle p-2 rounded mx-0">
                            <div class="col-12"><span class="small fw-bold text-danger">Chấm gắt gao (Dòng đầu)</span></div>
                            <div class="col-3">
                                <input type="number" class="form-control form-control-sm" title="Số dòng kiểm tra kỹ" value="${st.check_limit || 4}"
                                       onchange="ExcelRubricBuilder.updateHybridRule(${cIdx}, ${rIdx}, 'strict_check', 'check_limit', parseInt(this.value)||0)">
                            </div>
                            <div class="col-5">
                                <input type="text" class="form-control form-control-sm" placeholder="Đáp án chuẩn (cách bằng phẩy)" value="${expVals}"
                                       onchange="ExcelRubricBuilder.updateHybridRule(${cIdx}, ${rIdx}, 'strict_check', 'expected_values', this.value)">
                            </div>
                            <div class="col-4">
                                <input type="text" class="form-control form-control-sm pick-formula" id="rule_${cIdx}_${rIdx}_func" 
                                       placeholder="Hàm yêu cầu (SUM...)" value="${funcs}"
                                       onclick="ExcelRubricBuilder.enablePickMode('rule_${cIdx}_${rIdx}_func', 'Ô chứa công thức')"
                                       onchange="ExcelRubricBuilder.updateHybridRule(${cIdx}, ${rIdx}, 'strict_check', 'allowed_functions', this.value)">
                            </div>
                        </div>
                    </div>`;
            }

            else if (rule.action === "VERIFY_PIVOT_TABLE") {
                let isDataFld = rule.field_type === 'data';
                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card border-info">
                        ${btnRemove}
                        <h6 class="text-info small fw-bold mb-2"><i class="bi bi-layout-split"></i> Cấu trúc Pivot Table</h6>
                        <div class="row g-2 align-items-center">
                            <div class="col-3">
                                <select class="form-select form-select-sm" onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'field_type', this.value); ExcelRubricBuilder.refreshUI();">
                                    <option value="row" ${rule.field_type === 'row' ? 'selected' : ''}>Kéo vào Row</option>
                                    <option value="col" ${rule.field_type === 'col' ? 'selected' : ''}>Kéo vào Column</option>
                                    <option value="data" ${rule.field_type === 'data' ? 'selected' : ''}>Kéo vào Data (Values)</option>
                                </select>
                            </div>
                            <div class="col-3">
                                <input type="text" class="form-control form-control-sm" placeholder="Field ID (VD: 3 hoặc 6)" value="${rule.expected_fld || ''}"
                                       onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'expected_fld', this.value)">
                            </div>
                            <div class="col-3">
                                <select class="form-select form-select-sm" onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'expected_subtotal', this.value)" ${!isDataFld ? 'disabled' : ''}>
                                    <option value="sum" ${rule.expected_subtotal === 'sum' ? 'selected' : ''}>Hàm SUM</option>
                                    <option value="count" ${rule.expected_subtotal === 'count' ? 'selected' : ''}>Hàm COUNT</option>
                                    <option value="average" ${rule.expected_subtotal === 'average' ? 'selected' : ''}>Hàm AVERAGE</option>
                                </select>
                            </div>
                            ${scoreInput}
                        </div>
                    </div>`;
            }

            else if (rule.action === "VERIFY_CHART_TYPE") {
                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card border-primary">
                        ${btnRemove}
                        <h6 class="text-primary small fw-bold mb-2"><i class="bi bi-bar-chart"></i> Phân loại Biểu đồ</h6>
                        <div class="row g-2 align-items-center">
                            <div class="col-9">
                                <select class="form-select form-select-sm" onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'expected_type', this.value)">
                                    <option value="barchart" ${rule.expected_type === 'barchart' ? 'selected' : ''}>Biểu đồ Cột (Bar / Column)</option>
                                    <option value="piechart" ${rule.expected_type === 'piechart' ? 'selected' : ''}>Biểu đồ Tròn (Pie)</option>
                                    <option value="linechart" ${rule.expected_type === 'linechart' ? 'selected' : ''}>Biểu đồ Đường (Line)</option>
                                    <option value="scatterchart" ${rule.expected_type === 'scatterchart' ? 'selected' : ''}>Biểu đồ Phân tán (Scatter)</option>
                                </select>
                            </div>
                            ${scoreInput}
                        </div>
                    </div>`;
            }

            else if (rule.action === "VERIFY_CHART_SERIES_KEYWORDS") {
                let kws = (rule.expected_series_keywords || []).join(", ");
                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card border-primary">
                        ${btnRemove}
                        <h6 class="text-primary small fw-bold mb-2"><i class="bi bi-list-columns-reverse"></i> Dữ liệu vẽ Biểu đồ (Series / Values)</h6>
                        <div class="row g-2 align-items-center">
                            <div class="col-9">
                                <input type="text" class="form-control form-control-sm" placeholder="Từ khóa trong bảng nguồn (VD: doanh thu, số lượng)" value="${kws}"
                                       onchange="ExcelRubricBuilder.updateArrayRule(${cIdx}, ${rIdx}, 'expected_series_keywords', this.value)">
                            </div>
                            ${scoreInput}
                        </div>
                    </div>`;
            }

            else if (rule.action === "VERIFY_EXTRACTED_DATA") {
                let fb = (rule.forbidden_values || []).join(", ");
                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card border-warning">
                        ${btnRemove}
                        <h6 class="text-warning-emphasis small fw-bold mb-2"><i class="bi bi-funnel"></i> Lọc Trích Xuất (Advanced Filter)</h6>
                        <div class="row g-2 align-items-center">
                            <div class="col-5">
                                <input type="text" class="form-control form-control-sm border-warning" placeholder="Dữ liệu bắt buộc có (VD: xăng a92)" value="${rule.expected_value || ''}"
                                       onchange="ExcelRubricBuilder.updateRule(${cIdx}, ${rIdx}, 'expected_value', this.value)">
                            </div>
                            <div class="col-4">
                                <input type="text" class="form-control form-control-sm" placeholder="Cấm chứa chữ (VD: nhớt, dầu)" value="${fb}"
                                       onchange="ExcelRubricBuilder.updateArrayRule(${cIdx}, ${rIdx}, 'forbidden_values', this.value)">
                            </div>
                            ${scoreInput}
                        </div>
                    </div>`;
            }

            else {
                html += `
                    <div class="border rounded p-2 mb-2 bg-white position-relative rule-card">
                        ${btnRemove}
                        <div class="text-muted small">Quy tắc cơ bản: <b>${rule.action}</b></div>
                    </div>`;
            }
        });
        return html;
    }

    function createGlobalCriteria() {
        rubric.push({
            criteria_name: "Tiêu chí Đối tượng Toàn cục (Chart/Pivot)",
            allocated_points: 1.0,
            region_definition: {
                region_id: "GLOBAL_" + Date.now(),
                locator: { type: "global" }
            },
            anchor_locator: { type: "global" }, // Hỗ trợ cả Engine cũ
            rules: []
        });
        renderBuilderUI();
    }

    // --- DATA MUTATION ---
    function createEmptyCriteria() {
        rubric.push({
            criteria_name: "Tiêu chí mới",
            allocated_points: 1.0,
            region_definition: {
                region_id: "BANG_" + Date.now(),
                locator: { type: "header_signature", required_headers: [] }
            },
            rules: []
        });
        renderBuilderUI();
    }

    function refreshUI() {
        renderBuilderUI(); // Trợ thủ để render lại UI khi thay đổi Dropdown (ví dụ khóa dropdown subtotal của pivot)
    }

    function addSpecificRule(cIdx, ruleType) {
        let newRule = { action: ruleType, points: 1.0 };

        if (ruleType === "VERIFY_COLUMN_HYBRID") {
            newRule = {
                action: "VERIFY_COLUMN_HYBRID", target_column: "", expected_total_rows: 10, points: 1.0,
                strict_check: { check_limit: 4, expected_values: [], allowed_functions: [] },
                loose_check: { require_dynamic_formula: true }
            };
        } else if (ruleType === "VERIFY_PIVOT_TABLE") {
            newRule = { action: "VERIFY_PIVOT_TABLE", field_type: "row", source_col_header: "", expected_subtotal: "sum", points: 1.0 };
        } else if (ruleType === "VERIFY_CHART_TYPE") {
            newRule = { action: "VERIFY_CHART_TYPE", expected_type: "barchart", points: 0.5 };
        } else if (ruleType === "VERIFY_CHART_SERIES_KEYWORDS") {
            newRule = { action: "VERIFY_CHART_SERIES_KEYWORDS", expected_series_keywords: [], points: 1.0 };
        } else if (ruleType === "VERIFY_EXTRACTED_DATA") {
            newRule = { action: "VERIFY_EXTRACTED_DATA", expected_value: "", forbidden_values: [], points: 1.0 };
        }

        rubric[cIdx].rules.push(newRule);
        renderBuilderUI();
    }

    function removeCrit(idx) { rubric.splice(idx, 1); renderBuilderUI(); }
    function removeRule(cIdx, rIdx) { rubric[cIdx].rules.splice(rIdx, 1); renderBuilderUI(); }

    function updateCrit(cIdx, key, val) { rubric[cIdx][key] = val; }
    function updateRule(cIdx, rIdx, key, val) { rubric[cIdx].rules[rIdx][key] = val; }

    function updateArrayRule(cIdx, rIdx, key, strVal) {
        rubric[cIdx].rules[rIdx][key] = strVal.split(',').map(s => s.trim()).filter(s => s);
    }

    function updateAnchor(cIdx, strVal) {
        if (!rubric[cIdx].region_definition) rubric[cIdx].region_definition = { locator: { type: "header_signature" } };
        rubric[cIdx].region_definition.locator.required_headers = strVal.split(',').map(s => s.trim()).filter(s => s);
    }

    function updateHybridRule(cIdx, rIdx, block, key, val) {
        let rule = rubric[cIdx].rules[rIdx];
        if (!rule[block]) rule[block] = {};

        if (key === 'expected_values' || key === 'allowed_functions') {
            rule[block][key] = val.split(',').map(s => s.trim()).filter(s => s);
        } else {
            rule[block][key] = val;
        }
    }

    // --- QUICK TOOLS ---
    function addGlobalObjectCheck(objType) {
        let name = objType === 'chart' ? 'Biểu đồ' : 'Pivot Table';
        rubric.push({
            criteria_name: `Kiểm tra Tồn tại ${name}`,
            allocated_points: 0.5,
            anchor_locator: { type: "global" },
            rules: [{
                description: `File phải có ${name}`,
                action: "VERIFY_OBJECT_EXISTS",
                expected_object: objType,
                points: 0.5
            }]
        });
        renderBuilderUI();
        if (typeof showToast === 'function') showToast(`Đã thêm tiêu chí kiểm tra ${name}.`, 'success');
    }

    function getRubric() { return rubric; }
    function exportRubric() {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(rubric, null, 2));
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", "excel_rubric.json");
        dlAnchorElem.click();
    }
    function showRubricModal() {
        alert(JSON.stringify(rubric, null, 2));
    }

    return {
        init,
        handleNodeClick,
        enablePickMode,
        createEmptyCriteria,
        addSpecificRule,
        refreshUI,
        removeCrit,
        removeRule,
        updateCrit,
        updateRule,
        updateArrayRule,
        updateAnchor,
        updateHybridRule,
        addGlobalObjectCheck,
        getRubric,
        exportRubric,
        createGlobalCriteria,
        showRubricModal
    };
})();