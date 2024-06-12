import logging  # Import the logging module
import random 
import os
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, jsonify, session, render_template, redirect, request, url_for, flash
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

ITEMS_PER_PAGE = 30

## Helper 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("email") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    user_id = session.get("ma_nguoi_dung")
    if user_id:
        logging.debug(f"Current user_id from session: {user_id}")
    else:
        logging.debug("No user_id found in session")
    return user_id

@app.route('/')
def index():
    if session.get("email") is not None:
        return render_template('home.html')
    else:
        return render_template('index.html')

# LOGIN , REGISTER , LOGOUT

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        if not request.form.get("ten_dang_nhap"):
            return render_template("error.html", message="Phải cung cấp Tên đăng nhập")
        if not request.form.get("ten_nguoi_dung"):
            return render_template("error.html", message="Phải cung cấp Tên người dùng")
        elif not request.form.get("email"):
            return render_template("error.html", message="Phải cung cấp Email")
        elif not request.form.get("mat_khau1") or not request.form.get("mat_khau2"):
            return render_template("error.html", message="Phải cung cấp mật khẩu")
        elif request.form.get("mat_khau1") != request.form.get("mat_khau2"):
            return render_template("error.html", message="Mật khẩu không khớp")

        # end validation
        else:
            ten_nguoi_dung = request.form.get("ten_nguoi_dung")
            ten_dang_nhap = request.form.get("ten_dang_nhap")
            email = request.form.get("email")
            mat_khau = request.form.get("mat_khau1")

            try:
                db.execute(text("INSERT INTO NguoiDung(ten_dang_nhap, ten_nguoi_dung, email, mat_khau) VALUES (:ten_dang_nhap, :ten_nguoi_dung, :email, :mat_khau)"),
                           {"ten_dang_nhap": ten_dang_nhap, "ten_nguoi_dung": ten_nguoi_dung, "email": email, "mat_khau": generate_password_hash(mat_khau)})
            except Exception as e:
                return render_template("error.html", message=e)

            db.commit()

            Q = db.execute(text("SELECT * FROM NguoiDung WHERE email LIKE :email"), {"email": email}).fetchone()
            print(Q.ma_nguoi_dung)

            session["ten_nguoi_dung"] = Q.ten_nguoi_dung
            session["ma_nguoi_dung"] = Q.ma_nguoi_dung
            session["email"] = Q.email
            session["logged_in"] = True

            return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        form_dang_nhap = request.form.get("ten_dang_nhap")
        form_email = request.form.get("email")
        form_password = request.form.get("mat_khau")

        if not form_email:
            return render_template("error.html", message="must provide username")
        elif not form_password:
            return render_template("error.html", message="must provide password")

        Q = db.execute(text("SELECT * FROM NguoiDung WHERE email LIKE :email AND ten_dang_nhap LIKE :ten_dang_nhap"), {"email": form_email, "ten_dang_nhap": form_dang_nhap}).fetchone()
        db.commit()

        if Q is None:
            return render_template("error.html", message="User doesn't exists")
        if not check_password_hash(Q.mat_khau, form_password):
            return render_template("error.html", message="Invalid password")

        session["ma_nguoi_dung"] = Q.ma_nguoi_dung
        session["email"] = Q.email
        session["ten_nguoi_dung"] = Q.ten_nguoi_dung
        session["logged_in"] = True

        return render_template("home.html")

    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("index"))

# BUSINESS FUNCTION
@app.route('/page', methods=['GET'])
def page():
    # Function implementation
    pass

# Somewhere else in the code
@app.route('/page', methods=['GET'])
def another_page_function():
    # Another implementation
    pass

@app.route('/search', methods=['GET', 'POST'], endpoint='search')
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        query = request.form.get("input-search")
        if query is None:
            return render_template("error.html", message="Search field cannot be empty!")
        try:
            result = db.execute(text('SELECT * FROM tuvung WHERE LOWER(tu) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=str(e))
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list.html", result=result)

@app.route('/saved_words', methods=['GET', 'POST'], endpoint='search_saved_words')
def search_saved_words():
    if request.method == "GET":
        return render_template("saved_words.html")
    else:
        query = request.form.get("input-saved_words")
        if query is None:
            return render_template("error.html", message="Search field cannot be empty!")
        try:
            result = db.execute(text('SELECT * FROM tuvung WHERE LOWER(tu) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=str(e))
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list_saved_words.html", result=result)
    
@app.route('/create_vocabulary_page', methods=['POST'])
@login_required
def create_vocabulary_page():
    try:
        user_id = session.get("ma_nguoi_dung")
        data = request.json
        page_name = data.get('page_name')
        page_description = data.get('page_description', '')
        selected_words = data.get('words', [])

        if not page_name:
            return jsonify({"status": "error", "message": "Tên trang là bắt buộc"})

        result = db.execute(text('INSERT INTO TrangTuVung (ten_trang, mo_ta, ma_nguoi_dung) VALUES (:page_name, :page_description, :user_id) RETURNING ma_trang'),
                            {"page_name": page_name, "page_description": page_description, "user_id": user_id})
        page_id = result.fetchone()[0]

        for word in selected_words:
            db.execute(text('INSERT INTO TienDoHocTu (ma_trang, ma_nguoi_dung, ma_tu_vung, diem) VALUES (:page_id, :user_id, :ma_tu_vung, 0)'),
                       {"page_id": page_id, "user_id": user_id, "ma_tu_vung": word['ma_tu_vung']})
        db.commit()
        logging.debug("Vocabulary page created successfully")
        return jsonify({"status": "success", "page_id": page_id})
    except Exception as e:
        logging.exception("Error creating vocabulary page")
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/save_page', methods=['GET', 'POST'])
@login_required
def save_page():
    user_id = get_current_user_id()
    if request.method == 'POST':
        # Handle the form submission
        selected_words = request.form.getlist('selected_words')
        page_name = request.form.get('page_name')
        existing_page_id = request.form.get('existing_page_id')

        try:
            if not page_name and not existing_page_id:
                flash("Please enter a page name or select an existing page.")
                return redirect(url_for('search'))

            with engine.connect() as connection:
                if page_name:
                    result = connection.execute(
                        text('INSERT INTO TrangTuVung (ten_trang, ma_nguoi_dung) VALUES (:page_name, :user_id) RETURNING ma_trang'),
                        {"page_name": page_name, "user_id": user_id})
                    page_id = result.fetchone()[0]
                else:
                    page_id = existing_page_id

                insert_query = text('INSERT INTO TienDoHocTu (ma_trang, ma_nguoi_dung, ma_tu_vung, diem) VALUES (:page_id, :user_id, :ma_tu_vung, 0)')
                for word in selected_words:
                    connection.execute(insert_query, {"page_id": page_id, "user_id": user_id, "ma_tu_vung": word})

                connection.commit()

            session['selected_words'] = []
            flash("Words saved successfully.")
            return redirect(url_for('trang_tu_vung'))

        except Exception as e:
            logging.exception("Error saving words")
            return render_template("error.html", message=str(e))

    else:
        try:
            existing_pages = db.execute(
                text('SELECT ma_trang, ten_trang FROM TrangTuVung WHERE ma_nguoi_dung = :user_id'), 
                {"user_id": user_id}).fetchall()

            logging.debug(f"Fetched existing pages: {existing_pages}")

            return render_template('list.html', existing_pages=existing_pages)
        except Exception as e:
            logging.exception("Error fetching vocabulary pages")
            return render_template("error.html", message=str(e))

@app.route('/api/get_vocabulary_pages', methods=['GET'])
@login_required
def get_vocabulary_pages():
    try:
        user_id = get_current_user_id()  # Thay thế bằng phương thức của bạn để lấy ID người dùng hiện tại
        with engine.connect() as connection:
            result = connection.execute(
                text('SELECT ma_trang, ten_trang FROM TrangTuVung WHERE ma_nguoi_dung = :user_id'),
                {"user_id": user_id}
            ).fetchall()
            pages = [{"ma_trang": row[0], "ten_trang": row[1]} for row in result]  # Chuyển tuple thành dictionary
        return jsonify({"status": "success", "pages": pages})
    except Exception as e:
        logging.exception("Lỗi khi lấy các trang từ vựng")
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


@app.route('/saved_words', methods=['GET', 'POST'])
@login_required
def saved_words():
    user_id = get_current_user_id()
    if request.method == 'POST':
        # Handle the form submission
        selected_words = request.form.getlist('selected_words')
        page_name = request.form.get('page_name')
        existing_page_id = request.form.get('existing_page_id')

        try:
            if not page_name and not existing_page_id:
                flash("Please enter a page name or select an existing page.")
                return redirect(url_for('saved_words'))

            with engine.connect() as connection:
                if page_name:
                    result = connection.execute(
                        text('INSERT INTO TrangTuVung (ten_trang, ma_nguoi_dung) VALUES (:page_name, :user_id) RETURNING ma_trang'),
                        {"page_name": page_name, "user_id": user_id})
                    page_id = result.fetchone()[0]
                else:
                    page_id = existing_page_id

                insert_query = text('INSERT INTO TienDoHocTu (ma_trang, ma_nguoi_dung, ma_tu_vung, diem) VALUES (:page_id, :user_id, :ma_tu_vung, 0)')
                for word in selected_words:
                    connection.execute(insert_query, {"page_id": page_id, "user_id": user_id, "ma_tu_vung": word})

                connection.commit()

            flash("Words saved successfully.")
            return redirect(url_for('saved_words'))

        except Exception as e:
            logging.exception("Error saving words")
            return render_template("error.html", message=str(e))

    else:
        try:
            existing_pages = db.execute(
                text('SELECT ma_trang, ten_trang FROM TrangTuVung WHERE ma_nguoi_dung = :user_id'), 
                {"user_id": user_id}).fetchall()

            logging.debug(f"Fetched existing pages: {existing_pages}")

            return render_template('saved_words.html', existing_pages=existing_pages)
        except Exception as e:
            logging.exception("Error fetching vocabulary pages")
            return render_template("error.html", message=str(e))
        
@app.route('/trang_tu_vung')
@login_required
def trang_tu_vung():
    try:
        user_id = get_current_user_id()
        if user_id is None:
            raise ValueError("User ID not found in session")

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
    user_id = get_current_user_id()
    try:
        # Fetch the page using .mappings().fetchone() to get a dictionary-like result
        page = db.execute(
            text('SELECT * FROM TrangTuVung WHERE ma_trang = :page_id AND ma_nguoi_dung = :user_id'),
            {"page_id": page_id, "user_id": user_id}
        ).mappings().fetchone()
        
        if not page:
            flash("Page not found.")
            return redirect(url_for('trang_tu_vung'))

        # Fetch the word IDs
        word_ids = db.execute(
            text('SELECT ma_tu_vung FROM TienDoHocTu WHERE ma_trang = :page_id'),
            {"page_id": page_id}
        ).fetchall()
        word_ids = [word_id[0] for word_id in word_ids]

        if not word_ids:
            flash("No words found for this page.")
            return render_template('view_page.html', page=page, words=[])

        # Fetch the words using .mappings().fetchall() to get dictionary-like results
        words = db.execute(
            text('SELECT * FROM TuVung WHERE ma_tu_vung IN :word_ids'),
            {"word_ids": tuple(word_ids)}
        ).mappings().fetchall()

        return render_template('view_page.html', page=page, words=words)
    except Exception as e:
        logging.exception("Error viewing page")
        return render_template("error.html", message=str(e))



@app.route('/flashcard', methods=['GET'])
def flashcard():
    try:
        flashcard = db.execute(text('SELECT * FROM tuvung ORDER BY RANDOM() LIMIT 1')).fetchone()
        
    except Exception as e:
        return render_template("error.html", message=str(e))

    if not flashcard:
        return render_template("error.html", message="No flashcards available")

    return render_template("flashcard.html", flashcard=flashcard)

@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if request.method == 'POST':
        ma_trang = request.form.get('ma_trang')
        ma_nguoi_dung = request.form.get('ma_nguoi_dung')
        ma_tu_vung = request.form.get('ma_tu_vung')

        try:
            tuvung = db.execute(text('SELECT * FROM TienDoHocTu WHERE ma_trang = :ma_trang AND ma_nguoi_dung = :ma_nguoi_dung AND ma_tu_vung = :ma_tu_vung'), 
                                 {"ma_trang": ma_trang, "ma_nguoi_dung": ma_nguoi_dung, "ma_tu_vung": ma_tu_vung}).fetchone()
            if tuvung is None:
                return render_template("error.html", message="No vocabulary found")

            cau_hoi = tuvung.tu
            correct_choice = tuvung.nghia

            choices = db.execute(text('SELECT nghia FROM TienDoHocTu WHERE nghia != :correct_choice ORDER BY RANDOM() LIMIT 3')).fetchall()
            choice_a = choices[0].nghia
            choice_b = choices[1].nghia
            choice_c = choices[2].nghia

            db.execute(text('INSERT INTO CauHoi (tu, choice_a, choice_b, choice_c, correct_choice) VALUES (:cau_hoi, :choice_a, :choice_b, :choice_c, :correct_choice)'), 
                       {"cau_hoi": cau_hoi, "choice_a": choice_a, "choice_b": choice_b, "choice_c": choice_c, "correct_choice": correct_choice})
            db.commit()
        except Exception as e:
            return render_template("error.html", message=str(e))

        return redirect(url_for('page'))

    return render_template('add_question.html')

@app.route('/matching_game')
@login_required
def matching_game():
    user_id = get_current_user_id()
    page_id = request.args.get('page_id')

    if not page_id:
        flash("Page ID is required.")
        return redirect(url_for('trang_tu_vung'))

    try:
        words = db.execute(
        text('SELECT * FROM TuVung WHERE ma_tu_vung IN (SELECT ma_tu_vung FROM TienDoHocTu WHERE ma_trang = :page_id AND ma_nguoi_dung = :user_id) ORDER BY RANDOM() LIMIT 5'),
        {"page_id": page_id, "user_id": user_id}
    ).fetchall()

        if not words:
            flash("No words found for this page.")
            return redirect(url_for('trang_tu_vung'))

        # Shuffle the meanings
        meanings = [word.nghia for word in words]
        random.shuffle(meanings)

        return render_template('matching_game.html', words=words, meanings=meanings)
    except Exception as e:
        logging.exception("Error fetching words for matching game")
        return render_template("error.html", message=str(e))

@app.route('/check_matching_answers', methods=['POST'])
@login_required
def check_matching_answers():
    data = request.get_json()
    user_id = get_current_user_id()

    try:
        word_ids = [item['ma_tu_vung'] for item in data]
        print("Word IDs:", word_ids)  # Debug print

        # Fetch correct answers from database
        correct_answers = db.execute(
            text('SELECT ma_tu_vung, nghia FROM TuVung WHERE ma_tu_vung IN :word_ids'),
            {"word_ids": tuple(word_ids)}
        ).fetchall()
        print("Correct Answers from DB:", correct_answers)  # Debug print

        correct_answers_dict = {str(row.ma_tu_vung): row.nghia for row in correct_answers}
        print("Correct Answers Dict:", correct_answers_dict)  # Debug print

        # Check user answers
        user_correct_answers = {}
        for item in data:
            word_id = item['ma_tu_vung']
            user_answer = item['nghia']
            correct_answer = correct_answers_dict.get(str(word_id))

            if user_answer == correct_answer:
                user_correct_answers[word_id] = user_answer

        print("User Correct Answers:", user_correct_answers)  # Debug print

        return jsonify({"status": "success", "correct_answers": user_correct_answers, "message": "Answers checked successfully."})
    except Exception as e:
        logging.exception("Error checking answers")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/update_points_matching_game', methods=['POST'])
@login_required
def update_points_matching_game():
    data = request.get_json()
    user_id = get_current_user_id()
    ma_trang = data.get('ma_trang')

    try:
        points_per_correct = data['points_per_correct']
        correct_answers = data['correct_answers']
        total_points_added = 0

        for word_id, correct_meaning in correct_answers.items():
            result = db.execute(
                text('SELECT diem FROM TienDoHocTu WHERE ma_trang = :ma_trang AND ma_tu_vung = :word_id AND ma_nguoi_dung = :user_id'),
                {"ma_trang": ma_trang, "word_id": word_id, "user_id": user_id}
            ).fetchone()

            if result:
                current_points = result['diem'] if result['diem'] is not None else 0
                new_points = min(current_points + points_per_correct, 10)

                db.execute(
                    text('UPDATE TienDoHocTu SET diem = :new_points, lan_cuoi_hoc = CURRENT_TIMESTAMP WHERE ma_trang = :ma_trang AND ma_tu_vung = :word_id AND ma_nguoi_dung = :user_id'),
                    {"new_points": new_points, "ma_trang": ma_trang, "word_id": word_id, "user_id": user_id}
                )

                total_points_added += new_points - current_points

        db.commit()
        return jsonify({"status": "success", "message": f"Points updated successfully. Total points added: {total_points_added}"})
    except Exception as e:
        logging.exception("Error updating points")
        db.rollback()
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
