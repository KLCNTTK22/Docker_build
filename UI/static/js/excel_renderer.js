/**
 * EXCEL RENDERER - V5 (SEPARATED FILE & DEBUG MODE)
 */
const ExcelRenderer = (function () {
    function escapeHtml(unsafe) {
        if (unsafe === undefined || unsafe === null || unsafe === "") return "";
        return unsafe.toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function initHoverTooltip(container) {
        let tooltip = document.getElementById('ast-inspector-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'ast-inspector-tooltip';
            tooltip.style.cssText = 'position: absolute; display: none; background: rgba(33, 37, 41, 0.95); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-family: monospace; z-index: 10000; pointer-events: none; box-shadow: 0 4px 6px rgba(0,0,0,0.3); white-space: nowrap; line-height: 1.5; border: 1px solid #495057;';
            document.body.appendChild(tooltip);
        }

        container.addEventListener('mousemove', function (e) {
            const target = e.target.closest('.ast-selectable');
            if (target) {
                tooltip.style.display = 'block';
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY + 15) + 'px';

                const type = target.dataset.astType || 'Element';
                const path = target.dataset.astPath || '';
                const extra = target.dataset.extraInfo || '';

                tooltip.innerHTML = `<span style="color: #20c997; font-weight: bold;">[${type}]</span><br>
                                     <span style="color: #dee2e6;">Path: ${path}</span>
                                     ${extra ? `<br><span style="color: #ffc107;">${extra}</span>` : ''}`;

                document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
                target.classList.add('ast-hovered');
            } else {
                tooltip.style.display = 'none';
                document.querySelectorAll('.ast-selectable').forEach(el => el.classList.remove('ast-hovered'));
            }
        });

        container.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
    }

    function render(ast, containerId) {

        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        container.innerHTML = '';
        container.style.backgroundColor = '#f8f9fa';
        container.style.padding = '15px';

        initHoverTooltip(container);

        if (!ast || !ast.children) {
            container.innerHTML = '<div class="alert alert-danger">Lỗi: Dữ liệu JSON bị rỗng hoặc không có node children.</div>';
            return;
        }


        const navTabs = document.createElement('ul');
        navTabs.className = 'nav nav-tabs mb-3';
        navTabs.style.borderBottom = '2px solid #198754';

        const tabContent = document.createElement('div');
        tabContent.className = 'excel-tab-content-wrapper';

        let globalObjects = [];
        let sheetIndexDisplay = 0;

        ast.children.forEach((child, astIndex) => {
            const childPath = `children.${astIndex}`;
            const childType = child.type || child.tag;


            if (childType === 'worksheet') {
                const sheetName = child.properties?.name || `Sheet ${sheetIndexDisplay + 1}`;
                const tabId = `sheet-tab-${astIndex}`;
                const isActive = sheetIndexDisplay === 0;


                // 1. NÚT TAB
                const li = document.createElement('li');
                li.className = 'nav-item';

                const tabBtn = document.createElement('button');
                tabBtn.className = `nav-link custom-excel-tab ${isActive ? 'active fw-bold text-success' : 'text-secondary'}`;
                tabBtn.style.cursor = 'pointer';
                tabBtn.innerHTML = `<i class="bi bi-grid-3x3"></i> ${escapeHtml(sheetName)}`;

                tabBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    document.querySelectorAll('.custom-excel-pane').forEach(el => el.style.display = 'none');
                    document.querySelectorAll('.custom-excel-tab').forEach(el => {
                        el.classList.remove('active', 'text-success', 'fw-bold');
                        el.classList.add('text-secondary');
                    });
                    document.getElementById(tabId).style.display = 'block';
                    tabBtn.classList.remove('text-secondary');
                    tabBtn.classList.add('active', 'text-success', 'fw-bold');
                });

                li.appendChild(tabBtn);
                navTabs.appendChild(li);

                // 2. NỘI DUNG TAB
                const pane = document.createElement('div');
                pane.className = `custom-excel-pane`;
                pane.id = tabId;
                pane.style.display = isActive ? 'block' : 'none';
                pane.style.animation = 'fadeIn 0.3s';

                const sheetHeader = document.createElement('div');
                sheetHeader.className = 'ast-selectable alert alert-success p-2 mb-3 shadow-sm d-flex justify-content-between align-items-center';
                sheetHeader.dataset.astPath = childPath;
                sheetHeader.dataset.astType = `Worksheet (${sheetName})`;

                let sheetExtra = [];
                if (child.section?.autoFilter) sheetExtra.push('<i class="bi bi-funnel-fill"></i> AutoFilter');
                if (child.section?.conditionalFormatting?.length > 0) sheetExtra.push('<i class="bi bi-palette-fill"></i> C.Format');

                sheetHeader.innerHTML = `
                    <div><strong><i class="bi bi-file-earmark-spreadsheet"></i> Sheet: ${escapeHtml(sheetName)}</strong> <span class="text-muted ms-2 small">(Click để chấm toàn Sheet)</span></div>
                    <div>${sheetExtra.length > 0 ? '<span class="badge bg-success">' + sheetExtra.join('</span> <span class="badge bg-info text-dark">') + '</span>' : ''}</div>
                `;
                pane.appendChild(sheetHeader);

                // 3. VẼ BẢNG EXCEL
                const tableWrapper = document.createElement('div');
                tableWrapper.className = 'table-responsive bg-white border shadow-sm';
                tableWrapper.style.maxHeight = '600px';

                const table = document.createElement('table');
                table.className = 'table table-bordered table-sm mb-0 ast-table';
                table.style.whiteSpace = 'nowrap';
                table.style.fontSize = '13px';

                const tbody = document.createElement('tbody');
                let hasData = false;
                let parsedRows = 0;

                if (child.children) {
                    child.children.forEach((row, rowIdx) => {
                        if (row.type !== 'row' && row.tag !== 'row') {
                            return;
                        }

                        hasData = true;
                        parsedRows++;

                        const rowPath = `${childPath}.children.${rowIdx}`;
                        const tr = document.createElement('tr');

                        let isHidden = row.layout?.hidden === true;
                        if (isHidden) {
                            tr.style.opacity = '0.4';
                            tr.style.backgroundColor = '#f8f9fa';
                        }

                        const th = document.createElement('th');
                        th.className = 'ast-selectable bg-light text-center align-middle text-muted border-end border-2';
                        th.style.width = '60px';
                        th.dataset.astPath = rowPath;
                        th.dataset.astType = `Row (Dòng ${row.attributes?.r || rowIdx + 1})`;
                        th.innerHTML = (isHidden ? '<i class="bi bi-eye-slash-fill text-danger" title="Dòng ẩn"></i> ' : '') + (row.attributes?.r || rowIdx + 1);
                        tr.appendChild(th);

                        if (row.children) {
                            row.children.forEach((cell, cellIdx) => {
                                if (cell.type !== 'cell' && cell.tag !== 'c') return;

                                const cellPath = `${rowPath}.children.${cellIdx}`;
                                const td = document.createElement('td');
                                td.className = 'ast-selectable';
                                td.dataset.astPath = cellPath;

                                const coord = cell.attributes?.r || `Col ${cellIdx + 1}`;
                                td.dataset.astType = `Cell (${coord})`;

                                let value = '', formula = '';
                                if (cell.children) {
                                    cell.children.forEach(v => {
                                        if (v.tag === 'v' || v.type === 'value') value = v.text ?? v.value ?? "";
                                        if (v.tag === 'f' || v.type === 'formula') formula = v.text ?? v.value ?? "";
                                    });
                                }

                                if (formula || cell.properties?.is_dynamic_formula) {
                                    td.dataset.extraInfo = `Công thức: ${escapeHtml(formula)}`;
                                    td.style.backgroundColor = '#f0fdf4';
                                    td.innerHTML = `<span class="text-success fw-bold me-1"><i>ƒx</i></span> ${escapeHtml(value)}`;
                                } else {
                                    td.dataset.extraInfo = `Giá trị: ${escapeHtml(value)}`;
                                    td.innerHTML = escapeHtml(value) || '&nbsp;';
                                }

                                if (cell.style?.fill?.has_color || rowIdx === 0) {
                                    td.style.backgroundColor = '#e9ecef';
                                    td.style.fontWeight = 'bold';
                                }
                                tr.appendChild(td);
                            });
                        }
                        tbody.appendChild(tr);
                    });
                }


                if (!hasData) tbody.innerHTML = '<tr><td class="text-center p-4 text-muted">Sheet này trống hoặc không có dòng (row) hợp lệ.</td></tr>';

                table.appendChild(tbody);
                tableWrapper.appendChild(table);
                pane.appendChild(tableWrapper);
                tabContent.appendChild(pane);

                sheetIndexDisplay++;
            } else if (childType === 'chart' || childType === 'chartSpace' || childType === 'pivotTable' || childType === 'pivotTableDefinition') {
                globalObjects.push({ node: child, path: childPath });
            }
        });

        // 4. TAB CHO GLOBAL OBJECTS (CHART / PIVOT)
        if (globalObjects.length > 0) {
            const tabId = 'global-objects-tab';
            const li = document.createElement('li');
            li.className = 'nav-item';

            const tabBtn = document.createElement('button');
            tabBtn.className = `nav-link custom-excel-tab text-primary fw-bold`;
            tabBtn.innerHTML = `<i class="bi bi-pie-chart-fill"></i> Biểu đồ / Pivot`;

            tabBtn.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.custom-excel-pane').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.custom-excel-tab').forEach(el => {
                    el.classList.remove('active', 'text-success', 'fw-bold');
                    el.classList.add('text-secondary');
                });
                document.getElementById(tabId).style.display = 'block';
                tabBtn.classList.remove('text-secondary');
                tabBtn.classList.add('active', 'text-success', 'fw-bold');
            });

            li.appendChild(tabBtn);
            navTabs.appendChild(li);

            const pane = document.createElement('div');
            pane.className = 'custom-excel-pane p-3';
            pane.id = tabId;
            pane.style.display = 'none';
            pane.style.animation = 'fadeIn 0.3s';

            const rowDiv = document.createElement('div');
            rowDiv.className = 'row g-3';

            globalObjects.forEach(obj => {
                const col = document.createElement('div');
                col.className = 'col-md-6';

                const card = document.createElement('div');
                card.className = 'ast-selectable card h-100 shadow-sm border-primary';
                card.dataset.astPath = obj.path;

                const objType = obj.node.type || obj.node.tag;
                if (objType === 'chart' || objType === 'chartSpace') {
                    card.dataset.astType = "Chart (Biểu đồ)";
                    const types = obj.node.properties?.chart_types?.join(', ') || 'Unknown';

                    // Lấy thông tin Series của Chart
                    let seriesHtml = '';
                    if (obj.node.children) {
                        obj.node.children.forEach(s => {
                            if (s.tag === 'ser' || s.type === 'chart_series') {
                                let nRef = s.properties?.name_ref || 'N/A';
                                let vRef = s.properties?.value_ref || 'N/A';
                                seriesHtml += `<div class="badge bg-light text-dark border mb-1 d-block text-start text-truncate"><i class="bi bi-bookmark"></i> Name: ${escapeHtml(nRef)} <br> <i class="bi bi-database"></i> Value: ${escapeHtml(vRef)}</div>`;
                            }
                        });
                    }

                    card.innerHTML = `
                        <div class="card-body text-center">
                            <i class="bi bi-bar-chart-fill display-4 text-primary mb-2"></i>
                            <h5 class="fw-bold">Biểu đồ (${types})</h5>
                            <hr class="my-2">
                            <div class="text-start small fw-bold text-muted mb-1">Dữ liệu nguồn (Series):</div>
                            ${seriesHtml || '<span class="text-muted small">Không rõ nguồn</span>'}
                        </div>
                    `;
                } else {
                    card.dataset.astType = "Pivot Table";

                    // Lấy thông tin Fields của Pivot Table
                    let dataFieldsHtml = '';
                    if (obj.node.properties?.data_fields) {
                        obj.node.properties.data_fields.forEach(df => {
                            dataFieldsHtml += `<span class="badge bg-info text-dark me-1 mb-1 shadow-sm"><i class="bi bi-calculator"></i> ${escapeHtml(df.name)} (ID: ${df.fld}) - ${df.subtotal}</span>`;
                        });
                    }
                    let rowColsHtml = '';
                    let rowsF = obj.node.properties?.row_fields_index || [];
                    let colsF = obj.node.properties?.col_fields_index || [];
                    if (rowsF.length > 0) rowColsHtml += `<span class="badge bg-secondary me-1">Row IDs: ${rowsF.join(', ')}</span>`;
                    if (colsF.length > 0) rowColsHtml += `<span class="badge bg-secondary me-1">Col IDs: ${colsF.join(', ')}</span>`;

                    card.innerHTML = `
                        <div class="card-body text-center">
                            <i class="bi bi-table display-4 text-info mb-2"></i>
                            <h5 class="fw-bold">Pivot Table</h5>
                            <p class="small text-muted mb-2">Vùng dữ liệu: <code>${obj.node.layout?.ref || 'N/A'}</code></p>
                            <div class="text-start">
                                <div class="small fw-bold text-muted mb-1">Khu vực Row / Column:</div>
                                <div>${rowColsHtml || '<span class="text-muted small">Trống</span>'}</div>
                                <div class="small fw-bold text-muted mt-2 mb-1">Khu vực Data (Values):</div>
                                <div>${dataFieldsHtml || '<span class="text-muted small">Trống</span>'}</div>
                            </div>
                        </div>
                    `;
                }

                col.appendChild(card);
                rowDiv.appendChild(col);
            });

            pane.appendChild(rowDiv);
            tabContent.appendChild(pane);
        }

        container.appendChild(navTabs);
        container.appendChild(tabContent);
    }

    return { render };
})();