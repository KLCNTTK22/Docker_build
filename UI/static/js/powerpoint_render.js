/**
 * POWERPOINT RENDERER - AST HOVER INSPECT OPTIMIZED
 */

const PPTXRenderer = (function () {
    const EMU_TO_PX = 9525;

    function escapeHtml(unsafe) {
        if (!unsafe) return "";
        return unsafe.toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function emuToPx(emu) {
        if (!emu) return 0;
        return parseInt(emu) / EMU_TO_PX;
    }

    // Bộ phân giải Kế thừa toạ độ
    function resolveLayout(ast, node) {
        if (node.layout) return node.layout;

        if (node.properties?.is_placeholder && node.properties.placeholder) {
            const ph = node.properties.placeholder;
            const layoutsAndMasters = ast.children.filter(c => c.type === 'slide_layout' || c.type === 'slide_master');

            for (let lm of layoutsAndMasters) {
                if (lm.children) {
                    for (let child of lm.children) {
                        if (child.properties?.is_placeholder && child.properties.placeholder) {
                            const tplPh = child.properties.placeholder;
                            if (tplPh.type === ph.type && tplPh.idx === ph.idx && child.layout) return child.layout;
                        }
                    }
                }
            }
            for (let lm of layoutsAndMasters) {
                if (lm.children) {
                    for (let child of lm.children) {
                        if (child.properties?.is_placeholder && child.properties.placeholder) {
                            const tplPh = child.properties.placeholder;
                            if (tplPh.type === ph.type && child.layout) return child.layout;
                        }
                    }
                }
            }
        }
        return null;
    }

    // ==========================================
    // KHỞI TẠO TOOLTIP "HOVER INSPECT"
    // ==========================================
    function initHoverTooltip(container) {
        let tooltip = document.getElementById('ast-inspector-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'ast-inspector-tooltip';
            tooltip.style.cssText = 'position: absolute; display: none; background: rgba(33, 37, 41, 0.95); color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 11px; font-family: monospace; z-index: 10000; pointer-events: none; box-shadow: 0 4px 6px rgba(0,0,0,0.3); white-space: nowrap; line-height: 1.4; border: 1px solid #495057;';
            document.body.appendChild(tooltip);
        }

        container.addEventListener('mousemove', function(e) {
            const target = e.target.closest('.ast-selectable');
            
            if (target) {
                tooltip.style.display = 'block';
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY + 15) + 'px';
                
                const type = target.dataset.astType || 'Element';
                const path = target.dataset.astPath || '';
                tooltip.innerHTML = `<span style="color: #0dcaf0; font-weight: bold;">[${type}]</span><br><span style="color: #dee2e6;">Path: ${path}</span>`;
                
                document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
                target.classList.add('ast-hovered');
            } else {
                tooltip.style.display = 'none';
                document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
            }
        });

        container.addEventListener('mouseleave', function() {
            tooltip.style.display = 'none';
            document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
        });
    }

    // ==========================================
    // HÀM RENDER CHÍNH
    // ==========================================
    function render(ast, containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        container.style.backgroundColor = '#e9ecef';
        container.style.padding = '30px';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.alignItems = 'center';
        container.style.gap = '40px';
        container.style.overflowX = 'hidden';

        // Kích hoạt Hover Tooltip
        initHoverTooltip(container);

        let slideWidthEMU = 12192000;
        let slideHeightEMU = 6858000;

        if (ast.properties && ast.properties.slide_size) {
            slideWidthEMU = ast.properties.slide_size.cx || slideWidthEMU;
            slideHeightEMU = ast.properties.slide_size.cy || slideHeightEMU;
        }

        const slideW = emuToPx(slideWidthEMU);
        const slideH = emuToPx(slideHeightEMU);
        const containerWidth = container.clientWidth - 80;

        // --- GIAO DIỆN SLIDE MASTER TÍCH HỢP ---
        const masterNode = ast.children.find(c => c.type === 'slide_master');
        if (masterNode) {
            const masterBtn = document.createElement('button');
            masterBtn.className = 'btn btn-warning fw-bold text-dark shadow mb-2';
            masterBtn.innerHTML = '<i class="bi bi-layers-half"></i> Xem thiết lập Slide Master';

            const masterWrapper = document.createElement('div');
            masterWrapper.style.display = 'none';
            masterWrapper.style.width = '100%';
            masterWrapper.style.border = '2px dashed #ffc107';
            masterWrapper.style.padding = '20px';
            masterWrapper.style.backgroundColor = '#fff3cd';
            masterWrapper.style.borderRadius = '8px';
            masterWrapper.style.marginBottom = '20px';
            masterWrapper.style.display = 'flex';
            masterWrapper.style.flexDirection = 'column';
            masterWrapper.style.alignItems = 'center';

            let ts = masterNode.properties?.text_styles || {};
            const getSz = (val) => (parseInt(val) / 100) || 'N/A';

            const titleF = ts.titleStyle?.lvl1pPr?.font_name || ts.titleStyle?.font_name || 'N/A';
            const titleS = ts.titleStyle?.lvl1pPr?.sz || ts.titleStyle?.sz;

            const body1F = ts.bodyStyle?.lvl1pPr?.font_name || ts.bodyStyle?.font_name || 'N/A';
            const body1S = ts.bodyStyle?.lvl1pPr?.sz || ts.bodyStyle?.sz;

            const body2F = ts.bodyStyle?.lvl2pPr?.font_name || 'N/A';
            const body2S = ts.bodyStyle?.lvl2pPr?.sz;

            let fontInfo = `
                <div class="w-100 mb-3">
                    <h6 class="fw-bold text-warning-emphasis"><i class="bi bi-gear-fill"></i> Theme: ${ast.properties?.app_properties?.Template || 'Default'}</h6>
                    <ul class="small text-dark mb-0 list-unstyled">
                        <li><b>Tiêu đề:</b> Font <b>${titleF}</b>, Cỡ <b>${getSz(titleS)}pt</b></li>
                        <li><b>Nội dung cấp 1:</b> Font <b>${body1F}</b>, Cỡ <b>${getSz(body1S)}pt</b></li>
                        <li><b>Nội dung cấp 2:</b> Font <b>${body2F}</b>, Cỡ <b>${getSz(body2S)}pt</b></li>
                    </ul>
                </div>
            `;

            const masterAstIndex = ast.children.indexOf(masterNode);
            const masterSlideDOM = createSlideDOM(masterNode, `children.${masterAstIndex}`, ast, slideW, slideH, containerWidth - 40, "SLIDE MASTER");

            masterWrapper.innerHTML = fontInfo;
            masterWrapper.appendChild(masterSlideDOM);

            masterBtn.onclick = () => {
                const isHidden = masterWrapper.style.display === 'none';
                masterWrapper.style.display = isHidden ? 'flex' : 'none';
                masterBtn.innerHTML = isHidden ? '<i class="bi bi-eye-slash"></i> Ẩn Slide Master' : '<i class="bi bi-layers-half"></i> Xem thiết lập Slide Master';
            };

            masterWrapper.style.display = 'none';
            container.appendChild(masterBtn);
            container.appendChild(masterWrapper);
        }

        // --- RENDER CÁC SLIDE NỘI DUNG ---
        const slides = ast.children.filter(c => c.tag === 'p:sld' || c.type === 'slide');

        if (slides.length === 0) {
            container.innerHTML += '<div class="alert alert-warning w-100 text-center">Không tìm thấy trang Slide nào.</div>';
            return;
        }

        slides.forEach((slide, index) => {
            const actualAstIndex = ast.children.indexOf(slide);
            const slideDOM = createSlideDOM(slide, `children.${actualAstIndex}`, ast, slideW, slideH, containerWidth, `Slide ${slide.properties?.slide_index || (index + 1)}`);
            container.appendChild(slideDOM);
        });
    }

    function createSlideDOM(slideNode, slidePath, ast, slideW, slideH, maxAllowableWidth, labelText) {
        const wrapper = document.createElement('div');
        wrapper.className = 'ast-selectable pptx-slide-wrapper shadow-lg';
        wrapper.dataset.astPath = slidePath;
        wrapper.dataset.astType = "Slide (Trang chiếu)";

        wrapper.style.width = slideW + 'px';
        wrapper.style.height = slideH + 'px';
        wrapper.style.backgroundColor = '#ffffff';
        wrapper.style.position = 'relative';
        wrapper.style.flexShrink = '0';
        wrapper.style.border = '1px solid #6c757d';

        if (slideW > maxAllowableWidth) {
            const scale = maxAllowableWidth / slideW;
            wrapper.style.transform = `scale(${scale})`;
            wrapper.style.transformOrigin = 'top center';
            wrapper.style.marginBottom = `-${slideH * (1 - scale)}px`;
        }

        const slideLabel = document.createElement('div');
        let badgeColor = labelText === 'SLIDE MASTER' ? 'bg-warning text-dark' : 'bg-secondary';
        slideLabel.innerHTML = `<span class="badge ${badgeColor}" style="position: absolute; top: -15px; left: -10px; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.3); font-size: 14px;">${labelText}</span>`;
        wrapper.appendChild(slideLabel);

        if (slideNode.children) {
            slideNode.children.forEach((child, childIdx) => {
                const childPath = `${slidePath}.children.${childIdx}`;
                const el = createPPTXElement(child, childPath, ast);
                if (el) wrapper.appendChild(el);
            });
        }
        return wrapper;
    }

    function createPPTXElement(node, path, ast) {
        if (node.tag === 'p:transition' || node.type === 'transition') return null;

        const el = document.createElement('div');
        el.className = 'ast-selectable pptx-element';
        el.dataset.astPath = path;
        el.style.boxSizing = 'border-box';

        el.style.outline = '1px dashed #ced4da';
        el.onmouseenter = (e) => { e.stopPropagation(); el.style.outline = '2px dashed #0d6efd'; };
        el.onmouseleave = (e) => { e.stopPropagation(); el.style.outline = '1px dashed #ced4da'; };

        const layout = resolveLayout(ast, node);

        if (layout) {
            el.style.position = 'absolute';
            el.style.left = emuToPx(layout.x) + 'px';
            el.style.top = emuToPx(layout.y) + 'px';
            el.style.width = emuToPx(layout.cx) + 'px';
            el.style.height = emuToPx(layout.cy) + 'px';
            el.style.zIndex = '10';
        } else {
            el.style.position = 'relative';
            el.style.width = '90%';
            el.style.margin = '10px auto';
            el.style.border = '1px dashed #dc3545'; 
            el.style.minHeight = '30px';
        }

        if (node.properties?.is_action_button) {
            el.dataset.astType = "Action Button (Nút Action)";
            el.style.backgroundColor = '#0dcaf033';
            el.style.border = '2px solid #0dcaf0';
            el.style.display = 'flex';
            el.style.alignItems = 'center';
            el.style.justifyContent = 'center';
            el.innerHTML = `<i class="bi bi-play-circle text-info fs-3"></i>`;
            el.title = node.attributes?.name || "Action Button";
            return el;
        }

        if (node.tag === 'p:sp' || node.type === 'shape') {
            const isPlaceholder = node.properties?.is_placeholder;
            const phType = node.properties?.placeholder?.type;
            
            el.dataset.astType = isPlaceholder ? `Placeholder (${phType})` : "Shape (Hình khối/Hộp thoại)";

            let innerHtml = renderPPTXText(node.children, path);

            if (!innerHtml.includes('<span') && isPlaceholder) {
                let phLabels = {
                    'dt': '<i class="bi bi-calendar-date"></i> [Date]',
                    'ftr': '<i class="bi bi-card-text"></i> [Footer]',
                    'sldNum': '<i class="bi bi-hash"></i> [Slide #]',
                    'title': '[Title]',
                    'ctrTitle': '[Center Title]',
                    'body': '[Body Content]'
                };
                let label = phLabels[phType] || `[${phType}]`;
                innerHtml = `
                    <div class="d-flex align-items-center justify-content-center w-100 h-100 text-muted" 
                         style="background-color: rgba(200,200,200,0.1); font-size: 12px; font-weight: bold;">
                         ${label}
                    </div>
                `;
            }
            el.innerHTML = innerHtml;
        }
        else if (node.tag === 'p:pic' || node.type === 'picture') {
            el.dataset.astType = "Picture (Hình ảnh)";
            el.style.backgroundColor = '#e2e3e5';
            el.style.border = '1px solid #adb5bd';
            el.style.display = 'flex';
            el.style.alignItems = 'center';
            el.style.justifyContent = 'center';
            el.innerHTML = `
                <div class="text-center text-secondary">
                    <i class="bi bi-image fs-3"></i><br>
                    <small style="font-size: 10px;">${node.attributes?.name || "Hình ảnh"}</small>
                </div>
            `;
        }
        else if (node.tag === 'p:graphicFrame' || node.type === 'graphic_frame') {
            if (node.children && node.children.length > 0) {
                const graphicChild = node.children[0];

                if (graphicChild.tag === 'a:tbl' || graphicChild.type === 'table') {
                    el.dataset.astType = "Table (Bảng biểu)";
                    el.style.backgroundColor = 'transparent';
                    el.style.display = 'flex';
                    el.appendChild(renderPPTXTable(graphicChild, `${path}.children.0`));
                } else {
                    el.dataset.astType = "Graphic Frame (Khung đồ họa)";
                    el.style.backgroundColor = '#d1e7dd';
                    el.style.border = '2px solid #198754';
                    el.style.display = 'flex';
                    el.style.alignItems = 'center';
                    el.style.justifyContent = 'center';

                    const isChart = graphicChild.tag === 'c:chartSpace';
                    const isSmartArt = graphicChild.tag === 'dgm:dataModel' || node.properties?.frame_type === 'smartart';

                    if (isChart) {
                        el.dataset.astType = "Chart (Biểu đồ)";
                        el.innerHTML = `
                            <div class="text-center text-success">
                                <i class="bi bi-bar-chart-line-fill fs-2"></i><br>
                                <span class="fw-bold" style="font-size: 11px;">${node.attributes?.name || 'Biểu đồ'}</span>
                            </div>
                        `;
                    } else if (isSmartArt) {
                        el.dataset.astType = "SmartArt Container";
                        el.style.flexDirection = 'column';
                        el.style.padding = '10px';
                        el.innerHTML = `<div class="badge bg-success mb-2 w-100"><i class="bi bi-diagram-3-fill"></i> ${node.attributes?.name || 'SmartArt'}</div>`;
                        
                        let dataModel = node.children.find(c => c.type === 'smartart_data' || c.tag === 'dgm:dataModel');
                        if (dataModel && dataModel.children) {
                            let nodeContainer = document.createElement('div');
                            nodeContainer.className = 'd-flex flex-wrap gap-1 justify-content-center w-100';
                            
                            dataModel.children.forEach((pt, pIdx) => {
                                if (pt.type === 'smartart_node' || pt.tag === 'dgm:pt') {
                                    let nodeBox = document.createElement('div');
                                    nodeBox.className = 'ast-selectable border border-success bg-white p-1 text-center small';
                                    nodeBox.dataset.astPath = `${path}.children.0.children.${pIdx}`;
                                    nodeBox.dataset.astType = "SmartArt Node (Khối)";
                                    nodeBox.innerHTML = renderPPTXText(pt.children, nodeBox.dataset.astPath) || '[Trống]';
                                    nodeContainer.appendChild(nodeBox);
                                }
                            });
                            el.appendChild(nodeContainer);
                        }
                    }
                }
            }
        }
        return el;
    }

    function renderPPTXText(children, basePath) {
        if (!children) return '';
        let html = '<div style="padding: 5px; width: 100%; height: 100%; overflow: hidden; display: flex; flex-direction: column;">';

        children.forEach((p, pIdx) => {
            if (p.tag === 'a:p' || p.type === 'paragraph') {
                const alignVal = p.layout?.alignment || p.style?.align || 'left';
                let alignCss = 'left';
                if (alignVal === 'ctr' || alignVal === 'center') alignCss = 'center';
                if (alignVal === 'r' || alignVal === 'right') alignCss = 'right';
                if (alignVal === 'just' || alignVal === 'justify') alignCss = 'justify';

                let paraPath = `${basePath}.children.${pIdx}`;
                html += `<div class="ast-selectable" data-ast-path="${paraPath}" data-ast-type="Paragraph (Đoạn văn)" style="text-align: ${alignCss}; margin-bottom: 4px; line-height: 1.3;">`;

                if (p.children) {
                    p.children.forEach((r, rIdx) => {
                        if (r.tag === 'a:r' || r.type === 'text_run') {
                            let css = '';
                            const props = r.properties || r.style || {};

                            if (props.bold || props.b === '1') css += 'font-weight: bold; ';
                            if (props.italic || props.i === '1') css += 'font-style: italic; ';
                            if (props.underline) css += 'text-decoration: underline; ';

                            if (props.fontSize) css += `font-size: ${props.fontSize}px; `;
                            else if (props.sz) css += `font-size: ${parseInt(props.sz) / 100}px; `;

                            if (props.color && props.color !== 'auto') css += `color: #${props.color.replace('#', '')}; `;
                            if (props.resolvedFont || props.font_name) css += `font-family: '${props.resolvedFont || props.font_name}', sans-serif; `;

                            let runPath = `${paraPath}.children.${rIdx}`;
                            html += `<span class="ast-selectable" data-ast-path="${runPath}" data-ast-type="Text Run (Cụm chữ)" style="${css}">${escapeHtml(r.text || '')}</span>`;
                        }
                    });
                }
                html += `</div>`;
            }
        });

        html += '</div>';
        return html;
    }

    function renderPPTXTable(node, path) {
        const table = document.createElement('table');
        table.className = 'table table-bordered border-success ast-table w-100 h-100 mb-0';
        table.style.tableLayout = 'fixed';
        table.style.backgroundColor = 'white';

        if (node.children) {
            let rows = node.children.filter(c => c.tag === 'a:tr' || c.type === 'table_row');
            let skipMap = {}; 

            rows.forEach((row, r) => {
                if (!skipMap[r]) skipMap[r] = {};
                const tr = document.createElement('tr');
                let cells = row.children.filter(c => c.tag === 'a:tc' || c.type === 'table_cell');

                cells.forEach((cell, c) => {
                    if (skipMap[r][c]) return;

                    const td = document.createElement('td');
                    td.className = 'ast-selectable p-1';

                    const originalRowIdx = node.children.indexOf(row);
                    const originalCellIdx = row.children.indexOf(cell);
                    
                    td.dataset.astPath = `${path}.children.${originalRowIdx}.children.${originalCellIdx}`;
                    td.dataset.astType = `Table Cell (Ô ${r+1}-${c+1})`;

                    let rowSpan = parseInt(cell.attributes?.rowSpan || 1);
                    let colSpan = parseInt(cell.attributes?.gridSpan || 1);

                    if (rowSpan > 1) td.rowSpan = rowSpan;
                    if (colSpan > 1) td.colSpan = colSpan;

                    for (let dr = 0; dr < rowSpan; dr++) {
                        for (let dc = 0; dc < colSpan; dc++) {
                            if (dr === 0 && dc === 0) continue; 
                            if (!skipMap[r + dr]) skipMap[r + dr] = {};
                            skipMap[r + dr][c + dc] = true;
                        }
                    }

                    if (cell.layout?.shading) td.style.backgroundColor = `#${cell.layout.shading}`;
                    td.innerHTML = renderPPTXText(cell.children, td.dataset.astPath);
                    tr.appendChild(td);
                });
                table.appendChild(tr);
            });
        }
        return table;
    }

    return { render };
})();