import sys
import json
import os
from jinja2 import Template
from weasyprint import HTML

def format_value(val):
    """
    Rút gọn các giá trị phức tạp (như nguyên một block JSON AST của Word)
    để không làm vỡ giao diện PDF.
    """
    if val is None:
        return "N/A"
    if isinstance(val, (dict, list)):
        return "[Cấu trúc đối tượng phức tạp]"
    return str(val)

def normalize_grading_data(raw_data, info_str):
    """
    Chuẩn hóa các định dạng JSON khác nhau thành một format chung.
    Hỗ trợ trích xuất sâu vào mảng details con để làm báo cáo chi tiết hơn.
    """
    parts = [p.strip() for p in info_str.split('-')]
    
    normalized = {
        "student_id": parts[0] if len(parts) > 0 else "N/A",
        "student_name": parts[1] if len(parts) > 1 else "N/A",
        "student_class": parts[2] if len(parts) > 2 else "N/A",
        "final_score": raw_data.get("final_score", 0),
        "details": []
    }

    # Xử lý format có chứa key "report" (Thường là Word / Excel)
    if "report" in raw_data:
        for item in raw_data["report"]:
            sub_details = []
            # Bóc tách mảng details lồng bên trong
            for sub in item.get("details", []):
                sub_details.append({
                    "desc": sub.get("desc", ""),
                    "passed": sub.get("passed"),
                    "expected": format_value(sub.get("expected")),
                    "actual": format_value(sub.get("actual"))
                })
                
            normalized["details"].append({
                "criteria": item.get("criteria", ""),
                "status": item.get("status", ""),
                "score": f"{item.get('score', 0)}/{item.get('max_score', 0)}",
                "msg": item.get("message") or "",
                "sub_details": sub_details
            })
            
    # Xử lý format mảng "details" nằm ngay ở root (Thường là PowerPoint)
    elif "details" in raw_data and isinstance(raw_data["details"], list):
        for item in raw_data["details"]:
            # Ghép group_name và description để tạo tiêu chí chi tiết
            criteria_name = item.get("group_name", "")
            if item.get("description"):
                criteria_name += f": {item.get('description')}"
                
            normalized["details"].append({
                "criteria": criteria_name,
                "status": item.get("status", ""),
                "score": f"{item.get('awarded_points', 0)}/{item.get('max_points', 0)}",
                "msg": item.get("message") or "",
                "sub_details": [] # Format này thường ghi thẳng lý do vào message
            })
            
    return normalized

HTML_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: 'DejaVu Sans', sans-serif; padding: 20px; font-size: 13px; color: #333; }
        .header { border-bottom: 2px solid #2c3e50; margin-bottom: 20px; padding-bottom: 10px; }
        .header h2 { color: #2c3e50; margin-bottom: 5px; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 10px; }
        .score-highlight { font-size: 18px; color: #e74c3c; font-weight: bold; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; }
        th { background: #f8f9fa; color: #2c3e50; font-weight: bold; }
        
        /* Trạng thái */
        .SUCCESS, .PASSED, .TRUE { color: #27ae60; font-weight: bold; }
        .FAILED, .FALSE { color: #c0392b; font-weight: bold; }
        .PARTIAL { color: #f39c12; font-weight: bold; }
        
        /* Chi tiết con (Sub-details) */
        .sub-details { margin: 8px 0 0 0; padding-left: 20px; font-size: 12px; color: #555; }
        .sub-details li { margin-bottom: 4px; }
        .val-box { background: #f4f6f7; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        .msg-box { font-style: italic; color: #7f8c8d; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>BÁO CÁO CHẤM ĐIỂM TỰ ĐỘNG</h2>
        <div class="info-grid">
            <div>
                <p><strong>Họ và tên:</strong> {{ d.student_name }}</p>
                <p><strong>Mã SV:</strong> {{ d.student_id }}</p>
                <p><strong>Lớp:</strong> {{ d.student_class }}</p>
            </div>
            <div style="text-align: right;">
                <p><strong>TỔNG ĐIỂM:</strong> <span class="score-highlight">{{ d.final_score }}</span></p>
            </div>
        </div>
    </div>
    
    <table>
        <tr>
            <th style="width: 40%;">Tiêu chí (Criteria)</th>
            <th style="width: 15%;">Trạng thái</th>
            <th style="width: 10%;">Điểm</th>
            <th style="width: 35%;">Chi tiết & Ghi chú</th>
        </tr>
        {% for item in d.details %}
        <tr>
            <td>{{ item.criteria }}</td>
            <td class="{{ item.status.split('/')[0] | upper }}">{{ item.status }}</td>
            <td><strong>{{ item.score }}</strong></td>
            <td>
                {% if item.msg %}
                    <div class="msg-box">{{ item.msg }}</div>
                {% endif %}
                
                {% if item.sub_details %}
                    <ul class="sub-details">
                    {% for sub in item.sub_details %}
                        <li>
                            {{ sub.desc }}: 
                            {% if sub.passed == true or sub.passed == 'SUCCESS' or sub.passed == 'TRUE' %}
                                <span class="SUCCESS">Đạt</span>
                            {% elif sub.passed == 'PARTIAL' %}
                                <span class="PARTIAL">Một phần</span>
                            {% else %}
                                <span class="FAILED">Không đạt</span>
                            {% endif %}
                            
                            {% if not (sub.passed == true or sub.passed == 'SUCCESS' or sub.passed == 'TRUE') %}
                                <br>
                                {% if sub.expected != 'N/A' %}&bull; Cần: <span class="val-box">{{ sub.expected }}</span><br>{% endif %}
                                {% if sub.actual != 'N/A' %}&bull; Thực tế: <span class="val-box">{{ sub.actual }}</span>{% endif %}
                            {% endif %}
                        </li>
                    {% endfor %}
                    </ul>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def export_result_to_pdf(info_str, input_json_path, output_pdf_path):
    if not os.path.exists(input_json_path):
        raise FileNotFoundError(f"JSON file not found at {input_json_path}")

    with open(input_json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    data = normalize_grading_data(raw, info_str)
    template = Template(HTML_TEMPLATE)
    html_content = template.render(d=data)
    
    HTML(string=html_content).write_pdf(output_pdf_path)
    return output_pdf_path

def export_result_to_pdf_from_dict(info_str, raw_data, output_pdf_path):
    data = normalize_grading_data(raw_data, info_str)
    template = Template(HTML_TEMPLATE)
    html_content = template.render(d=data)
    
    HTML(string=html_content).write_pdf(output_pdf_path)
    return output_pdf_path

if __name__ == "__main__":
    if len(sys.argv) > 3:
        info = sys.argv[1]
        inp = sys.argv[2]
        out = sys.argv[3]
        export_result_to_pdf(info, inp, out)
        print(f"Success: PDF generated at {out}")
    else:
        print("Usage: python result_to_pdf.py <info> <input_json> <output_pdf>")