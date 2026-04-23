import sys
import os
import json
import PyPDF2
import docx

# Khai báo đường dẫn để Python hiểu cấu trúc thư mục
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import đầy đủ các Parser và Grader cho 3 định dạng
from Parser.docx_parser.core import parse_docx
from Grade.word_grade import grade_submission as grade_word

from Parser.excel_parser.core import parse_xlsx
from Grade.excel_grade import grade_submission as grade_excel

from Parser.pptx_parser.core import parse_pptx
from Grade.pptx_grade import grade_submission as grade_pptx


def extract_file_text(file_path):
    text = ""
    try:
        if file_path.lower().endswith('.pdf'):
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    if page.extract_text():
                        text += page.extract_text() + "\n"
        elif file_path.lower().endswith('.docx'):
            import docx
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            return {"error": "Định dạng file đề không được hỗ trợ để trích xuất chữ."}
            
        return {"text": text.strip()}
    except Exception as e:
        return {"error": str(e)}

def main():
    # SỬA LỖI Ở ĐÂY: Chỉ check < 2 để cho phép lệnh grade_local đi qua
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Thiếu tham số dòng lệnh."}))
        sys.exit(0)

    command = sys.argv[1].lower()

    try:
        # ==========================================
        # LỆNH GRADE_LOCAL: Chấm tự động toàn bộ thư mục
        # ==========================================
        if command == "grade_local":
            # Khởi tạo đường dẫn tuyệt đối
            submit_dir = "/shared_workspace/submit"
            rubric_dir = "/shared_workspace/rubric"
            result_dir = "/shared_workspace/result"

            # Đảm bảo các thư mục tồn tại để không báo lỗi
            os.makedirs(submit_dir, exist_ok=True)
            os.makedirs(rubric_dir, exist_ok=True)
            os.makedirs(result_dir, exist_ok=True)

            # 1. Load và phân loại Rubrics
            rubrics_map = {}
            for r_file in os.listdir(rubric_dir):
                if r_file.endswith('.json'):
                    r_path = os.path.join(rubric_dir, r_file)
                    with open(r_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name_lower = r_file.lower()
                        # Map rubric dựa vào từ khóa trong tên file
                        if 'word' in name_lower or 'docx' in name_lower:
                            rubrics_map['.docx'] = data
                        elif 'excel' in name_lower or 'xlsx' in name_lower:
                            rubrics_map['.xlsx'] = data
                        elif 'powerpoint' in name_lower or 'pptx' in name_lower or 'power' in name_lower:
                            rubrics_map['.pptx'] = data

            if not rubrics_map:
                print(json.dumps({"error": "Không tìm thấy file rubric nào hợp lệ trong thư mục rubric."}))
                sys.exit(0)

            # 2. Xử lý chấm điểm từng file trong submit
            summary_report = []

            for s_file in os.listdir(submit_dir):
                s_path = os.path.join(submit_dir, s_file)
                if not os.path.isfile(s_path):
                    continue

                ext = os.path.splitext(s_file)[1].lower()
                if ext not in ['.docx', '.xlsx', '.pptx']:
                    continue # Bỏ qua các file rác không phải Office

                result_path = os.path.join(result_dir, f"{s_file}.json")
                file_summary = {"file_name": s_file, "status": "processing"}

                try:
                    if ext not in rubrics_map:
                        raise ValueError(f"Không có rubric tương ứng cho đuôi {ext}")

                    rubric = rubrics_map[ext]
                    ast = None
                    grade_result = None

                    # Parse và Grade
                    if ext == '.docx':
                        ast = parse_docx(s_path, clean=True)
                        grade_result = grade_word(rubric, ast)
                    elif ext == '.xlsx':
                        ast = parse_xlsx(s_path, clean=True)
                        grade_result = grade_excel(rubric, ast)
                    elif ext == '.pptx':
                        ast = parse_pptx(s_path, clean=True)
                        grade_result = grade_pptx(rubric, ast)

                    # Lấy Metadata
                    props = grade_result.get("properties", {})
                    metadata = props.get("metadata", {})
                    core_props = props.get("core_properties", {})
                    created_by = metadata.get("creator") or core_props.get("creator") or core_props.get("dc:creator") or ""
                    updated_by = metadata.get("lastModifiedBy") or core_props.get("lastModifiedBy") or core_props.get("cp:lastModifiedBy") or ""

                    # Lưu file kết quả chi tiết
                    with open(result_path, 'w', encoding='utf-8') as f:
                        json.dump(grade_result, f, ensure_ascii=False)

                    # Cập nhật báo cáo tóm tắt
                    file_summary.update({
                        "status": "success",
                        "result_path": result_path,
                        "final_score": grade_result.get("final_score", 0),
                        "created_by": created_by,
                        "updated_by": updated_by
                    })

                except Exception as e:
                    file_summary.update({
                        "status": "error",
                        "error_msg": str(e)
                    })

                summary_report.append(file_summary)

            # 3. Trả kết quả mảng tổng hợp cho n8n
            print(json.dumps(summary_report, ensure_ascii=False))

        # ==========================================
        # CÁC LỆNH CŨ (PARSE, EXTRACT_TEXT, GRADE LẺ)
        # ==========================================
        else:
            # SỬA LỖI Ở ĐÂY: Dời việc lấy file_path vào trong block này
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Thiếu tham số dòng lệnh. Cú pháp: python n8n_bridge.py [parse/grade] [file_path]"}))
                sys.exit(0)
            
            file_path = sys.argv[2]

            if not os.path.exists(file_path):
                print(json.dumps({"error": f"Không tìm thấy file tại: {file_path}"}))
                sys.exit(0)

            if command == "parse":
                ast = None
                if file_path.lower().endswith('.docx'):
                    ast = parse_docx(file_path, clean=True)
                elif file_path.lower().endswith('.xlsx'):
                    ast = parse_xlsx(file_path, clean=True)
                elif file_path.lower().endswith('.pptx'):
                    ast = parse_pptx(file_path, clean=True)
                else:
                    print(json.dumps({"error": "Định dạng file không được hỗ trợ để parse."}))
                    sys.exit(0)
                
                print(json.dumps(ast, ensure_ascii=False))

            elif command == "extract_text":
                result = extract_file_text(file_path)
                print(json.dumps(result, ensure_ascii=False))

            elif command == "grade":
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Thiếu file rubric. Cú pháp: python n8n_bridge.py grade [file_path] [rubric_path]"}))
                    sys.exit(0)
                    
                rubric_path = sys.argv[3]
                if not os.path.exists(rubric_path):
                    print(json.dumps({"error": f"Không tìm thấy file rubric tại: {rubric_path}"}))
                    sys.exit(0)

                with open(rubric_path, 'r', encoding='utf-8') as f:
                    rubric = json.load(f)
                
                result = None
                if file_path.lower().endswith('.docx'):
                    ast = parse_docx(file_path, clean=True)
                    result = grade_word(rubric, ast)
                elif file_path.lower().endswith('.xlsx'):
                    ast = parse_xlsx(file_path, clean=True)
                    result = grade_excel(rubric, ast)
                elif file_path.lower().endswith('.pptx'):
                    ast = parse_pptx(file_path, clean=True)
                    result = grade_pptx(rubric, ast)
                else:
                    print(json.dumps({"error": "Định dạng file không được hỗ trợ để chấm điểm."}))
                    sys.exit(0)
                
                props = result.get("properties", {})
                metadata = props.get("metadata", {})
                core_props = props.get("core_properties", {})

                created_by = metadata.get("creator") or core_props.get("creator") or core_props.get("dc:creator") or ""
                updated_by = metadata.get("lastModifiedBy") or core_props.get("lastModifiedBy") or core_props.get("cp:lastModifiedBy") or ""
                
                base_filename = os.path.splitext(os.path.basename(file_path))[0]
                grade_dir = "/shared_workspace/grade"
                os.makedirs(grade_dir, exist_ok=True)
                result_path = os.path.join(grade_dir, f"result_{base_filename}.json")
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False)
                summary = {
                    "file_path": result_path,
                    "final_score": result.get("final_score", 0),
                    "metadata_clean": {
                        "created_by": created_by,
                        "updated_by": updated_by
                    }
                }
                print(json.dumps(summary, ensure_ascii=False))
                
            else:
                print(json.dumps({"error": f"Lệnh không hợp lệ: {command}"}))
                sys.exit(0)

    except Exception as e:
        # Bắt toàn bộ lỗi runtime và trả về chuẩn JSON cho n8n
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(0)

if __name__ == "__main__":
    main()