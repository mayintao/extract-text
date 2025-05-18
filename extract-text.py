from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import fitz  # PyMuPDF
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def hello_world():
    return 'Hello, World!'


# -------------------- 上传文件 → 保存并返回 file_id，用于后续分页提取 --------------------
@app.route("/api/ai/pdf-upload", methods=["POST"])
def upload_pdf_file():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"error": "请上传 PDF 文件"}), 400

    file_id = uuid.uuid4().hex
    filepath = os.path.join(UPLOAD_FOLDER, f"{file_id}.pdf")
    file.save(filepath)

    try:
        doc = fitz.open(filepath)
        total_pages = len(doc)
        first_page_text = doc.load_page(0).get_text()
        doc.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "file_id": file_id,
        "total_pages": total_pages,
        "first_page_text": first_page_text
    })


# -------------------- 提取某一页内容（通过 file_id + page 参数） --------------------
@app.route("/api/ai/pdf-page", methods=["GET"])
def extract_page():
    file_id = request.args.get("file_id")
    page = int(request.args.get("page", 1))

    filepath = os.path.join(UPLOAD_FOLDER, f"{file_id}.pdf")
    if not os.path.exists(filepath):
        return jsonify({"error": "文件未找到或已过期"}), 404

    try:
        doc = fitz.open(filepath)
        if page < 1 or page > len(doc):
            return jsonify({"error": "页码超出范围"}), 400
        text = doc.load_page(page - 1).get_text()
        doc.close()
        return jsonify({
            "page": page,
            "text": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- 上传历史查询接口 --------------------

@app.route("/api/ai/upload-history", methods=["GET"])
def get_upload_history():
    files = []
    for f in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, f)
        if os.path.isfile(path):
            files.append({
                "filename": f,
                "timestamp": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })
    files.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(files)


# -------------------- 清空上传历史接口 --------------------

@app.route("/api/ai/clear-uploaded", methods=["GET"])
def clear_uploaded_files():
    deleted_files = []
    for f in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, f)
        if os.path.isfile(path):
            os.remove(path)
            deleted_files.append(f)
    return jsonify({"message": "Uploaded files cleared", "deleted_files": deleted_files})


# -------------------- 启动 --------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render 默认 10000
    app.run(host="0.0.0.0", port=port)
