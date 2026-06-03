/**
 * POWERPOINT RUBRIC BUILDER MODULE - MASTER & SLIDE DEEP INSPECTOR
 * Tự động quét sâu đa tầng (Slide/Master > Element > Sub-Element) và trích xuất định dạng.
 */

const PPTRubricBuilder = (function () {
    let globalRubric = [];
    let currentPendingGroups = [];
    let AST = null;
    let currentNodePath = null;

    // Danh sách "Tự chọn" (Presets) phù hợp với PowerPoint
    const PPTX_PRESETS = [
        { label: "🔤 Font chữ", path: "style.font_name", type: "VERIFY_PROPERTY", match: "EXACT" },
        { label: "📏 Cỡ chữ (Font Size)", path: "style.sz", type: "VERIFY_PROPERTY", match: "EXACT" },
        { label: "Chữ In đậm", path: "style.b", type: "VERIFY_PROPERTY", match: "EXACT", val: "1" },
        { label: "Chữ In nghiêng", path: "style.i", type: "VERIFY_PROPERTY", match: "EXACT", val: "1" },
        { label: "🎨 Màu nền đối tượng (Fill Color)", path: "style.fill.color", type: "VERIFY_PROPERTY", match: "EXACT" },
        { label: "✨ Hiệu ứng đồ họa (Glow, Reflection...)", path: "style.effects", type: "VERIFY_PROPERTY", match: "CONTAINS" },
        { label: "🎬 Hiệu ứng xuất hiện (Animation)", path: "properties.animations.0.presetClass", type: "VERIFY_PROPERTY", match: "EXACT", val: "entr" },
        { label: "🔗 Đường dẫn liên kết (Hyperlink)", path: "properties.hyperlink_target", type: "VERIFY_PROPERTY", match: "CONTAINS" },
        { label: "📐 Cấu trúc hình khối (Geometry Type)", path: "properties.geometry_type", type: "VERIFY_PROPERTY", match: "EXACT" },
        { label: "Nội dung Text (Mở rộng)", path: "text", type: "VERIFY_PROPERTY", match: "CONTAINS" }
    ];

    function init(parsedAST) {
        AST = parsedAST;
        globalRubric = [];
    }

    // ==========================================
    // UTILS TRUY XUẤT DỮ LIỆU
    // ==========================================
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

    function getSlideTitle(slideNode) {
        if (!slideNode) return "Slide";
        let titleNode = slideNode.children?.find(c => c.properties?.is_placeholder && (c.properties.placeholder.type === 'title' || c.properties.placeholder.type === 'ctrTitle'));
        if (titleNode) return extractAllText(titleNode).trim().substring(0, 40) || "Slide Không Tiêu Đề";
        return `Slide ${slideNode.properties?.slide_index || ''}`;
    }

    function getParentSlide(path) {
        let keys = path.split('.');
        if (keys.length >= 2 && keys[0] === 'children') {
            let idx = parseInt(keys[1]);
            return AST.children[idx];
        }
        return null;
    }

    function getSpatialZone(layout) {
        if (!layout) return "CENTER_X_CENTER_Y";
        let x = parseFloat(layout.x || 0);
        let y = parseFloat(layout.y || 0);
        let cx = parseFloat(layout.cx || 0);
        let cy = parseFloat(layout.cy || 0);

        let centerX = x + (cx / 2);
        let centerY = y + (cy / 2);

        const SLIDE_W = 12192000;
        const SLIDE_H = 6858000;

        let zones = [];
        if (centerX < SLIDE_W * 0.33) zones.push("LEFT");
        else if (centerX > SLIDE_W * 0.66) zones.push("RIGHT");
        else zones.push("CENTER_X");

        if (centerY < SLIDE_H * 0.33) zones.push("TOP");
        else if (centerY > SLIDE_H * 0.66) zones.push("BOTTOM");
        else zones.push("CENTER_Y");

        return zones.join("_");
    }

    // ==========================================
    // CẤU TRÚC ĐỐI TƯỢNG (FACTORY)
    // ==========================================
    function createRuleObj(desc, path, value, action = "VERIFY_PROPERTY", match = "EXACT") {
        return {
            id: 'rule_' + Date.now() + Math.random().toString().substring(2, 6),
            description: desc,
            property_to_check: path,
            expected_value: value,
            action: action,
            match_type: match,
            points: 0.25
        };
    }

    function createRuleGroup(name, anchor, rules = []) {
        return {
            id: 'group_' + Date.now() + Math.random().toString().substring(2, 6),
            criteria_name: name,
            allocated_points: 0,
            anchor_locator: anchor,
            rules: rules,
            sub_criteria: []
        };
    }

    // ==========================================
    // CÁC HÀM PRESETS (GIAO DIỆN)
    // ==========================================
    function presetSlideCount() {
        let expectedCount = AST.properties?.app_properties?.Slides || 4;
        let group = createRuleGroup("Yêu cầu số lượng Slide toàn bài", { type: "presentation", tag: "p:presentation" }, [
            createRuleObj("Tổng số lượng Slide", "properties.app_properties.Slides", parseInt(expectedCount), "VERIFY_PROPERTY", "EXACT")
        ]);
        group.rules[0].points = 1.0;
        currentPendingGroups = [group];
        renderBuilderArea("Yêu cầu số lượng Slide", "global", "");
    }

    function presetTransitionCheck() {
        let group = createRuleGroup("Hiệu ứng chuyển trang", { type: "slide", tag: "p:sld" }, [
            createRuleObj("Loại Transition", "properties.effect_type", "p:circle", "VERIFY_PROPERTY", "CONTAINS")
        ]);
        group.rules[0].points = 1.0;
        currentPendingGroups = [group];
        renderBuilderArea("Hiệu ứng chuyển Slide (Transition)", "global", "");
    }

    function presetActionButtons() {
        let group = createRuleGroup("Cấu hình nút điều hướng", { type: "presentation", tag: "p:presentation" }, [
            {
                id: 'rule_' + Date.now(),
                description: "Số lượng nút điều hướng",
                action: "VERIFY_COUNT",
                property_to_check: "children",
                expected_count: 3,
                points: 1.5
            }
        ]);
        currentPendingGroups = [group];
        renderBuilderArea("Cấu hình Action Buttons", "global", "");
    }

    function presetMatrixLayout() {
        let group = createRuleGroup("Ma trận bố cục không gian", { type: "slide", tag: "p:sld" }, [
            {
                id: 'rule_' + Date.now(),
                description: "Kiểm tra ma trận",
                action: "VERIFY_MATRIX_LAYOUT",
                expected_matrix: "[[1], [2, 3]]",
                items_definition: {
                    "1": { "type": "shape", "text_contains": "Tiêu đề" },
                    "2": { "type": "graphic_frame", "properties": { "frame_type": "smartart" } }
                },
                points: 2.0
            }
        ]);
        currentPendingGroups = [group];
        renderBuilderArea("Kiểm tra Ma trận Bố cục", "slide", "");
        if (typeof showToast === 'function') showToast("MẸO: Click vào các khối con để gán ID ma trận!", "info");
    }

    function createEmptyCriteria() {
        currentPendingGroups = [];
        currentNodePath = null;
        renderBuilderArea("Tiêu chí Tự chọn", "slide", "");
    }

    // ==========================================
    // MÁY QUÉT SÂU (DEEP SCANNERS)
    // ==========================================
    function parseTextRunsDeep(node, relPath, targetRules) {
        if (node.type === 'text_run') {
            let txt = node.text?.trim();
            if (txt) {
                targetRules.push(createRuleObj(`Nội dung chữ: "${txt.substring(0, 15)}..."`, `${relPath}.text`, txt, "VERIFY_PROPERTY", "CONTAINS"));
            }
            let s = node.style || {};
            if (s.font_name) targetRules.push(createRuleObj(`Font chữ: ${s.font_name}`, `${relPath}.style.font_name`, s.font_name));
            if (s.sz) targetRules.push(createRuleObj(`Cỡ chữ: ${parseInt(s.sz) / 100}pt`, `${relPath}.style.sz`, s.sz));
            if (s.b === '1' || s.b === 1) targetRules.push(createRuleObj(`Định dạng In đậm`, `${relPath}.style.b`, "1"));
            if (s.i === '1' || s.i === 1) targetRules.push(createRuleObj(`Định dạng In nghiêng`, `${relPath}.style.i`, "1"));
            if (s.u && s.u !== 'none') targetRules.push(createRuleObj(`Định dạng Gạch chân`, `${relPath}.style.u`, s.u));
            if (s.fill?.color) targetRules.push(createRuleObj(`Màu chữ (Hex): ${s.fill.color}`, `${relPath}.style.fill.color`, s.fill.color));

            if (s.effects && s.effects.length > 0) {
                targetRules.push(createRuleObj(`Hiệu ứng chữ: ${s.effects.join(',')}`, `${relPath}.style.effects`, s.effects.join(','), "VERIFY_PROPERTY", "CONTAINS"));
            }
        }
        if (node.children) {
            node.children.forEach((c, idx) => {
                let currentPath = relPath ? `${relPath}.children.${idx}` : `children.${idx}`;
                parseTextRunsDeep(c, currentPath, targetRules);
            });
        }
    }

    function scanInteractions(node, rules) {
        let p = node.properties || {};
        if (p.animations?.length > 0) {
            let anim = p.animations[0];
            rules.push(createRuleObj(`Hiệu ứng Animation (${anim.presetClass || 'entr'})`, `properties.animations.0.presetClass`, anim.presetClass || 'entr'));
        }
        if (p.is_action_button || p.click_action) {
            let action = p.click_action?.action || "unknown";
            rules.push(createRuleObj(`Hành động Click: ${action.split('?jump=')[1] || 'Link'}`, `properties.click_action.action`, action, "VERIFY_PROPERTY", "CONTAINS"));
        }
    }

    // ==========================================
    // SỰ KIỆN CLICK TỪ TÀI LIỆU
    // ==========================================
    function handleNodeClick(astPath) {
        currentNodePath = astPath;
        const node = getNodeByPath(astPath);
        if (!node) return;
        currentSelectedNode = node;

        const builderArea = document.getElementById('rubric-builder-area');

        if (!builderArea.classList.contains('d-none') && currentPendingGroups.length > 0) {
            let firstRule = currentPendingGroups[0].rules[0];
            if (firstRule && firstRule.action === "VERIFY_MATRIX_LAYOUT") {
                let itemId = prompt("Nhập số định danh (ID) cho khối này trong lưới ma trận:");
                if (!itemId) return;

                let nodeText = extractAllText(node).trim();
                firstRule.items_definition[itemId] = {
                    type: node.type,
                    text_contains: nodeText.length > 0 ? nodeText.substring(0, 15) : undefined,
                    properties: node.properties?.is_placeholder ? { is_placeholder: true } : undefined
                };
                renderCart();
                return;
            }
        }

        currentPendingGroups = [];
        let rootNode = null;
        let rootType = "";
        let parts = astPath.split('.');
        while (parts.length > 0) {
            let n = getNodeByPath(parts.join('.'));
            if (n?.type === 'slide') { rootNode = n; rootType = 'slide'; break; }
            if (n?.type === 'slide_master') { rootNode = n; rootType = 'slide_master'; break; }
            parts.pop(); parts.pop();
        }

        if (!rootNode) return;

        let mainGroup = null;
        let criteriaTitle = "";

        if (rootType === 'slide_master') {
            criteriaTitle = "Định dạng Slide Master";
            mainGroup = createRuleGroup(criteriaTitle, { type: "slide_master", tag: "p:sldMaster" });

            if (AST.properties?.app_properties?.Template) {
                mainGroup.rules.push(createRuleObj("Sử dụng đúng Theme", "properties.app_properties.Template", AST.properties.app_properties.Template));
            }

            let ts = rootNode.properties?.text_styles || {};
            ["titleStyle", "bodyStyle", "otherStyle"].forEach(style => {
                for (let i = 1; i <= 5; i++) {
                    let lvl = ts[style]?.[`lvl${i}pPr`] || (i === 1 ? ts[style] : null);
                    if (lvl) {
                        let styleName = style === "titleStyle" ? "Tiêu đề" : (style === "bodyStyle" ? "Nội dung" : "Khác");
                        let subGroup = createRuleGroup(`${styleName} (Cấp ${i})`, { type: "master_style", style_type: style, level: i });

                        if (lvl.font_name && !lvl.font_name.startsWith("+")) {
                            let r = createRuleObj("Kiểm tra Font chữ", `properties.text_styles.${style}.lvl${i}pPr.font_name`, lvl.font_name);
                            r.level = i; subGroup.rules.push(r);
                        }
                        if (lvl.sz) {
                            let r = createRuleObj("Kiểm tra Cỡ chữ", `properties.text_styles.${style}.lvl${i}pPr.sz`, lvl.sz);
                            r.level = i; subGroup.rules.push(r);
                        }
                        if (subGroup.rules.length > 0) mainGroup.sub_criteria.push(subGroup);
                    }
                }
            });
        }
        else if (rootType === 'slide') {
            let slideTitleStr = getSlideTitle(rootNode);
            criteriaTitle = `Thiết lập cho Slide: ${slideTitleStr}`;
            let mainAnchor = {
                type: "slide",
                tag: "p:sld",
                properties: { slide_index: rootNode.properties.slide_index },
                text_contains: slideTitleStr.substring(0, 15)
            };
            mainGroup = createRuleGroup(criteriaTitle, mainAnchor);

            let trans = rootNode.children?.find(c => c.type === 'transition');
            if (trans) {
                mainGroup.rules.push(createRuleObj("Loại hiệu ứng chuyển trang", "properties.effect_type", trans.properties.effect_type));
                let dur = trans.attributes?.['{http://schemas.microsoft.com/office/powerpoint/2010/main}dur'];
                if (dur) mainGroup.rules.push(createRuleObj("Thời gian chuyển trang (Duration)", "attributes.{http://schemas.microsoft.com/office/powerpoint/2010/main}dur", dur));
            }
        }

        rootNode.children?.forEach((child, cIdx) => {
            if (child.type === 'transition') return;

            let childText = extractAllText(child).trim();
            let childLabel = childText ? `Khối: "${childText.substring(0, 20)}..."` : `Đối tượng: ${child.type}`;

            let childLocator = { type: child.type, tag: child.tag };
            if (childText) childLocator.text_contains = childText.substring(0, 15);

            if (child.properties?.is_placeholder) {
                if (!childText) {
                    childLocator.properties = childLocator.properties || {};
                    childLocator.properties.placeholder = { type: child.properties.placeholder.type };
                }
            }
            if (child.properties?.is_action_button) {
                childLocator.properties = childLocator.properties || {};
                childLocator.properties.is_action_button = true;
            }

            let subGroup = createRuleGroup(childLabel, childLocator);

            if (child.layout) {
                let zone = getSpatialZone(child.layout);
                subGroup.rules.push(createRuleObj(`Vị trí bố cục tự động (${zone})`, "layout", zone, "VERIFY_LAYOUT"));
            }

            if (child.type === 'shape') {
                if (child.properties?.geometry_type) {
                    subGroup.rules.push(createRuleObj("Cấu trúc hình khối (Geometry)", "properties.geometry_type", child.properties.geometry_type));
                }
                if (child.style?.fill?.color) {
                    subGroup.rules.push(createRuleObj("Màu nền đối tượng (Fill Color)", "style.fill.color", child.style.fill.color));
                }

                parseTextRunsDeep(child, "", subGroup.rules);
                scanInteractions(child, subGroup.rules);
            }
            else if (child.type === 'picture') {
                subGroup.rules.push(createRuleObj("Xác minh chèn Hình ảnh vào slide", "type", "picture", "VERIFY_PROPERTY"));
                if (child.properties?.filename) {
                    subGroup.rules.push(createRuleObj("Tên file ảnh", "properties.filename", child.properties.filename, "VERIFY_PROPERTY", "CONTAINS"));
                }
            }
            else if (child.type === 'graphic_frame') {
                let fType = child.properties?.frame_type;
                subGroup.rules.push(createRuleObj("Loại đối tượng đồ họa", "properties.frame_type", fType));

                if (fType === 'table' && child.children?.[0]) {
                    let tbl = child.children[0];
                    subGroup.rules.push(createRuleObj("Số cột của bảng", "children.0.properties.cols_count", tbl.properties.cols_count));

                    tbl.children?.forEach((row, rIdx) => {
                        row.children?.forEach((cell, cIdx) => {
                            let cellText = extractAllText(cell).trim();
                            if (cellText) {
                                let cellGroup = createRuleGroup(`Ô [R${rIdx + 1}-C${cIdx + 1}]`, { type: "table_cell", tag: "a:tc", text_contains: cellText.substring(0, 10) });
                                parseTextRunsDeep(cell, "", cellGroup.rules);
                                if (cell.attributes?.gridSpan) cellGroup.rules.push(createRuleObj("Gộp cột (Colspan)", "attributes.gridSpan", cell.attributes.gridSpan));
                                subGroup.sub_criteria.push(cellGroup);
                            }
                        });
                    });
                }
                else if (fType === 'smartart' && child.children?.[0]) {
                    let dm = child.children[0];
                    dm.children?.forEach((pt, pIdx) => {
                        if (pt.type === 'smartart_node') {
                            let ptText = extractAllText(pt).trim();
                            if (ptText) {
                                let ptGroup = createRuleGroup("Node SmartArt", { type: "smartart_node", tag: "dgm:pt", text_contains: ptText.substring(0, 10) });
                                parseTextRunsDeep(pt, "", ptGroup.rules);
                                subGroup.sub_criteria.push(ptGroup);
                            }
                        }
                    });
                }
                else if (fType === 'chart' && child.children?.[0]) {
                    let chartType = child.children[0].properties?.chart_type;
                    if (chartType) subGroup.rules.push(createRuleObj(`Loại biểu đồ (${chartType})`, `children.0.properties.chart_type`, chartType));
                }
            }

            if (child.properties?.is_placeholder) {
                let ph = child.properties.placeholder?.type;
                if (['ftr', 'dt', 'sldNum'].includes(ph)) {
                    subGroup.rules.push(createRuleObj(`Định dạng khối tự động: ${ph}`, "properties.placeholder.type", ph));
                }
            }

            if (subGroup.rules.length > 0 || subGroup.sub_criteria.length > 0) {
                mainGroup.sub_criteria.push(subGroup);
            }
        });

        currentPendingGroups.push(mainGroup);
        autoDistributePoints(currentPendingGroups[0], 2.0);
        renderBuilderArea(mainGroup.criteria_name, rootType, "");
    }

    // ==========================================
    // RENDER GIAO DIỆN (UI CỘT PHẢI)
    // ==========================================
    function renderBuilderArea(title, anchorTag, anchorTextVal) {
        document.getElementById('rubric-empty-state').classList.add('d-none');
        const builderArea = document.getElementById('rubric-builder-area');
        builderArea.classList.remove('d-none');

        let optionsHtml = PPTX_PRESETS.map((tpl, i) => `<option value="${i}">${tpl.label}</option>`).join('');

        builderArea.innerHTML = `
            <div class="mb-3 border-bottom pb-3">
                <label class="form-label fw-bold text-success">📌 1. Tên Nhóm Tiêu Chí</label>
                <input type="text" id="criteria_name" class="form-control fw-bold border-success mb-3" value="${title}" onchange="if(PPTRubricBuilder.currentPendingGroups[0]) PPTRubricBuilder.currentPendingGroups[0].criteria_name = this.value">
                <small class="text-muted"><i class="bi bi-shield-check text-success"></i> Hệ thống tự động khóa định vị (Anchor) vào Slide hoặc Master tùy vùng click.</small>
            </div>
            
            <div class="input-group input-group-sm mb-3 shadow-sm">
                <span class="input-group-text bg-white"><i class="bi bi-plus-circle-fill text-success"></i></span>
                <select class="form-select" id="pptx_rule_select">
                    <option value="">-- Bổ sung thêm Luật kiểm tra thủ công --</option>
                    ${optionsHtml}
                </select>
                <button class="btn btn-outline-success fw-bold" onclick="PPTRubricBuilder.addManualRule()">Thêm vào Gốc</button>
            </div>

            <h6 class="fw-bold border-bottom pb-2"><i class="bi bi-diagram-3"></i> Cấu trúc Luật Đa Tầng (Rules Tree):</h6>
            <div id="selected_rules_cart" class="mb-3" style="max-height: 500px; overflow-y: auto;"></div>
            
            <div class="d-flex justify-content-between mt-3">
                <button class="btn btn-outline-danger" onclick="document.getElementById('rubric-builder-area').innerHTML=''; document.getElementById('rubric-empty-state').classList.remove('d-none');"><i class="bi bi-x"></i> Hủy bỏ</button>
                <button class="btn btn-success fw-bold px-4 shadow" onclick="PPTRubricBuilder.saveCurrentCriteria()"><i class="bi bi-save"></i> LƯU NHÓM TIÊU CHÍ</button>
            </div>
        `;
        renderCart();
    }

    function addManualRule() {
        const sel = document.getElementById('pptx_rule_select');
        if (sel.value === "" || currentPendingGroups.length === 0) return;
        const tpl = PPTX_PRESETS[sel.value];
        currentPendingGroups[0].rules.push(createRuleObj(tpl.label, tpl.path, tpl.val || "", tpl.type, tpl.match));
        renderCart();
    }

    function addSubRule(groupId) {
        const sel = document.getElementById('pptx_rule_select');
        if (sel.value === "") return alert("Vui lòng chọn 1 thuộc tính định dạng ở hộp Dropdown phía trên trước!");
        const tpl = PPTX_PRESETS[sel.value];

        let targetGroup = null;
        for (let g of currentPendingGroups) {
            if (g.id === groupId) { targetGroup = g; break; }
            if (g.sub_criteria) {
                let sub = g.sub_criteria.find(s => s.id === groupId);
                if (sub) { targetGroup = sub; break; }
                for (let s of g.sub_criteria) {
                    if (s.sub_criteria) {
                        let sub3 = s.sub_criteria.find(s3 => s3.id === groupId);
                        if (sub3) { targetGroup = sub3; break; }
                    }
                }
            }
        }

        if (targetGroup) {
            targetGroup.rules.push(createRuleObj(tpl.label, tpl.path, tpl.val || "", tpl.type, tpl.match));
            autoDistributePoints(currentPendingGroups[0], 2.0);
            renderCart();
        }
    }

    // --- HÀM MỚI: XÓA CẢ MỘT KHỐI (SUB-CRITERIA) ---
    function removeGroup(targetGroupId) {
        function delGrp(groups) {
            for (let i = 0; i < groups.length; i++) {
                if (groups[i].sub_criteria) {
                    const idx = groups[i].sub_criteria.findIndex(g => g.id === targetGroupId);
                    if (idx > -1) {
                        groups[i].sub_criteria.splice(idx, 1);
                        return true;
                    }
                    if (delGrp(groups[i].sub_criteria)) return true;
                }
            }
            return false;
        }

        if (confirm("Bạn có chắc chắn muốn xóa toàn bộ khối này (và các luật con bên trong)?")) {
            delGrp(currentPendingGroups);
            autoDistributePoints(currentPendingGroups[0], 2.0);
            renderCart();
        }
    }

    function updateRule(groupId, ruleId, field, val) {
        function findGroupAndRule(groups) {
            for (let g of groups) {
                if (g.id === groupId) {
                    let r = g.rules.find(x => x.id == ruleId);
                    if (r) return r;
                }
                if (g.sub_criteria) {
                    let res = findGroupAndRule(g.sub_criteria);
                    if (res) return res;
                }
            }
            return null;
        }
        let rule = findGroupAndRule(currentPendingGroups);
        if (rule) {
            if (field === 'points') {
                rule.points = parseFloat(val);
                rule.is_manually_edited = true;
                let totalPts = currentPendingGroups[0].target_points || 2.0;
                autoDistributePoints(currentPendingGroups[0], totalPts);
                renderCart();
            } else {
                rule[field] = val;
            }
        }
    }

    function removeRule(groupId, ruleId) {
        function delRule(groups) {
            for (let g of groups) {
                if (g.id === groupId) {
                    const idx = g.rules.findIndex(x => x.id == ruleId);
                    if (idx > -1) { g.rules.splice(idx, 1); return true; }
                }
                if (g.sub_criteria && delRule(g.sub_criteria)) return true;
            }
            return false;
        }
        delRule(currentPendingGroups);
        autoDistributePoints(currentPendingGroups[0], 2.0);
        renderCart();
    }

    function updateMainPoints(val) {
        if (currentPendingGroups.length === 0) return;
        let pts = parseFloat(val) || 0;
        currentPendingGroups[0].target_points = pts;
        autoDistributePoints(currentPendingGroups[0], pts);
        renderCart();
    }

    function autoDistributePoints(group, availablePoints) {
        // 1. Thu thập tất cả các "nhánh" cần chia điểm (Rule chưa sửa tay + Tất cả các nhóm con)
        let unlockedBranches = [];
        let lockedPoints = 0;

        // Kiểm tra các rule trực tiếp
        group.rules.forEach(r => {
            if (r.is_manually_edited) {
                lockedPoints += (r.points || 0);
            } else {
                unlockedBranches.push({ type: 'rule', ref: r });
            }
        });

        // Kiểm tra các nhóm con (Sub-criteria luôn được chia điểm từ cha)
        if (group.sub_criteria) {
            group.sub_criteria.forEach(sub => {
                unlockedBranches.push({ type: 'sub', ref: sub });
            });
        }

        const N = unlockedBranches.length;
        if (N === 0) return;

        // 2. Tính toán số điểm còn lại và quy đổi ra số nguyên (nhân 100) để chia chính xác
        let remainingPoints = Math.max(0, availablePoints - lockedPoints);
        let totalCents = Math.round(remainingPoints * 100);
        let baseCentsPerBranch = Math.floor(totalCents / N);
        let remainderCents = totalCents % N; // Phần dư cần được bù vào

        // 3. Phân bổ điểm
        unlockedBranches.forEach((branch, index) => {
            // Mỗi nhánh nhận điểm cơ sở, các nhánh đầu tiên nhận thêm 0.01đ từ phần dư
            let allocatedCents = baseCentsPerBranch + (index < remainderCents ? 1 : 0);
            let allocatedPoints = allocatedCents / 100;

            if (branch.type === 'rule') {
                branch.ref.points = allocatedPoints;
            } else {
                // Nếu là nhóm con, ném số điểm được chia xuống để nó tự chia tiếp cho con của nó
                autoDistributePoints(branch.ref, allocatedPoints);
            }
        });
    }

    function renderRulesList(group, depth = 0) {
        let html = '';
        let marginLeft = depth * 20;
        let borderColor = depth === 0 ? 'border-success' : (depth === 1 ? 'border-primary' : 'border-info');

        group.rules.forEach((rule) => {
            html += `
            <div class="card mb-2 border-start border-4 ${borderColor} shadow-sm" style="margin-left: ${marginLeft}px;">
                <div class="card-body p-2">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <input type="text" class="form-control form-control-sm fw-bold text-dark border-0 bg-transparent px-0 w-75" 
                            value="${rule.description}" onchange="PPTRubricBuilder.updateRule('${group.id}', '${rule.id}', 'description', this.value)">
                        <div class="d-flex gap-1 align-items-center">
                            <span class="small text-muted">Điểm:</span>
                            <input type="number" class="form-control form-control-sm text-center" style="width: 50px;" value="${rule.points}" step="0.25" onchange="PPTRubricBuilder.updateRule('${group.id}', '${rule.id}', 'points', this.value)">
                            <button class="btn btn-sm text-danger p-0" onclick="PPTRubricBuilder.removeRule('${group.id}', '${rule.id}')" title="Xóa luật"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text bg-light text-muted" style="font-size:0.75rem;">Kỳ vọng</span>
                        <input type="text" class="form-control text-dark font-monospace" value="${rule.expected_value || rule.action}" onchange="PPTRubricBuilder.updateRule('${group.id}', '${rule.id}', 'expected_value', this.value)" title="Path: ${rule.property_to_check}">
                    </div>
                </div>
            </div>`;
        });
        return html;
    }

    function renderCart() {
        const cartDiv = document.getElementById('selected_rules_cart');
        if (!cartDiv) return;
        if (currentPendingGroups.length === 0) {
            cartDiv.innerHTML = '<div class="alert alert-secondary text-center small py-2">Trống.</div>';
            return;
        }

        let html = '';
        function renderGroupRecursive(group, depth) {
            let res = '';
            if (depth > 0) {
                // Đã bổ sung nút XÓA KHỐI (removeGroup) trên giao diện
                res += `<div class="mt-2 p-2 bg-light border rounded" style="margin-left: ${(depth - 1) * 20}px;">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="text-primary fw-bold mb-0" style="font-size: 0.9rem;"><i class="bi bi-box"></i> ${group.criteria_name}</h6>
                                <div>
                                    <button class="btn btn-sm btn-outline-success py-0 me-1" onclick="PPTRubricBuilder.addSubRule('${group.id}')" title="Thêm luật vào khối này"><i class="bi bi-plus"></i> Luật</button>
                                    <button class="btn btn-sm btn-outline-danger py-0" onclick="PPTRubricBuilder.removeGroup('${group.id}')" title="Xóa toàn bộ khối này"><i class="bi bi-trash"></i> Xóa khối</button>
                                </div>
                            </div>`;
            }
            res += renderRulesList(group, depth);
            if (group.sub_criteria) {
                group.sub_criteria.forEach(sub => res += renderGroupRecursive(sub, depth + 1));
            }
            if (depth > 0) res += `</div>`;
            return res;
        }

        currentPendingGroups.forEach(mainGroup => {
            let currentTotal = mainGroup.target_points || 2.0;
            html += `
            <div class="d-flex justify-content-between align-items-center mt-3 mb-2 pb-2 border-bottom">
                <h6 class="text-success fw-bold mb-0"><i class="bi bi-display"></i> Layer Cấp Cao Nhất</h6>
                <div class="input-group input-group-sm w-auto shadow-sm">
                    <span class="input-group-text bg-success text-white fw-bold">Tổng điểm khối này:</span>
                    <input type="number" id="main_total_points" class="form-control text-center fw-bold text-success" style="width: 75px;" value="${currentTotal}" step="0.25" onchange="PPTRubricBuilder.updateMainPoints(this.value)">
                </div>
            </div>`;
            html += renderGroupRecursive(mainGroup, 0);
        });

        cartDiv.innerHTML = html;
    }

    // ==========================================
    // LƯU DỮ LIỆU ĐỂ EXPORT (VỚI AUTO-CLEAN DỌN RÁC)
    // ==========================================
    function saveCurrentCriteria() {
        if (currentPendingGroups.length === 0) return alert("Cần ít nhất 1 luật!");
        const name = document.getElementById('criteria_name').value;

        // Đệ quy dọn dẹp ID, tính tổng điểm VÀ TỰ ĐỘNG XÓA KHỐI RỖNG
        function cleanGroup(group) {
            let total = group.rules.reduce((sum, r) => sum + parseFloat(r.points || 0), 0);
            group.rules = group.rules.map(({ id, ...rest }) => rest);

            if (group.sub_criteria) {
                let subTotal = 0;
                let cleanedSubCriteria = [];
                for (let sub of group.sub_criteria) {
                    let cleanedSub = cleanGroup(sub);
                    // CHỈ GIỮ LẠI khối nếu nó có luật, HOẶC nhóm con của nó có luật
                    if (cleanedSub.rules.length > 0 || (cleanedSub.sub_criteria && cleanedSub.sub_criteria.length > 0)) {
                        subTotal += cleanedSub.allocated_points;
                        cleanedSubCriteria.push(cleanedSub);
                    }
                }
                group.sub_criteria = cleanedSubCriteria;
                group.allocated_points = total + subTotal;

                // Nếu mảng rỗng thì xóa luôn trường sub_criteria cho JSON gọn
                if (group.sub_criteria.length === 0) {
                    delete group.sub_criteria;
                }
            } else {
                group.allocated_points = total;
            }
            delete group.id;
            return group;
        }

        let finalGroup = cleanGroup(JSON.parse(JSON.stringify(currentPendingGroups[0])));

        // Khối Main ngoài cùng không có luật nào thì chặn lưu
        if (finalGroup.rules.length === 0 && !finalGroup.sub_criteria) {
            return alert("Không thể lưu cụm tiêu chí rỗng. Vui lòng thiết lập ít nhất 1 luật!");
        }

        finalGroup.criteria_name = name;
        globalRubric.push(finalGroup);

        if (document.getElementById('btnSaveRubric')) document.getElementById('btnSaveRubric').disabled = false;
        document.getElementById('rubric-builder-area').innerHTML = '';
        document.getElementById('rubric-empty-state').classList.remove('d-none');
        if (typeof showToast === 'function') showToast(`Đã lưu tiêu chí: ${name}`, "success");
    }

    // Modal & Export
    function showRubricModal() {
        let tbodyHtml = '';
        globalRubric.forEach((crit, index) => {
            let anchorDesc = crit.anchor_locator.type === 'presentation' ? 'Toàn trang' :
                crit.anchor_locator.type === 'slide_master' ? 'Slide Master' :
                    `Slide ${crit.anchor_locator.properties?.slide_index || ''}`;

            let ruleCount = crit.rules.length;

            tbodyHtml += `
                <tr>
                    <td class="fw-bold text-primary">${crit.criteria_name}</td>
                    <td><span class="badge bg-light border text-dark text-wrap text-start lh-base">${anchorDesc}</span></td>
                    <td class="text-center fw-bold text-success">${crit.allocated_points}</td>
                    <td class="text-center">${ruleCount}+</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-outline-danger" onclick="PPTRubricBuilder.deleteCriteria(${index})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        });

        if (globalRubric.length === 0) tbodyHtml = `<tr><td colspan="5" class="text-center text-muted py-4">Chưa có tiêu chí nào.</td></tr>`;

        let modalEl = document.getElementById('rubricViewModal');

        // NẾU MODAL CHƯA TỒN TẠI -> TẠO MỚI (Lần đầu bấm Xem)
        if (!modalEl) {
            const modalHtml = `
            <div class="modal fade" id="rubricViewModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title fw-bold"><i class="bi bi-card-checklist"></i> Danh sách Tiêu chí Rubric</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-0">
                            <table class="table table-hover mb-0">
                                <thead class="table-light">
                                    <tr><th>Tên tiêu chí</th><th>Mốc định vị (Anchor)</th><th class="text-center">Điểm</th><th class="text-center">Luật gốc</th><th class="text-center">Xóa</th></tr>
                                </thead>
                                <tbody id="rubricModalTbody">${tbodyHtml}</tbody>
                            </table>
                        </div>
                        <div class="modal-footer bg-light">
                            <button type="button" class="btn btn-secondary fw-bold" data-bs-dismiss="modal">Đóng</button>
                            <button type="button" class="btn btn-success fw-bold" onclick="PPTRubricBuilder.downloadRubric()"><i class="bi bi-download"></i> Tải File JSON</button>
                        </div>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modalEl = document.getElementById('rubricViewModal');
            new bootstrap.Modal(modalEl).show();
        }
        // NẾU MODAL ĐÃ MỞ RỒI -> CHỈ CẬP NHẬT LẠI DỮ LIỆU CỦA BẢNG (Khi bấm Xóa)
        else {
            document.getElementById('rubricModalTbody').innerHTML = tbodyHtml;

            // Đảm bảo Modal luôn ở trạng thái hiển thị
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
            return showToast("Rubric đang trống! Vui lòng tạo ít nhất 1 tiêu chí.", "warning");
        }

        const rubricBlob = new Blob([JSON.stringify(globalRubric, null, 4)], { type: "application/json" });
        const url = URL.createObjectURL(rubricBlob);
        const a = document.createElement('a');
        a.href = url;
        // Đổi tên file cho phù hợp với PowerPoint
        a.download = "rubric_powerpoint_export.json";
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

    return {
        init, handleNodeClick, presetSlideCount, presetTransitionCheck, presetActionButtons, presetMatrixLayout,
        createEmptyCriteria, addManualRule, addSubRule, updateRule, removeRule, removeGroup, saveCurrentCriteria, downloadRubric,
        showRubricModal, deleteCriteria, exportRubric, updateMainPoints,
        currentPendingGroups,
        getRubric: () => globalRubric
    };
})();