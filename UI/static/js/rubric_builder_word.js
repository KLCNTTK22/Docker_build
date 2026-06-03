/**
 * RUBRIC BUILDER MODULE
 * Quản lý AST, sinh Form cấu hình và xuất JSON Rule Engine
 */

const RubricBuilder = (function () {
    let globalRubric = [];
    let currentPendingRules = [];
    let AST = null;
    let currentNodePath = null;

    // Danh sách "Tự chọn"
    const RULE_TEMPLATES = [
        { label: "📦 Cấu hình Nhóm con (Bảng, Danh sách...)", path: "", type: "SCOPE" },
        { label: "Font chữ (Ví dụ: Arial)", path: "properties.resolvedFont", type: "STRICT" },
        { label: "Cỡ chữ (Ví dụ: 14)", path: "properties.fontSize", type: "TOLERANT_RANGE" },
        { label: "Chữ In đậm", path: "properties.bold", type: "STRICT", val: true },
        { label: "Chữ In nghiêng", path: "properties.italic", type: "STRICT", val: true },
        { label: "Chữ Gạch ngang", path: "properties.strike", type: "STRICT", val: true },
        { label: "Chữ Gạch chân", path: "properties.underline", type: "STRICT", val: "single" },
        { label: "Căn lề (Trái/Phải/Giữa)", path: "layout.alignment", type: "TOLERANT_VALS" },
        { label: "Kiểu danh sách (Bullet/Decimal)", path: "list.format", type: "TOLERANT_VALS" },
        { label: "Tab Stop (Căn lề)", path: "layout.tabs.0.align", type: "STRICT" },
        { label: "Tab Leader (Dấu chấm)", path: "layout.tabs.0.leader", type: "STRICT", val: "dot" },
        { label: "Gộp ô (Colspan)", path: "layout.colspan", type: "STRICT" },
        { label: "Viền bảng (Border Top)", path: "borders.top.style", type: "STRICT" },
        { label: "Chia cột (Columns)", path: "section.columns.count", type: "STRICT" },
        { label: "Link liên kết (URL)", path: "references.0.url", type: "STRICT" },
        { label: "Nội dung Text (Fuzzy)", path: "", type: "FUZZY_TEXT" }
    ];

    function init(parsedAST) {
        AST = parsedAST;
        globalRubric = [];
    }

    function extractAllText(node) {
        if (!node) return "";
        let txt = node.text || "";
        if (node.children) node.children.forEach(c => txt += extractAllText(c));
        return txt;
    }

    function getNodeByPath(path) {
        if (!path) return AST;
        const keys = path.split('.');
        let current = AST;
        for (let key of keys) {
            if (current && current[key] !== undefined) current = current[key];
            else return null;
        }
        return current;
    }

    function getNestedValue(obj, path) {
        if (!path) return obj;
        if (path === 'children.length') return obj.children ? obj.children.length : 0;
        const keys = path.split('.');
        let current = obj;
        for (let key of keys) {
            if (current && current[key] !== undefined) current = current[key];
            else return null;
        }
        return current;
    }

    // ==========================================
    // CÁC HÀM XỬ LÝ NÚT NHANH TRÊN GIAO DIỆN
    // ==========================================

    function addGlobalPageSetup() {
        if (!AST || !AST.section) {
            if (typeof showToast === 'function') showToast("Không tìm thấy thông tin Page Setup.", "warning");
            return;
        }
        const sec = AST.section;
        currentNodePath = "w:document";
        currentPendingRules = [];

        // Tạo luật
        const createTol = (desc, path, val) => {
            const v = parseFloat(val);
            return {
                id: Date.now() + Math.random(), description: desc, property_path: path, expected_value: v,
                match_flag: "TOLERANT", accepted_range: [Math.floor(v * 0.95), Math.ceil(v * 1.05)], points: 0.5
            };
        };

        if (sec.pageSize && sec.pageSize.w) currentPendingRules.push(createTol("Kiểm tra Chiều rộng trang", "section.pageSize.w", sec.pageSize.w));
        if (sec.margin) {
            if (sec.margin.top) currentPendingRules.push(createTol("Kiểm tra Lề trên", "section.margin.top", sec.margin.top));
            if (sec.margin.bottom) currentPendingRules.push(createTol("Kiểm tra Lề dưới", "section.margin.bottom", sec.margin.bottom));
            if (sec.margin.left) currentPendingRules.push(createTol("Kiểm tra Lề trái", "section.margin.left", sec.margin.left));
        }
        renderBuilderArea("Cài đặt Trang (Page Setup)", "w:document", "");
    }

    // Hàm tạo preset kiểm tra Hình ảnh/Shape theo chuẩn quét FORWARD
    function addGlobalExistenceCheck(typeString) {
        currentNodePath = null;
        currentPendingRules = [];

        let rule = {
            id: Date.now(),
            description: `Quét xuống dưới để tìm ${typeString === 'image' ? 'Hình ảnh' : typeString}`,
            property_path: "",
            expected_value: "",
            match_flag: "PRESENCE_ONLY",
            search_mode: "FORWARD",
            search_target_key: "type",
            search_target_value: typeString,
            points: 1.0
        };

        currentPendingRules.push(rule);

        // Render form với Tag mặc định là w:p và dặn người dùng click chọn chữ
        renderBuilderArea(`Kiểm tra chèn ${typeString}`, "w:p", "");
        if (typeof showToast === 'function') showToast(`Hãy CLICK VÀO DÒNG CHỮ ngay phía trước ${typeString} để làm mốc bắt đầu quét!`, "info");
    }

    function addGlobalHeaderFooterCheck() {
        currentNodePath = "w:document";
        currentPendingRules = [];
        let rule = createRuleObj(`Tồn tại Header / Footer`, "section.headers_footers", "", "PRESENCE_ONLY");
        rule.points = 1.0;
        currentPendingRules.push(rule);
        renderBuilderArea("Kiểm tra có tạo Header/Footer", "w:document", "");
    }

    function createEmptyCriteria() {
        currentPendingRules = [];
        currentNodePath = null;
        renderBuilderArea("Tiêu chí Tự chọn", "w:p", "");
    }

    // ==========================================
    // SỰ KIỆN CLICK TỪ TÀI LIỆU
    // ==========================================
    function handleNodeClick(astPath) {
        currentNodePath = astPath;
        const node = getNodeByPath(astPath);
        if (!node) return;

        const nodeText = extractAllText(node).trim();
        let defaultTag = node.tag || node.type;
        let defaultText = node.tag === 'w:p' && nodeText.length > 2 ? nodeText.substring(0, 30) : "";

        const builderArea = document.getElementById('rubric-builder-area');

        // NẾU FORM ĐANG MỞ -> Hành động này là "Hút dữ liệu" vào Form
        if (!builderArea.classList.contains('d-none') && currentPendingRules.length > 0) {
            // Cập nhật lại Mỏ neo trên UI
            document.getElementById('criteria_anchor_tag').value = defaultTag;
            document.getElementById('criteria_anchor_text').value = defaultText;

            // Hút dữ liệu vào các luật còn trống
            autoFillEmptyRulesFromNode(currentPendingRules, node);
            renderCart();
            if (typeof showToast === 'function') showToast("Đã lấy thông số từ văn bản vào Tiêu chí!", "success");
            return;
        }

        // NẾU CHƯA CÓ FORM -> Khởi tạo mới và gợi ý
        currentPendingRules = [];
        let displayTitle = nodeText ? `Đoạn văn: "${nodeText.substring(0, 30)}..."` : `Đối tượng: ${defaultTag}`;

        renderBuilderArea(displayTitle, defaultTag, defaultText);
        autoDetectProperties(node, nodeText);
    }

    // ==========================================
    // RENDER GIAO DIỆN (UI BÌNH DÂN HÓA MỎ NEO)
    // ==========================================
    function renderBuilderArea(title, anchorTag, anchorTextVal) {
        document.getElementById('rubric-empty-state').classList.add('d-none');
        const builderArea = document.getElementById('rubric-builder-area');
        builderArea.classList.remove('d-none');

        let optionsHtml = RULE_TEMPLATES.map((tpl, i) => `<option value="${i}">${tpl.label}</option>`).join('');

        // Thiết kế khu vực Mỏ Neo (Chia đôi Tag và Text)
        let anchorInputHtml = '';
        if (anchorTag === "w:document") {
            anchorInputHtml = `
                <div class="row g-2">
                    <div class="col-4">
                        <input type="text" id="criteria_anchor_tag" class="form-control form-control-sm text-center bg-light" value="w:document" readonly title="Mỏ neo Toàn cục">
                    </div>
                    <div class="col-8">
                        <input type="text" id="criteria_anchor_text" class="form-control form-control-sm bg-light" value="" readonly placeholder="(Không cần chữ nhận diện)">
                    </div>
                </div>
            `;
        } else {
            anchorInputHtml = `
                <div class="row g-2">
                    <div class="col-4">
                        <label class="form-label small text-muted mb-1">Loại thẻ (Tag)</label>
                        <select id="criteria_anchor_tag" class="form-select form-select-sm font-monospace text-primary fw-bold">
                            <option value="w:p" ${anchorTag === 'w:p' ? 'selected' : ''}>w:p (Đoạn chữ)</option>
                            <option value="w:tbl" ${anchorTag === 'w:tbl' ? 'selected' : ''}>w:tbl (Bảng biểu)</option>
                            <option value="w:sdt" ${anchorTag === 'w:sdt' ? 'selected' : ''}>w:sdt (Mục lục/Control)</option>
                            <option value="pic:pic" ${anchorTag === 'pic:pic' || anchorTag === 'image' ? 'selected' : ''}>pic:pic (Hình ảnh)</option>
                            <option value="wps:wsp" ${anchorTag === 'wps:wsp' || anchorTag === 'shape' ? 'selected' : ''}>wps:wsp (Hình khối)</option>
                            <option value="${anchorTag}" ${!['w:p', 'w:tbl', 'w:sdt', 'pic:pic', 'wps:wsp'].includes(anchorTag) ? 'selected' : 'd-none'}>${anchorTag}</option>
                        </select>
                    </div>
                    <div class="col-8">
                        <label class="form-label small text-muted mb-1">Chữ nhận diện (text_contains)</label>
                        <input type="text" id="criteria_anchor_text" class="form-control form-control-sm" value="${anchorTextVal || ''}" placeholder="Nhập chữ để tìm kiếm...">
                    </div>
                    <div class="col-12 mt-1">
                        <small class="text-secondary" style="font-size:0.7em"><i class="bi bi-info-circle"></i> Mẹo: Bạn có thể sửa trực tiếp hoặc Click vào file bên trái để máy tự lấy thẻ và chữ.</small>
                    </div>
                </div>
            `;
        }

        builderArea.innerHTML = `
            <div class="mb-3 border-bottom pb-3">
                <label class="form-label fw-bold text-primary">1. Tên Tiêu Chí (Criteria Name)</label>
                <input type="text" id="criteria_name" class="form-control fw-bold border-primary mb-3" value="${title}">
                
                <label class="form-label fw-bold text-dark mt-2 mb-0">2. Mỏ neo chính (Global Anchor)</label>
                <div class="bg-white border rounded p-2 mt-1">
                    ${anchorInputHtml}
                </div>
            </div>
            
            <div class="input-group input-group-sm mb-3 shadow-sm">
                <span class="input-group-text bg-white"><i class="bi bi-plus-circle-fill text-success"></i></span>
                <select class="form-select" id="manual_rule_select">
                    <option value="">-- Cấu hình Luật / Thêm Mỏ neo con (Scope) --</option>
                    ${optionsHtml}
                </select>
                <button class="btn btn-outline-success fw-bold" onclick="RubricBuilder.addManualRule()">Thêm</button>
            </div>

            <h6 class="fw-bold border-bottom pb-2"><i class="bi bi-diagram-3"></i> Cấu trúc Luật (Rules Tree):</h6>
            <div id="selected_rules_cart" class="mb-3"></div>
            
            <div class="d-flex justify-content-between mt-3">
                <button class="btn btn-outline-danger" onclick="document.getElementById('rubric-builder-area').innerHTML=''; document.getElementById('rubric-empty-state').classList.remove('d-none');"><i class="bi bi-x"></i> Hủy</button>
                <button class="btn btn-primary fw-bold px-4 shadow" onclick="RubricBuilder.saveCurrentCriteria()"><i class="bi bi-save"></i> LƯU TIÊU CHÍ</button>
            </div>
        `;
        renderCart();
    }

    // Tạo rule obj
    function createRuleObj(label, path, value, matchFlag) {
        const rId = Date.now() + Math.random();
        if (matchFlag === 'SCOPE') {
            return { id: rId, description: `${label}`, scope_locator: path, search_mode: "FORWARD", nested_rules: [], points: 0.0 };
        }
        let rule = {
            id: rId, description: `Kiểm tra ${label}`, property_path: path, expected_value: value,
            match_flag: matchFlag === 'TOLERANT_VALS' || matchFlag === 'TOLERANT_RANGE' ? 'TOLERANT' : matchFlag,
            search_mode: "OFFSET", relative_offset: 0, points: 0.5
        };
        if (matchFlag === 'TOLERANT_RANGE') {
            const v = parseFloat(value) || 0;
            rule.accepted_range = [Math.floor(v * 0.95), Math.ceil(v * 1.05)];
        } else if (matchFlag === 'TOLERANT_VALS') rule.accepted_values = [value];
        return rule;
    }

    function autoDetectProperties(node, nodeText) {
        // [MỚI] NẾU CLICK VÀO BẢNG -> TỰ ĐỘNG XÂY DỰNG CẤU TRÚC LỒNG NHAU (NESTED RULES)
        if (node.type === 'table' || node.tag === 'w:tbl') {
            // 1. Kiểm tra viền bảng chung
            if (node.borders && node.borders.top) {
                currentPendingRules.push(createRuleObj("Viền bảng (Border Top)", "borders.top.style", node.borders.top.style, "STRICT"));
            }

            // 2. Quét qua từng Hàng (Row)
            if (node.children) {
                node.children.forEach((row, rIdx) => {
                    if (row.tag !== 'w:tr' && row.type !== 'table_row') return;

                    let rowScope = createRuleObj(`Chui vào Hàng ${rIdx + 1}`, "children", "", "SCOPE");
                    rowScope.search_mode = 'INDEX';
                    rowScope.scope_index = rIdx;
                    rowScope.nested_rules = [];

                    // 3. Quét qua từng Ô (Cell) trong Hàng
                    if (row.children) {
                        row.children.forEach((cell, cIdx) => {
                            if (cell.tag !== 'w:tc' && cell.type !== 'table_cell') return;

                            let cellScope = createRuleObj(`Chui vào Ô Cột ${cIdx + 1}`, "children", "", "SCOPE");
                            cellScope.search_mode = 'INDEX';
                            cellScope.scope_index = cIdx;
                            cellScope.nested_rules = [];

                            // A. Bóc tách Chữ (Text) bên trong ô
                            let cellText = extractAllText(cell).trim();
                            if (cellText) {
                                let shortText = cellText.length > 20 ? cellText.substring(0, 20) + '...' : cellText;
                                cellScope.nested_rules.push(createRuleObj(`Nội dung chữ: "${shortText}"`, "text", cellText, "FUZZY_TEXT"));
                            }

                            // B. Kiểm tra Gộp Cột (Colspan)
                            if (cell.layout && cell.layout.colspan) {
                                cellScope.nested_rules.push(createRuleObj(`Gộp ${cell.layout.colspan} cột (Colspan)`, "layout.colspan", cell.layout.colspan, "STRICT"));
                            }

                            // C. Kiểm tra Gộp Dòng (Rowspan)
                            if (cell.layout && cell.layout.rowspan) {
                                cellScope.nested_rules.push(createRuleObj(`Gộp dòng dọc (Rowspan = ${cell.layout.rowspan})`, "layout.rowspan", cell.layout.rowspan, "STRICT"));
                            }

                            // D. Kiểm tra Màu nền (Shading)
                            if (cell.layout && cell.layout.shading && cell.layout.shading !== "clear") {
                                cellScope.nested_rules.push(createRuleObj(`Màu nền (Shading: ${cell.layout.shading})`, "layout.shading", cell.layout.shading, "STRICT"));
                            }

                            // Chỉ thêm Ô vào Hàng nếu Ô đó có chứa quy tắc (có chữ hoặc có gộp)
                            if (cellScope.nested_rules.length > 0) {
                                rowScope.nested_rules.push(cellScope);
                            }
                        });
                    }

                    // Chỉ thêm Hàng vào Bảng nếu Hàng đó có chứa Ô hợp lệ
                    if (rowScope.nested_rules.length > 0) {
                        currentPendingRules.push(rowScope);
                    }
                });
            }
            renderCart();
            return; // Bảng đã được xử lý xong, thoát hàm để không bị chạy phần gán text rác ở dưới
        }

        // ===============================================
        // CODE CŨ CHO CÁC KHỐI BÌNH THƯỜNG (PARAGRAPH, TEXT...)
        // ===============================================
        if (nodeText && nodeText.length > 0) {
            currentPendingRules.push(createRuleObj("Nội dung gõ đúng", "", nodeText, "FUZZY_TEXT"));
        }

        if (node.properties && node.properties.pStyle) {
            currentPendingRules.push(createRuleObj(`Style đoạn văn (${node.properties.pStyle})`, `properties.pStyle`, node.properties.pStyle, "STRICT"));
        }

        let props = null;
        let prefix = "";
        if (node.type === 'paragraph' || node.tag === 'w:p') {
            if (node.properties && node.properties.paragraphRunProperties) {
                props = node.properties.paragraphRunProperties;
                prefix = "properties.paragraphRunProperties.";
            }
        } else {
            props = node.properties;
            prefix = "properties.";
        }

        if (props) {
            if (props.bold) currentPendingRules.push(createRuleObj("Chữ In đậm", `${prefix}bold`, true, "STRICT"));
            if (props.italic) currentPendingRules.push(createRuleObj("Chữ In nghiêng", `${prefix}italic`, true, "STRICT"));
            if (props.strike) currentPendingRules.push(createRuleObj("Chữ Gạch ngang", `${prefix}strike`, true, "STRICT"));
            if (props.underline && props.underline !== "none") currentPendingRules.push(createRuleObj(`Chữ Gạch chân (${props.underline})`, `${prefix}underline`, props.underline, "STRICT"));

            if (props.fontSize) {
                if (parseFloat(props.fontSize) > 50) currentPendingRules.push(createRuleObj("Hiệu ứng Drop Cap (Chữ to)", `${prefix}fontSize`, props.fontSize, "TOLERANT_RANGE"));
                else currentPendingRules.push(createRuleObj("Cỡ chữ", `${prefix}fontSize`, props.fontSize, "TOLERANT_RANGE"));
            }

            if (props.color && props.color !== "auto") currentPendingRules.push(createRuleObj("Màu chữ", `${prefix}color`, props.color, "STRICT"));
            if (props.font && props.font.ascii) currentPendingRules.push(createRuleObj("Font chữ", `${prefix}font.ascii`, props.font.ascii, "STRICT"));
            else if (props.resolvedFont) currentPendingRules.push(createRuleObj("Font chữ", `${prefix}resolvedFont`, props.resolvedFont, "STRICT"));

            if (props.shadow) currentPendingRules.push(createRuleObj("Hiệu ứng: Đổ bóng", `${prefix}shadow.blurPt`, props.shadow.blurPt, "PRESENCE_ONLY"));
            if (props.glow) currentPendingRules.push(createRuleObj("Hiệu ứng: Phát sáng", `${prefix}glow.radiusPt`, props.glow.radiusPt, "PRESENCE_ONLY"));
            if (props.outline) currentPendingRules.push(createRuleObj("Hiệu ứng: Viền chữ", `${prefix}outline.widthPt`, props.outline.widthPt, "PRESENCE_ONLY"));
        }

        if (node.layout) {
            if (node.layout.alignment) currentPendingRules.push(createRuleObj("Căn lề", "layout.alignment", node.layout.alignment, "TOLERANT_VALS"));

            if (node.layout.tabs && node.layout.tabs.length > 0) {
                node.layout.tabs.forEach((tab, idx) => {
                    if (tab.align) currentPendingRules.push(createRuleObj(`Tab ${idx + 1} (Căn ${tab.align})`, `layout.tabs.${idx}.align`, tab.align, "STRICT"));
                    if (tab.leader) currentPendingRules.push(createRuleObj(`Tab ${idx + 1} (Dấu ${tab.leader})`, `layout.tabs.${idx}.leader`, tab.leader, "STRICT"));
                });
            }

            if (node.layout.spacing) {
                if (node.layout.spacing.linePt) currentPendingRules.push(createRuleObj("Khoảng cách Dòng (Line Spacing)", "layout.spacing.linePt", node.layout.spacing.linePt, "TOLERANT_RANGE"));
                if (node.layout.spacing.beforePt) currentPendingRules.push(createRuleObj("Cách đoạn trên (Space Before)", "layout.spacing.beforePt", node.layout.spacing.beforePt, "TOLERANT_RANGE"));
                if (node.layout.spacing.afterPt) currentPendingRules.push(createRuleObj("Cách đoạn dưới (Space After)", "layout.spacing.afterPt", node.layout.spacing.afterPt, "TOLERANT_RANGE"));
            }
        }

        if (node.list && node.list.format) {
            currentPendingRules.push(createRuleObj(`Định dạng Danh sách (${node.list.format})`, `list.format`, node.list.format, "STRICT"));
        }

        renderCart();
    }

    function addManualRule() {
        const sel = document.getElementById('manual_rule_select');
        if (sel.value === "") return;
        const tpl = RULE_TEMPLATES[sel.value];
        currentPendingRules.push(createRuleObj(tpl.label, tpl.path, tpl.val || "", tpl.type));
        renderCart();
    }

    function addSubRule(parentId) {
        const sel = document.getElementById('manual_rule_select');
        if (sel.value === "") return alert("Vui lòng chọn 1 thuộc tính ở hộp dropdown phía trên trước khi bấm 'Luật con'!");
        const tpl = RULE_TEMPLATES[sel.value];

        function find(rules, id) {
            for (let r of rules) {
                if (r.id == id) return r;
                if (r.nested_rules) { let found = find(r.nested_rules, id); if (found) return found; }
            }
            return null;
        }

        const parent = find(currentPendingRules, parentId);
        if (parent && parent.nested_rules) {
            parent.nested_rules.push(createRuleObj(tpl.label, tpl.path, tpl.val || "", tpl.type));
            renderCart();
        }
    }

    function autoFillEmptyRulesFromNode(rules, node) {
        for (let r of rules) {
            if (r.nested_rules) {
                autoFillEmptyRulesFromNode(r.nested_rules, node);
            } else if (r.expected_value === "" || r.expected_value === undefined) {
                if (r.match_flag === 'FUZZY_TEXT') r.expected_value = extractAllText(node).trim();
                else if (r.property_path) {
                    const valLocal = getNestedValue(node, r.property_path);
                    if (valLocal !== null && valLocal !== undefined) r.expected_value = valLocal;
                }
            }
        }
    }

    // ==========================================
    // VẼ CÂY UI GIỎ HÀNG
    // ==========================================
    function syncCartData() {
        function syncNodes(rules) {
            rules.forEach(r => {
                const descI = document.querySelector(`.rule-desc[data-id="${r.id}"]`);
                if (descI) r.description = descI.value;
                const ptsI = document.querySelector(`.rule-points[data-id="${r.id}"]`);
                if (ptsI) r.points = parseFloat(ptsI.value);
                const expI = document.querySelector(`.rule-expected[data-id="${r.id}"]`);
                if (expI) r.expected_value = expI.value;
                const offI = document.querySelector(`.rule-offset[data-id="${r.id}"]`);
                if (offI) r.relative_offset = parseInt(offI.value) || 0;
                const tkI = document.querySelector(`.rule-target-key[data-id="${r.id}"]`);
                if (tkI) r.search_target_key = tkI.value;
                const tvI = document.querySelector(`.rule-target-val[data-id="${r.id}"]`);
                if (tvI) r.search_target_value = tvI.value;

                if (r.nested_rules) syncNodes(r.nested_rules);
            });
        }
        syncNodes(currentPendingRules);
    }

    function changeSearchMode(id, mode) {
        syncCartData();
        function find(rules, id) {
            for (let r of rules) {
                if (r.id == id) return r;
                if (r.nested_rules) { let f = find(r.nested_rules, id); if (f) return f; }
            }
            return null;
        }
        const rule = find(currentPendingRules, id);
        if (rule) rule.search_mode = mode;
        renderCart();
    }

    function updateRule(id, field, val) {
        function find(rules, id) {
            for (let r of rules) {
                if (r.id == id) return r;
                if (r.nested_rules) { let f = find(r.nested_rules, id); if (f) return f; }
            }
            return null;
        }
        const rule = find(currentPendingRules, id);
        if (rule) rule[field] = field === 'points' ? parseFloat(val) : val;
    }

    function removeRule(id) {
        function del(rules, id) {
            for (let i = 0; i < rules.length; i++) {
                if (rules[i].id == id) { rules.splice(i, 1); return true; }
                if (rules[i].nested_rules && del(rules[i].nested_rules, id)) return true;
            }
            return false;
        }
        del(currentPendingRules, id);
        renderCart();
    }

    function renderCart() {
        const cartDiv = document.getElementById('selected_rules_cart');
        if (currentPendingRules.length === 0) {
            cartDiv.innerHTML = '<div class="alert alert-secondary text-center small py-2">Chưa có luật nào. Hãy chọn từ danh sách hoặc click vào tài liệu.</div>';
            return;
        }
        cartDiv.innerHTML = generateRulesHTML(currentPendingRules, 0);
    }

    function generateRulesHTML(rules, depth) {
        let html = '';
        let marginLeft = depth * 20;

        rules.forEach((rule) => {
            const isScope = rule.nested_rules !== undefined;
            let valStatus = rule.expected_value === "" ? `<span class="badge bg-warning text-dark">Chờ hút data</span>` : ``;

            if (isScope) {
                let scopeInput = rule.search_mode === 'INDEX'
                    ? `<input type="number" class="form-control form-control-sm text-center font-monospace" value="${rule.scope_index || 0}" onchange="RubricBuilder.updateRule('${rule.id}', 'scope_index', this.value)" title="Index của đối tượng con">`
                    : `<input type="text" class="form-control form-control-sm rule-target-key font-monospace" value="${rule.scope_locator || ''}" onchange="RubricBuilder.updateRule('${rule.id}', 'scope_locator', this.value)" placeholder="Vd: children.0 hoặc w:p">`;

                html += `
                <div class="card mb-2 border-warning shadow-sm" style="margin-left: ${marginLeft}px;">
                    <div class="card-header bg-warning bg-opacity-25 py-1 px-2 d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center gap-2 w-75">
                            <i class="bi bi-box-seam text-warning-emphasis"></i>
                            <input type="text" class="form-control form-control-sm fw-bold border-0 bg-transparent px-0 w-100 rule-desc" 
                                value="${rule.description}" data-id="${rule.id}">
                        </div>
                        <button class="btn btn-sm text-danger p-0" onclick="RubricBuilder.removeRule('${rule.id}')" title="Xóa nhóm"><i class="bi bi-trash"></i></button>
                    </div>
                    <div class="card-body py-2 px-2 bg-light">
                        <div class="d-flex gap-2 align-items-center mb-2">
                            <select class="form-select form-select-sm w-auto bg-white text-secondary" onchange="RubricBuilder.changeSearchMode('${rule.id}', this.value)">
                                <option value="FORWARD" ${rule.search_mode === 'FORWARD' || !rule.search_mode ? 'selected' : ''}>Tìm kiếm theo Path/Tag</option>
                                <option value="INDEX" ${rule.search_mode === 'INDEX' ? 'selected' : ''}>Đi vào Index con (Mảng)</option>
                            </select>
                            ${scopeInput}
                            <button class="btn btn-sm btn-success text-nowrap py-0" onclick="RubricBuilder.addSubRule('${rule.id}')"><i class="bi bi-plus"></i> Luật con</button>
                        </div>
                        <div class="mt-2 border-start border-2 border-warning ps-2">
                            ${generateRulesHTML(rule.nested_rules, depth + 1)}
                        </div>
                    </div>
                </div>`;
            } else {
                let searchConfigHtml = '';
                if (rule.search_mode === 'FORWARD') {
                    searchConfigHtml = `
                        <div class="input-group input-group-sm mt-2">
                            <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Key cần tìm</span>
                            <input type="text" class="form-control rule-target-key font-monospace" value="${rule.search_target_key || 'type'}" data-id="${rule.id}">
                            <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Value cần tìm</span>
                            <input type="text" class="form-control rule-target-val font-monospace" value="${rule.search_target_value || 'image'}" data-id="${rule.id}">
                        </div>
                    `;
                } else {
                    searchConfigHtml = `
                        <div class="input-group input-group-sm mt-2" style="width: 140px;" title="0: Tại chỗ | 1: Dòng dưới">
                            <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Lệch dòng</span>
                            <input type="number" class="form-control rule-offset text-center" value="${rule.relative_offset || 0}" data-id="${rule.id}">
                        </div>
                    `;
                }

                if (rule.match_flag === 'TOLERANT') {
                    const numVal = parseFloat(rule.expected_value);
                    if (!isNaN(numVal)) {
                        const min = rule.accepted_range ? rule.accepted_range[0] : Math.floor(numVal * 0.95);
                        const max = rule.accepted_range ? rule.accepted_range[1] : Math.ceil(numVal * 1.05);
                        searchConfigHtml += `
                            <div class="input-group input-group-sm mt-2 w-75">
                                <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Cho phép từ</span>
                                <input type="number" class="form-control rule-min text-center" value="${min}" data-id="${rule.id}">
                                <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Đến</span>
                                <input type="number" class="form-control rule-max text-center" value="${max}" data-id="${rule.id}">
                            </div>`;
                    } else {
                        const vals = rule.accepted_values ? rule.accepted_values.join(', ') : rule.expected_value;
                        searchConfigHtml += `
                            <div class="input-group input-group-sm mt-2">
                                <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Nhiều lựa chọn (cách phẩy)</span>
                                <input type="text" class="form-control rule-vals" value="${vals}" data-id="${rule.id}">
                            </div>`;
                    }
                } else if (rule.match_flag === 'FUZZY_TEXT') {
                    searchConfigHtml += `
                        <div class="input-group input-group-sm mt-2 w-75">
                            <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Tỷ lệ đúng yêu cầu:</span>
                            <input type="number" class="form-control text-center rule-ratio" value="${rule.required_ratio || 0.8}" min="0.1" max="1.0" step="0.05" data-id="${rule.id}">
                        </div>`;
                }

                html += `
                <div class="card mb-2 border-start border-4 border-primary shadow-sm" style="margin-left: ${marginLeft}px;">
                    <div class="card-body py-2 px-2 bg-white">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <input type="text" class="form-control form-control-sm fw-bold text-dark border-0 bg-transparent px-0 w-50 rule-desc" 
                                value="${rule.description}" data-id="${rule.id}">
                            
                            <div class="d-flex gap-2 align-items-center">
                                <select class="form-select form-select-sm text-secondary bg-light" style="width: 130px; font-size: 0.75em;" onchange="RubricBuilder.changeSearchMode('${rule.id}', this.value)">
                                    <option value="OFFSET" ${rule.search_mode !== 'FORWARD' ? 'selected' : ''}>Quét tại chỗ</option>
                                    <option value="FORWARD" ${rule.search_mode === 'FORWARD' ? 'selected' : ''}>Quét xuống dưới</option>
                                </select>
                                <input type="number" class="form-control form-control-sm text-center border-primary rule-points" style="width: 55px;" value="${rule.points}" step="0.25" data-id="${rule.id}" title="Điểm số">
                                <button class="btn btn-sm text-danger p-1" onclick="RubricBuilder.removeRule('${rule.id}')"><i class="bi bi-trash"></i></button>
                            </div>
                        </div>

                        <div class="d-flex flex-column gap-1">
                            <code class="text-secondary" style="font-size:0.7em">Path: ${rule.property_path || '(Chỉ check Text)'} | Flag: ${rule.match_flag}</code>
                            <div class="input-group input-group-sm mt-1">
                                <span class="input-group-text bg-light text-muted" style="font-size:0.7em">Yêu cầu = </span>
                                <input type="text" class="form-control rule-expected" value="${rule.expected_value}" data-id="${rule.id}">
                            </div>
                            ${searchConfigHtml}
                            <div class="mt-1">${valStatus}</div>
                        </div>
                    </div>
                </div>`;
            }
        });
        return html;
    }

    // ==========================================
    // LƯU DỮ LIỆU ĐỂ EXPORT
    // ==========================================
    function saveCurrentCriteria() {
        syncCartData();
        if (currentPendingRules.length === 0) return alert("Cần ít nhất 1 luật!");

        const name = document.getElementById('criteria_name').value;
        const anchorTag = document.getElementById('criteria_anchor_tag').value.trim();
        const anchorTextVal = document.getElementById('criteria_anchor_text').value.trim();

        // 1. Lưu Mỏ Neo (Dùng Tag & Text rành mạch)
        let anchor = { tag: anchorTag };
        if (anchorTextVal !== "") anchor.text_contains = anchorTextVal;

        let totalPoints = 0;

        function cleanUpRules(rulesArray) {
            let cleaned = [];
            for (let r of rulesArray) {
                let newR = { ...r };
                delete newR.id;

                if (!newR.nested_rules) totalPoints += parseFloat(newR.points || 0);

                if (newR.expected_value === "true") newR.expected_value = true;
                else if (newR.expected_value === "false") newR.expected_value = false;
                else if (!isNaN(parseFloat(newR.expected_value)) && newR.expected_value !== "") newR.expected_value = parseFloat(newR.expected_value);

                // Dọn dẹp theo logic
                if (newR.nested_rules) {
                    if (newR.search_mode === "INDEX") {
                        newR.scope_index = parseInt(newR.scope_index) || 0;
                        delete newR.scope_locator;
                    }
                    newR.nested_rules = cleanUpRules(newR.nested_rules);
                } else {
                    if (newR.search_mode === "FORWARD") {
                        delete newR.relative_offset;
                    } else {
                        delete newR.search_target_key;
                        delete r.search_target_value;
                        delete newR.search_mode;
                    }
                }

                if (newR.match_flag === 'TOLERANT_RANGE') {
                    const minI = document.querySelector(`.rule-min[data-id="${r.id}"]`);
                    const maxI = document.querySelector(`.rule-max[data-id="${r.id}"]`);
                    newR.match_flag = "TOLERANT";
                    if (minI && maxI) newR.accepted_range = [parseFloat(minI.value), parseFloat(maxI.value)];
                } else if (newR.match_flag === 'TOLERANT_VALS') {
                    const valI = document.querySelector(`.rule-vals[data-id="${r.id}"]`);
                    newR.match_flag = "TOLERANT";
                    if (valI) newR.accepted_values = valI.value.split(',').map(v => v.trim());
                } else if (newR.match_flag === 'FUZZY_TEXT') {
                    const ratioI = document.querySelector(`.rule-ratio[data-id="${r.id}"]`);
                    if (ratioI) newR.required_ratio = parseFloat(ratioI.value);
                }

                cleaned.push(newR);
            }
            return cleaned;
        }

        const finalRules = cleanUpRules(currentPendingRules);

        globalRubric.push({
            criteria_name: name,
            allocated_points: totalPoints,
            anchor_locator: anchor,
            rules: finalRules
        });

        if (document.getElementById('btnSaveRubric')) document.getElementById('btnSaveRubric').disabled = false;
        document.getElementById('rubric-builder-area').innerHTML = '';
        document.getElementById('rubric-empty-state').classList.remove('d-none');
        if (typeof showToast === 'function') showToast(`Đã lưu tiêu chí: ${name}`, "success");
    }

    // Modal & Export
    function showRubricModal() {
        // 1. Chuẩn bị nội dung bảng
        let tbodyHtml = '';
        globalRubric.forEach((crit, index) => {
            let anchorDesc = crit.anchor_locator.tag === 'w:document' ? 'Toàn trang' :
                `<span class="text-primary font-monospace">${crit.anchor_locator.tag}</span>` +
                (crit.anchor_locator.text_contains ? `<br>Chữ: "${crit.anchor_locator.text_contains}"` : '');

            tbodyHtml += `
                <tr>
                    <td class="fw-bold text-primary">${crit.criteria_name}</td>
                    <td><span class="badge bg-light border text-dark text-wrap text-start lh-base">${anchorDesc}</span></td>
                    <td class="text-center fw-bold text-success">${crit.allocated_points}</td>
                    <td class="text-center">${crit.rules.length}</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-outline-danger" onclick="RubricBuilder.deleteCriteria(${index})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        });

        if (globalRubric.length === 0) tbodyHtml = `<tr><td colspan="5" class="text-center text-muted py-4">Chưa có tiêu chí nào.</td></tr>`;

        // 2. Kiểm tra xem Modal đã tồn tại trong DOM chưa để tránh lỗi chồng Backdrop (màn hình đen)
        let modalEl = document.getElementById('rubricViewModal');

        if (!modalEl) {
            // Nếu chưa có thì tạo mới hoàn toàn
            const modalHtml = `
            <div class="modal fade" id="rubricViewModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title fw-bold"><i class="bi bi-card-checklist"></i> Danh sách Tiêu chí Rubric (Word)</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-0">
                            <table class="table table-hover mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>Tên tiêu chí</th>
                                        <th>Mốc định vị (Anchor)</th>
                                        <th class="text-center">Điểm</th>
                                        <th class="text-center">Luật</th>
                                        <th class="text-center">Xóa</th>
                                    </tr>
                                </thead>
                                <tbody id="rubricModalTbody">${tbodyHtml}</tbody>
                            </table>
                        </div>
                        <div class="modal-footer bg-light">
                            <button type="button" class="btn btn-secondary fw-bold" data-bs-dismiss="modal">Đóng</button>
                            <button type="button" class="btn btn-success fw-bold" onclick="RubricBuilder.downloadRubric()"><i class="bi bi-download"></i> Tải File JSON</button>
                        </div>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modalEl = document.getElementById('rubricViewModal');
            new bootstrap.Modal(modalEl).show();
        } else {
            // Nếu đã có rồi thì chỉ cập nhật lại ruột (tbody) để màn hình không bị giật hoặc đen
            document.getElementById('rubricModalTbody').innerHTML = tbodyHtml;

            // Đảm bảo modal hiện lên nếu nó đang bị ẩn
            let bsModal = bootstrap.Modal.getInstance(modalEl);
            if (!bsModal) bsModal = new bootstrap.Modal(modalEl);
            bsModal.show();
        }
    }

    function deleteCriteria(index) {
        if (confirm("Bạn có chắc chắn muốn xóa tiêu chí này?")) {
            globalRubric.splice(index, 1);
            showRubricModal();
            if (globalRubric.length === 0 && document.getElementById('btnSaveRubric')) document.getElementById('btnSaveRubric').disabled = true;
        }
    }
    async function downloadRubric() {
        if (globalRubric.length === 0) {
            return alert("Rubric đang trống! Vui lòng tạo ít nhất 1 tiêu chí.");
        }

        const rubricBlob = new Blob([JSON.stringify(globalRubric, null, 4)], { type: "application/json" });
        const url = URL.createObjectURL(rubricBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "rubric_word_export.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        if (typeof showToast === 'function') showToast("Đã tải JSON Rubric thành công!", "success");
    }

    async function exportRubric() {
        const fileInput = document.getElementById('fileInput');

        if (!fileInput || fileInput.files.length === 0) {
            return showToast(
                "Không tìm thấy file gốc. Vui lòng tải file lên trước!",
                "warning"
            );
        }

        if (globalRubric.length === 0) {
            return showToast(
                "Rubric đang trống! Vui lòng tạo ít nhất 1 tiêu chí.",
                "warning"
            );
        }

        const originalFile = fileInput.files[0];

        // Tạo file JSON
        const rubricBlob = new Blob(
            [JSON.stringify(globalRubric, null, 4)],
            { type: "application/json" }
        );

        const rubricFile = new File(
            [rubricBlob],
            "rubric_graduation_project.json",
            { type: "application/json" }
        );

        let rubricName = "";

        while (true) {

            rubricName = prompt(
                "Nhập tên rubric:",
                rubricName
            );

            // Người dùng bấm cancel
            if (rubricName === null) {
                return;
            }

            rubricName = rubricName.trim();

            if (rubricName === "") {
                showToast(
                    "Tên rubric không được để trống!",
                    "warning"
                );
                continue;
            }

            try {

                const formData = new FormData();

                formData.append("name", rubricName);
                formData.append("originalFile", originalFile);
                formData.append("rubricFile", rubricFile);

                const response = await fetch(
                    "/api/save-rubric",
                    {
                        method: "POST",
                        body: formData
                    }
                );

                const result = await response.json();

                // Thành công
                if (response.ok && result.status === "success") {

                    showToast(
                        "Lưu rubric thành công!",
                        "success"
                    );

                    console.log(result);
                    return;
                }

                // Trùng tên
                if (result.status === "error" &&
                    result.code === "EXISTS_NAME") {

                    showToast(
                        "Tên rubric đã tồn tại. Vui lòng nhập tên khác!",
                        "warning"
                    );

                    continue;
                }

                // Lỗi khác
                throw new Error(
                    result.message || "Upload thất bại"
                );

            } catch (error) {

                console.error(error);

                showToast(
                    error.message || "Có lỗi xảy ra khi gửi dữ liệu!",
                    "danger"
                );

                return;
            }
        }
    }

    // EXPORT PUBLIC API
    return {
        init, handleNodeClick, addGlobalPageSetup, addGlobalExistenceCheck,
        createEmptyCriteria, addManualRule, addSubRule, updateRule, changeSearchMode,
        removeRule, saveCurrentCriteria, showRubricModal, deleteCriteria, exportRubric, downloadRubric,
        getRubric: () => globalRubric
    };
})();