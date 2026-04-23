from flask import Flask, render_template, request, jsonify
import os
import json

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Đường dẫn dùng chung (Shared Volume với n8n)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DATA_DIR = os.path.join(PROJECT_ROOT, 'shared_workspace')
os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Hỗ trợ tạo folder theo môn
SUPPORTED_SUBJECTS = ['grade', 'submit', 'rubric', 'tmp', 'grade']
for sub in SUPPORTED_SUBJECTS:
        os.makedirs(os.path.join(BASE_DATA_DIR, sub), exist_ok=True)

# ==========================================
# 1. ROUTES ĐIỀU HƯỚNG GIAO DIỆN (FRONTEND)
# ==========================================

@app.route('/')
def home():
    return render_template('home.html', active_page='home')

@app.route('/create')
def create_rubric():
    return render_template('create.html', active_page='create')

# Trang Quản lý Rubric
@app.route('/rubrics')
def manage_rubrics():
    return render_template('rubrics.html', active_page='rubrics')

# Đổi route exams thành Cuộc Thi
@app.route('/exams')
def list_exams():
    return render_template('list_exams.html', active_page='exams')

# Route mới cho chức năng Chấm Local
@app.route('/grade-local')
def grade_local():
    return render_template('grade_local.html', active_page='grade_local')

# Placeholder cho chức năng Chấm AI (làm sau)
@app.route('/grade-ai')
def grade_ai():
    return render_template('grade_ai.html', active_page='grade_ai')

# Route xem Kết Quả (Vẫn giữ cấu trúc cũ cho app.js xử lý sau này)
@app.route('/subject/<subject_name>')
def view_results(subject_name):
    if subject_name not in SUPPORTED_SUBJECTS:
        return "Môn học không được hỗ trợ", 404
    return render_template('results.html', active_page='results', subject=subject_name)


# ==========================================
# 2. API ENDPOINTS (Dành cho app.js gọi)
# ==========================================

@app.route('/api/<subject_name>/list_files', methods=['GET'])
def api_list_files(subject_name):
    """Trả về danh sách file rubric và file bài làm (ast) của sinh viên"""
    if subject_name not in SUPPORTED_SUBJECTS:
        return jsonify({"error": "Invalid subject"}), 400
        
    try:
        rubrics_dir = os.path.join(BASE_DATA_DIR, subject_name, 'rubrics')
        students_dir = os.path.join(BASE_DATA_DIR, subject_name, 'students')
        
        # Chỉ lấy file .json
        rubrics = [f for f in os.listdir(rubrics_dir) if f.endswith('.json')]
        students = [f for f in os.listdir(students_dir) if f.endswith('.json')]
        
        return jsonify({
            "rubrics": rubrics,
            "students": students
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/<subject_name>/load_data', methods=['GET'])
def api_load_data(subject_name):
    """Đọc dữ liệu Rubric, AST và Report từ file JSON"""
    if subject_name not in SUPPORTED_SUBJECTS:
        return jsonify({"error": "Invalid subject"}), 400
        
    rubric_file = request.args.get('rubric')
    student_file = request.args.get('student')
    
    data = {
        "rubric": [],
        "ast": {},
        "report": {}
    }
    
    try:
        # 1. Đọc Rubric
        if rubric_file:
            r_path = os.path.join(BASE_DATA_DIR, subject_name, 'rubrics', rubric_file)
            if os.path.exists(r_path):
                with open(r_path, 'r', encoding='utf-8') as f:
                    data['rubric'] = json.load(f)
                    
        # 2. Đọc AST của sinh viên
        if student_file:
            s_path = os.path.join(BASE_DATA_DIR, subject_name, 'students', student_file)
            if os.path.exists(s_path):
                with open(s_path, 'r', encoding='utf-8') as f:
                    data['ast'] = json.load(f)
                    
            # 3. Đọc Report chấm điểm (Giả định tên file report giống tên file student)
            rep_path = os.path.join(BASE_DATA_DIR, subject_name, 'results', student_file)
            if os.path.exists(rep_path):
                with open(rep_path, 'r', encoding='utf-8') as f:
                    data['report'] = json.load(f)
                    
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/<subject_name>/save_rubric', methods=['POST'])
def api_save_rubric(subject_name):
    """Lưu lại nội dung Rubric sau khi giảng viên chỉnh sửa trên UI"""
    if subject_name not in SUPPORTED_SUBJECTS:
        return jsonify({"status": "error", "message": "Invalid subject"}), 400
        
    req_data = request.json
    filename = req_data.get('filename')
    rubric_data = req_data.get('data')
    
    if not filename or not rubric_data:
        return jsonify({"status": "error", "message": "Missing filename or data"}), 400
        
    try:
        r_path = os.path.join(BASE_DATA_DIR, subject_name, 'rubrics', filename)
        with open(r_path, 'w', encoding='utf-8') as f:
            json.dump(rubric_data, f, ensure_ascii=False, indent=4)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)