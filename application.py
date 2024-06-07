import logging
import os
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, jsonify, session, render_template, redirect, request, url_for, flash, jsonify
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Check if DATABASE_URL is set
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure Flask session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLAlchemy
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


ITEMS_PER_PAGE = 20

## Helper 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip actual login check for demo purposes
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/page', methods=['GET'])
def page():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    offset = (page - 1) * ITEMS_PER_PAGE

    try:
        result = db.execute(text('SELECT * FROM tuvung ORDER BY ma_tu_vung LIMIT :limit OFFSET :offset'), {"limit": ITEMS_PER_PAGE, "offset": offset}).fetchall()
        total_results = db.execute(text('SELECT COUNT(*) FROM tuvung')).scalar()
    except Exception as e:
        return render_template("error.html", message=str(e))

    pagination = Pagination(page=page, total=total_results, search=False, record_name='result', per_page=ITEMS_PER_PAGE)

    return render_template("list.html", result=result, pagination=pagination)
        

@app.route('/search', methods=['GET', 'POST'])
def search():
    try:
        if request.method == "GET":
            return render_template("search.html")

        query = request.form.get("input-search")
        page = request.args.get('page', type=int, default=1)

        if not query:
            return render_template("error.html", message="Search field cannot be empty!")

        per_page = 20
        offset = (page - 1) * per_page
        query_like = f"%{query.lower()}%"
        total = db.execute(text('SELECT COUNT(*) FROM TuVung WHERE LOWER(tu) LIKE :query'), {"query": query_like}).scalar()
        result = db.execute(text('SELECT * FROM TuVung WHERE LOWER(tu) LIKE :query ORDER BY tu LIMIT :limit OFFSET :offset'), 
                             {"query": query_like, "limit": per_page, "offset": offset}).fetchall()
        pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

        selected_words = session.get('selected_words', [])

        # Lấy danh sách các trang từ vựng của người dùng
        existing_pages = db.execute(text('SELECT * FROM TrangTuVung WHERE ma_nguoi_dung = :user_id'), {"user_id": 1}).fetchall()

        return render_template("list.html", result=result, pagination=pagination, selected_words=selected_words, existing_pages=existing_pages)
    except Exception as e:
        logging.exception("Error during search")
        return render_template("error.html", message=str(e))

@app.route('/save_selected_words', methods=['POST'])
def save_selected_words():
    try:
        selected_words = request.json
        session['selected_words'] = selected_words
        return jsonify({"status": "success"})
    except Exception as e:
        logging.exception("Error saving selected words")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/create_vocabulary_page', methods=['POST'])
def create_vocabulary_page():
    try:
        data = request.json
        logging.info(f"Received data: {data}")

        page_name = data.get('page_name')
        page_description = data.get('page_description', '')
        selected_words = data.get('words', [])

        if not page_name:
            logging.error("Tên trang là bắt buộc")
            return jsonify({"status": "error", "message": "Tên trang là bắt buộc"})

        user_id = 1  # Giả định user_id cố định

        result = db.execute(text('INSERT INTO TrangTuVung (ten_trang, mo_ta, ma_nguoi_dung) VALUES (:page_name, :page_description, :user_id) RETURNING ma_trang'),
                            {"page_name": page_name, "page_description": page_description, "user_id": user_id})
        page_id = result.fetchone()[0]
        logging.info(f"Page created with ID: {page_id}")

        for word in selected_words:
            db.execute(text('INSERT INTO TienDoHocTu (ma_trang, ma_nguoi_dung, ma_tu_vung, diem) VALUES (:page_id, :user_id, :ma_tu_vung, 0)'),
                       {"page_id": page_id, "user_id": user_id, "ma_tu_vung": word['ma_tu_vung']})
        db.commit()

        return jsonify({"status": "success", "page_id": page_id})
    except Exception as e:
        logging.exception("Error creating vocabulary page")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/save_words_to_existing_page', methods=['POST'])
def save_words_to_existing_page():
    try:
        data = request.json
        existing_page_id = data.get('existing_page_id')
        selected_words = data.get('words', [])

        if not existing_page_id:
            return jsonify({"status": "error", "message": "Existing page ID is required"})

        with engine.connect() as connection:
            word_count = connection.execute(text('SELECT COUNT(*) FROM TienDoHocTu WHERE ma_trang = :page_id'), {"page_id": existing_page_id}).scalar()
            if word_count + len(selected_words) > 10:
                return jsonify({"status": "error", "message": "The page already has too many words. Please create a new page."})

            for word in selected_words:
                connection.execute(text('INSERT INTO TienDoHocTu (ma_trang, ma_nguoi_dung, ma_tu_vung, diem) VALUES (:page_id, :user_id, :ma_tu_vung, 0)'),
                                   {"page_id": existing_page_id, "user_id": 1, "ma_tu_vung": word['ma_tu_vung']})
            connection.commit()

        return jsonify({"status": "success"})
    except Exception as e:
        logging.exception("Error saving words to existing page")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/save_words', methods=['POST'])
def save_words():
    try:
        selected_words = session.get('selected_words', [])
        if not selected_words:
            flash("No words selected to save.")
            return redirect(url_for('search'))

        page_name = request.form.get('page_name')
        existing_page_id = request.form.get('existing_page_id')

        if not page_name and not existing_page_id:
            flash("Please enter a page name or select an existing page.")
            return redirect(url_for('search'))

        user_id = 1  # Fixed user_id

        with engine.connect() as connection:
            if page_name:
                result = connection.execute(text('INSERT INTO TrangTuVung (ten_trang, ma_nguoi_dung) VALUES (:page_name, :user_id) RETURNING ma_trang'),
                                            {"page_name": page_name, "user_id": user_id})
                page_id = result.fetchone()[0]
            else:
                page_id = existing_page_id

            word_count = connection.execute(text('SELECT COUNT(*) FROM TrangTuVungTuVung WHERE ma_trang = :page_id'), {"page_id": page_id}).scalar()
            if word_count + len(selected_words) > 10:
                flash("The page already has too many words. Please create a new page.")
                return redirect(url_for('search'))

            for word in selected_words:
                connection.execute(text('INSERT INTO TrangTuVungTuVung (ma_trang, tu, phienam, nghia) VALUES (:page_id, :tu, :phienam, :nghia)'),
                                   {"page_id": page_id, "tu": word['tu'], "phienam": word['phienam'], "nghia": word['nghia']})
            connection.commit()

        session['selected_words'] = []  # Clear session after saving
        flash("Words saved successfully.")
        return redirect(url_for('trang_tu_vung'))
    except Exception as e:
        logging.exception("Error saving words")
        return render_template("error.html", message=str(e))

@app.route('/trang_tu_vung')
@login_required
def trang_tu_vung():
    try:
        user_id = 1  # Fixed user_id
        logging.debug(f"Fetching vocabulary pages for user {user_id}")
        
        pages = db.execute(text('SELECT * FROM TrangTuVung WHERE ma_nguoi_dung = :user_id'), {"user_id": user_id}).fetchall()
        logging.debug(f"Pages: {pages}")
        
        return render_template('trang_tu_vung.html', pages=pages)
    except Exception as e:
        logging.exception("Error fetching vocabulary pages")
        return render_template("error.html", message=str(e))

@app.route('/view_page/<int:page_id>')
@login_required
def view_page(page_id):
    try:
        # Lấy thông tin trang từ bảng TrangTuVung
        page = db.execute(text('SELECT * FROM TrangTuVung WHERE ma_trang = :page_id'), {"page_id": page_id}).fetchone()
        if not page:
            flash("Page not found.")
            return redirect(url_for('trang_tu_vung'))

        # Lấy danh sách mã từ vựng từ bảng TienDoHocTu
        word_ids = db.execute(text('SELECT ma_tu_vung FROM TienDoHocTu WHERE ma_trang = :page_id'), {"page_id": page_id}).fetchall()
        word_ids = [word_id[0] for word_id in word_ids]

        # Lấy thông tin từ vựng từ bảng TuVung
        words = db.execute(text('SELECT * FROM TuVung WHERE ma_tu_vung IN :word_ids'), {"word_ids": tuple(word_ids)}).fetchall()

        return render_template('view_page.html', page=page, words=words)
    except Exception as e:
        logging.exception("Error viewing page")
        return render_template("error.html", message=str(e))

if __name__ == "__main__":
    app.run(debug=True)
