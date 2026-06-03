/**
 * Engine Render AST của Word sang HTML (Giai đoạn 2: Hover Inspect)
 */

function renderWordAST(ast, containerId) {
    const previewContainer = document.getElementById(containerId);
    previewContainer.innerHTML = ''; 
    
    if (!ast.children || !Array.isArray(ast.children)) {
        previewContainer.innerHTML = '<p class="text-danger">Không tìm thấy nội dung văn bản.</p>';
        return;
    }

    // ==========================================
    // KHỞI TẠO TOOLTIP "HOVER INSPECT" NHƯ F12
    // ==========================================
    let tooltip = document.getElementById('ast-inspector-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'ast-inspector-tooltip';
        // Style cho tooltip trôi nổi màu đen
        tooltip.style.cssText = 'position: absolute; display: none; background: rgba(33, 37, 41, 0.95); color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 11px; font-family: monospace; z-index: 10000; pointer-events: none; box-shadow: 0 4px 6px rgba(0,0,0,0.3); white-space: nowrap; line-height: 1.4; border: 1px solid #495057;';
        document.body.appendChild(tooltip);
    }

    // Bám theo chuột để bắt thẻ sâu nhất
    previewContainer.addEventListener('mousemove', function(e) {
        // e.target luôn là phần tử sâu nhất chuột chạm vào
        const target = e.target.closest('.ast-selectable');
        
        if (target) {
            tooltip.style.display = 'block';
            // Vị trí chuột + lệch ra một xíu để không che mất con trỏ
            tooltip.style.left = (e.pageX + 15) + 'px';
            tooltip.style.top = (e.pageY + 15) + 'px';
            
            const type = target.dataset.astType || 'Element';
            const path = target.dataset.astPath || '';
            tooltip.innerHTML = `<span style="color: #0dcaf0; font-weight: bold;">[${type}]</span><br><span style="color: #dee2e6;">Path: ${path}</span>`;
            
            // Xóa highlight cũ, chỉ highlight thẻ hiện tại
            document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
            target.classList.add('ast-hovered');
        } else {
            tooltip.style.display = 'none';
            document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
        }
    });

    previewContainer.addEventListener('mouseleave', function() {
        tooltip.style.display = 'none';
        document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
    });

    // ==========================================
    // RENDER VĂN BẢN (Đã thêm data-ast-type)
    // ==========================================
    const context = { listCounters: {}, footnotes: [] };

    ast.children.forEach((node, index) => {
        const rootPath = `children.${index}`;
        const el = buildHtmlFromWordNode(node, null, context, rootPath);
        if (el) previewContainer.appendChild(el);
    });

    // Render Footnotes
    if (context.footnotes.length > 0) {
        const fnContainer = document.createElement('div');
        fnContainer.className = 'mt-5 pt-3 border-top border-2 border-secondary';
        context.footnotes.forEach(fn => {
            const fnItem = document.createElement('div');
            fnItem.className = 'd-flex mb-2 text-muted small';
            fnItem.innerHTML = `<div class="fw-bold text-primary me-2"><sup>${fn.id}</sup></div>`;
            const fnContent = document.createElement('div');
            if (fn.children) {
                fn.children.forEach((c, idx) => {
                    const cEl = buildHtmlFromWordNode(c, null, context, `footnotes.${fn.id}.children.${idx}`);
                    if (cEl) fnContent.appendChild(cEl);
                });
            }
            fnItem.appendChild(fnContent);
            fnContainer.appendChild(fnItem);
        });
        previewContainer.appendChild(fnContainer);
    }
}

function buildHtmlFromWordNode(node, parentNode = null, context = { listCounters: {}, footnotes: [] }, currentPath = "") {
    if (!node) return null;

    // ---------------------------------------------------------
    // 1. PARAGRAPH (w:p)
    // ---------------------------------------------------------
    if (node.type === 'paragraph' || node.tag === 'w:p') {
        const p = document.createElement('div');
        p.className = 'ast-selectable mb-1'; 
        p.dataset.astPath = currentPath; 
        p.dataset.astType = "Paragraph (Đoạn văn)"; // Gắn nhãn
        
        if (node.section) {
            const secInfo = document.createElement('div');
            secInfo.className = 'badge bg-info text-dark w-100 my-2 text-start opacity-75';
            let secText = '<i class="bi bi-layout-split"></i> Section Break';
            if (node.section.pageSize && node.section.pageSize.orient === 'landscape') secText += ' (Trang ngang)';
            if (node.section.columns && node.section.columns.count > 1) secText += ` - Chia ${node.section.columns.count} cột`;
            secInfo.innerHTML = secText;
            p.appendChild(secInfo);

            if (node.section.headers_footers && node.section.headers_footers.length > 0) {
                const hfContainer = document.createElement('div');
                hfContainer.className = 'my-3 p-3 border border-primary border-dashed bg-light rounded';
                
                node.section.headers_footers.forEach((hf, hfIdx) => {
                    const hfBlock = document.createElement('div');
                    hfBlock.className = 'ast-selectable border-bottom border-primary mb-2 pb-2';
                    hfBlock.dataset.astPath = `${currentPath}.section.headers_footers.${hfIdx}`;
                    hfBlock.dataset.astType = `Header/Footer (${hf.displayType})`; // Gắn nhãn H/F
                    
                    const hfLabel = document.createElement('div');
                    hfLabel.className = 'badge bg-primary mb-2';
                    hfLabel.innerText = `${hf.type.toUpperCase()} (${hf.displayType})`;
                    hfBlock.appendChild(hfLabel);

                    if (hf.children) {
                        hf.children.forEach((c, cIdx) => {
                            const cEl = buildHtmlFromWordNode(c, node, context, `${currentPath}.section.headers_footers.${hfIdx}.children.${cIdx}`);
                            if (cEl) hfBlock.appendChild(cEl);
                        });
                    }
                    hfContainer.appendChild(hfBlock);
                });
                p.appendChild(hfContainer);
            }
        }

        if (node.layout) {
            if (node.layout.alignment) p.style.textAlign = node.layout.alignment === 'both' ? 'justify' : node.layout.alignment;
            if (node.layout.indent) {
                if (node.layout.indent.firstLinePt) p.style.textIndent = node.layout.indent.firstLinePt + 'px';
                if (node.layout.indent.leftPt) p.style.marginLeft = node.layout.indent.leftPt + 'px';
            }
            if (node.layout.spacing) {
                if (node.layout.spacing.beforePt) p.style.marginTop = node.layout.spacing.beforePt + 'px';
                if (node.layout.spacing.afterPt) p.style.marginBottom = node.layout.spacing.afterPt + 'px';
                if (node.layout.spacing.linePt) p.style.lineHeight = (node.layout.spacing.linePt / 12) + 'px';
            }
        }

        if (node.properties && node.properties.pStyle) {
            if (node.properties.pStyle.includes('Heading')) {
                p.style.fontWeight = 'bold';
                p.style.fontSize = '1.2em';
                p.style.marginBottom = '8px';
                p.style.color = '#2c3e50';
            }
        }

        if (node.properties && node.properties.paragraphRunProperties) {
            const prp = node.properties.paragraphRunProperties;
            if (prp.fontSize) p.style.fontSize = prp.fontSize + 'px';
            if (prp.color && prp.color !== 'auto') p.style.color = '#' + prp.color;
            if (prp.font && prp.font.ascii) p.style.fontFamily = `"${prp.font.ascii}", sans-serif`;
            
            let textShadow = [];
            if (prp.shadow) textShadow.push('2px 2px 4px rgba(0,0,0,0.4)');
            if (prp.glow) textShadow.push('0 0 8px rgba(0, 150, 255, 0.8)');
            if (textShadow.length > 0) p.style.textShadow = textShadow.join(', ');
            if (prp.outline) p.style.webkitTextStroke = '0.5px black';
        }

        if (node.list) {
            const listKey = `${node.list.numId}_${node.list.level}`;
            if (context.listCounters[listKey] === undefined) {
                context.listCounters[listKey] = node.list.start !== undefined ? parseInt(node.list.start) : 1;
            } else {
                context.listCounters[listKey]++;
            }

            const listSpan = document.createElement('span');
            listSpan.style.marginRight = '8px';
            listSpan.style.fontWeight = 'bold';
            
            let listText = node.list.text || "•";
            if (node.list.format === "decimal" || node.list.format === "lowerLetter") {
                listText = listText.replace(/%\d/g, context.listCounters[listKey]);
            } else if (node.list.format === "bullet") {
                if (listText.includes("%") || listText === "") listText = "•"; 
            }
            listSpan.innerText = listText;
            p.appendChild(listSpan);
        }

        if (node.unknown && node.unknown.includes('oMathPara')) {
            const mathBox = document.createElement('div');
            mathBox.className = 'fst-italic font-monospace p-2 border border-warning bg-light text-center';
            mathBox.innerHTML = '<i class="bi bi-calculator"></i> [Công thức Toán Học - Equation]';
            p.appendChild(mathBox);
        }

        if (node.children) {
            node.children.forEach((child, index) => {
                const childPath = `${currentPath}.children.${index}`;
                const childEl = buildHtmlFromWordNode(child, node, context, childPath);
                if (childEl) p.appendChild(childEl);
            });
        } else if (node.text) {
             p.innerText = node.text;
        }

        return p;
    }

    // ---------------------------------------------------------
    // 2. RUN (w:r) - Chứa Text
    // ---------------------------------------------------------
    if (node.type === 'run' || node.tag === 'w:r') {
        const span = document.createElement('span');
        
        if (node.text) {
            const textParts = node.text.split('\t');
            textParts.forEach((part, index) => {
                if (part) span.appendChild(document.createTextNode(part));
                if (index < textParts.length - 1) {
                    const hasDotLeader = parentNode && parentNode.layout && parentNode.layout.tabs && parentNode.layout.tabs.some(t => t.leader === 'dot');
                    const tabSpan = document.createElement('span');
                    tabSpan.className = 'badge bg-light text-secondary border mx-1';
                    tabSpan.innerHTML = hasDotLeader ? '&#8614; Tab <span style="letter-spacing: 2px;">......</span>' : '&#8614; Tab';
                    span.appendChild(tabSpan);
                }
            });
        }

        if (node.properties) {
            const prp = node.properties;
            if (prp.bold) span.style.fontWeight = 'bold';
            if (prp.italic) span.style.fontStyle = 'italic';
            if (prp.fontSize) span.style.fontSize = prp.fontSize + 'px';
            if (prp.color && prp.color !== 'auto') span.style.color = '#' + prp.color;
            if (prp.font && prp.font.ascii) span.style.fontFamily = `"${prp.font.ascii}", sans-serif`;
            else if (prp.resolvedFont) span.style.fontFamily = `"${prp.resolvedFont}", sans-serif`;

            let deco = [];
            if (prp.strike) deco.push('line-through');
            if (prp.underline && prp.underline !== 'none') deco.push('underline');
            if (deco.length > 0) span.style.textDecoration = deco.join(' ');

            let textShadow = [];
            if (prp.shadow) textShadow.push('2px 2px 4px rgba(0,0,0,0.4)');
            if (prp.glow) textShadow.push('0 0 8px rgba(0, 150, 255, 0.8)');
            if (textShadow.length > 0) span.style.textShadow = textShadow.join(', ');
            if (prp.outline) span.style.webkitTextStroke = '0.5px black';
        }

        if (node.references) {
            node.references.forEach(ref => {
                if (ref.type === 'ink') {
                    const inkBadge = document.createElement('span');
                    inkBadge.className = 'badge bg-dark mx-1';
                    inkBadge.innerHTML = `<i class="bi bi-pen"></i> Chữ ký/Vẽ tay (${ref.name || 'Ink'})`;
                    span.appendChild(inkBadge);
                }
            });
        }

        if (node.children) {
            node.children.forEach((child, index) => {
                const childPath = `${currentPath}.children.${index}`;
                const childEl = buildHtmlFromWordNode(child, node, context, childPath);
                if (childEl) span.appendChild(childEl);
            });
        }

        return span;
    }

    // ---------------------------------------------------------
    // 3. CÁC ĐỐI TƯỢNG ĐỒ HỌA
    // ---------------------------------------------------------
    const isGraphic = ['shape', 'smartart', 'smartartNode', 'smartartData', 'chart', 'image'].includes(node.type) || 
                      ['pic:pic', 'wps:wsp', 'a:graphicData', 'dgm:pt', 'dgm:dataModel'].includes(node.tag);

    if (isGraphic) {
        const box = document.createElement('div');
        box.className = 'ast-selectable border rounded p-2 my-2 bg-white shadow-sm';
        box.dataset.astPath = currentPath; 
        box.dataset.astType = `Graphic (${node.type || 'Object'})`; // Gắn nhãn
        
        let icon = 'bi-bounding-box';
        let label = 'Đối tượng đồ họa';
        let bgColor = 'bg-secondary';

        if (node.type === 'image' || node.tag === 'pic:pic') { icon = 'bi-image'; label = 'Hình ảnh (Image)'; bgColor = 'bg-success'; }
        if (node.type === 'chart') { icon = 'bi-bar-chart-fill'; label = 'Biểu đồ (Chart)'; bgColor = 'bg-primary'; }
        if (node.type === 'shape' || node.tag === 'wps:wsp') { icon = 'bi-triangle-fill'; label = `Hình khối (Shape)`; bgColor = 'bg-warning text-dark'; }
        if (node.type?.includes('smartart') || node.tag?.includes('dgm')) { icon = 'bi-diagram-3-fill'; label = 'SmartArt Node'; bgColor = 'bg-info text-dark'; }

        let titleInfo = node.properties && node.properties.name ? ` - ${node.properties.name}` : '';
        if (node.properties && node.properties.geometry) titleInfo += ` (${node.properties.geometry})`;

        box.innerHTML = `<div class="badge ${bgColor} mb-1"><i class="bi ${icon}"></i> ${label}${titleInfo}</div>`;

        if (node.text) {
            const txt = document.createElement('div');
            txt.className = 'fw-bold mt-1';
            txt.innerText = node.text;
            box.appendChild(txt);
        }

        if (node.children && node.children.length > 0) {
            const childContainer = document.createElement('div');
            childContainer.className = 'ms-3 mt-2 ps-2 border-start border-2 border-primary';
            node.children.forEach((c, cIdx) => {
                const cPath = `${currentPath}.children.${cIdx}`;
                const cEl = buildHtmlFromWordNode(c, node, context, cPath);
                if (cEl) childContainer.appendChild(cEl);
            });
            box.appendChild(childContainer);
        }

        if (node.layout && node.layout.mode === 'inline') {
            box.classList.add('d-inline-block');
            box.style.verticalAlign = 'middle';
            box.style.width = 'auto';
        }

        return box;
    }

    // ---------------------------------------------------------
    // 4. BẢNG (w:tbl)
    // ---------------------------------------------------------
    if (node.type === 'table') {
        const wrapper = document.createElement('div');
        wrapper.className = 'ast-selectable mb-3 overflow-auto';
        wrapper.dataset.astPath = currentPath; 
        wrapper.dataset.astType = "Table (Bảng)";

        const table = document.createElement('table');
        table.className = 'table table-bordered border-dark w-100 mb-0 bg-white';
        const tbody = document.createElement('tbody');
        
        if (node.children) {
            node.children.forEach((trNode, trIdx) => {
                if (trNode.type === 'table_row') {
                    const tr = document.createElement('tr');
                    const trPath = `${currentPath}.children.${trIdx}`; 
                    
                    tr.className = 'ast-selectable';
                    tr.dataset.astPath = trPath;
                    tr.dataset.astType = "Table Row (Hàng)";

                    if (trNode.children) {
                        trNode.children.forEach((tcNode, tcIdx) => {
                            if (tcNode.type === 'table_cell') {
                                const td = document.createElement('td');
                                const tdPath = `${trPath}.children.${tcIdx}`; 
                                
                                td.className = 'ast-selectable';
                                td.dataset.astPath = tdPath;
                                td.dataset.astType = "Table Cell (Ô)";

                                if (tcNode.layout && tcNode.layout.colspan) td.setAttribute('colspan', tcNode.layout.colspan);
                                if (tcNode.layout && tcNode.layout.rowspan === 'restart') td.setAttribute('rowspan', 1);
                                if (tcNode.layout && tcNode.layout.alignment) td.style.textAlign = tcNode.layout.alignment;
                                if (tcNode.layout && tcNode.layout.shading) td.style.backgroundColor = '#' + tcNode.layout.shading;

                                if (tcNode.children) {
                                    tcNode.children.forEach((c, cIdx) => {
                                        const cPath = `${tdPath}.children.${cIdx}`;
                                        const childEl = buildHtmlFromWordNode(c, trNode, context, cPath);
                                        if (childEl) td.appendChild(childEl);
                                    });
                                }
                                tr.appendChild(td);
                            }
                        });
                    }
                    tbody.appendChild(tr);
                }
            });
        }
        table.appendChild(tbody);
        wrapper.appendChild(table);
        return wrapper;
    }

    // ---------------------------------------------------------
    // 5. HYPERLINK
    // ---------------------------------------------------------
    if (node.type === 'hyperlink') {
        const a = document.createElement('a');
        a.className = 'ast-selectable';
        a.dataset.astPath = currentPath;
        a.dataset.astType = "Hyperlink (Liên kết)";
        a.style.color = '#0d6efd';
        a.style.textDecoration = 'underline';
        
        if (node.references && node.references[0] && node.references[0].url) {
            a.href = node.references[0].url;
            a.target = "_blank";
            a.title = node.references[0].url;
        } else {
            a.href = "#"; 
            a.title = "Internal Link / Mục lục";
        }
        
        if (node.children) {
            node.children.forEach((child, idx) => {
                const childEl = buildHtmlFromWordNode(child, node, context, `${currentPath}.children.${idx}`);
                if (childEl) a.appendChild(childEl);
            });
        }
        return a;
    }

    // ---------------------------------------------------------
    // 6. SDT (Mục Lục TOC, Content Controls)
    // ---------------------------------------------------------
    if (node.type === 'sdt') {
        const div = document.createElement('div');
        div.className = 'p-3 bg-light border border-secondary border-dashed mb-2 ast-selectable';
        div.dataset.astPath = currentPath; 
        div.dataset.astType = "TOC / Control (Mục lục)";
        
        if (node.children) {
            node.children.forEach((child, index) => {
                const childPath = `${currentPath}.children.${index}`;
                const childEl = buildHtmlFromWordNode(child, node, context, childPath);
                if (childEl) div.appendChild(childEl);
            });
        }
        return div;
    }

    // ---------------------------------------------------------
    // 7. PAGE BREAKS
    // ---------------------------------------------------------
    if (node.type === 'pageBreak' || node.type === 'renderedPageBreak') {
        const pb = document.createElement('div');
        pb.className = 'd-flex align-items-center my-3 ast-placeholder w-100 opacity-50';
        pb.innerHTML = `<hr class="flex-grow-1 border-secondary" style="border-top-style: dashed; margin: 0;"><span class="badge bg-secondary mx-3"><i class="bi bi-scissors"></i> Trạng/Dòng mới</span><hr class="flex-grow-1 border-secondary" style="border-top-style: dashed; margin: 0;">`;
        return pb;
    }

    // ---------------------------------------------------------
    // 8. CÁC THẺ WRAPPER CHUNG
    // ---------------------------------------------------------
    if (node.children) {
        const fragment = document.createDocumentFragment();
        node.children.forEach((child, index) => {
            const childPath = `${currentPath}.children.${index}`;
            const childEl = buildHtmlFromWordNode(child, node, context, childPath);
            if (childEl) fragment.appendChild(childEl);
        });
        return fragment;
    }

    return null;
}