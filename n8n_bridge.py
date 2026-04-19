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
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Thiếu tham số dòng lệnh. Cú pháp: python n8n_bridge.py [parse/grade] [file_path]"}))
        sys.exit(1)

    command = sys.argv[1].lower()
    file_path = sys.argv[2]

    if not os.path.exists(file_path):
        print(json.dumps({"error": f"Không tìm thấy file tại: {file_path}"}))
        sys.exit(1)

    try:
        # ==========================================
        # LỆNH PARSE: Sinh JSON AST từ file
        # ==========================================
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
                sys.exit(1)
            
            # In ra màn hình để n8n nhận JSON
            print(json.dumps(ast, ensure_ascii=False))

        # ==========================================
        # LỆNH EXTRACT_TEXT: Trích xuất chữ từ Đề thi (PDF/Word)
        # ==========================================
        elif command == "extract_text":
            result = extract_file_text(file_path)
            print(json.dumps(result, ensure_ascii=False))

        # ==========================================
        # LỆNH GRADE: Chấm điểm bài làm theo Rubric
        # ==========================================
        elif command == "grade":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Thiếu file rubric. Cú pháp: python n8n_bridge.py grade [file_path] [rubric_path]"}))
                sys.exit(1)
                
            rubric_path = sys.argv[3]
            if not os.path.exists(rubric_path):
                print(json.dumps({"error": f"Không tìm thấy file rubric tại: {rubric_path}"}))
                sys.exit(1)

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
                sys.exit(1)
            
            # In ra báo cáo JSON để n8n nhận kết quả
            print(json.dumps(result, ensure_ascii=False))
            
        else:
            print(json.dumps({"error": f"Lệnh không hợp lệ: {command}"}))
            sys.exit(1)

    except Exception as e:
        # Bắt toàn bộ lỗi runtime và trả về chuẩn JSON cho n8n
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()