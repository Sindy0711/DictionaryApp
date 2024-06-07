import os
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, jsonify, session, render_template, redirect, request, url_for
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter
from werkzeug.security import check_password_hash,generate_password_hash

from dotenv import load_dotenv
load_dotenv() 

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
        
@app.route('/')
def index():
    if session.get("email") is not None:
        return render_template('home.html')
    else:
        return render_template('index.html')
    


# LOGIN , REGISTER , LOGOUT

@app.route('/register' , methods = ['GET' ,'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        if not request.form.get("ten_dang_nhap"):
            return render_template("error.html" , message = "Phải cung cấp Tên đăng nhập")
        if not request.form.get("ten_nguoi_dung"):
            return render_template("error.html" , message = "Phải cung cấp Tên người dùng")
        elif not request.form.get("email"):
            return render_template("error.html" , message = "Phải cung cấp Email")
        elif not request.form.get("mat_khau1") or not request.form.get("mat_khau2"):
            return render_template("error.html", message="Phải cung cấp mật khẩu")
        elif request.form.get("mat_khau1") != request.form.get("mat_khau2"):
            return render_template("error.html", message="Mật khẩu không khớp")
        
        # end validation
        else :
            ten_nguoi_dung = request.form.get("ten_nguoi_dung")
            ten_dang_nhap = request.form.get("ten_dang_nhap")
            email = request.form.get("email")
            mat_khau = request.form.get("mat_khau1")
            
            try:
                db.execute(text("INSERT INTO NguoiDung(ten_dang_nhap, ten_nguoi_dung, email , mat_khau) VALUES (:ten_dang_nhap, :ten_nguoi_dung, :email, :mat_khau)"),{ "ten_dang_nhap" : ten_dang_nhap,  "ten_nguoi_dung" : ten_nguoi_dung, "email" : email, "mat_khau" : generate_password_hash(mat_khau)})
            except Exception as e:
                return render_template("error.html", message=e)
            
            db.commit()
            
            Q = db.execute(text("SELECT * FROM NguoiDung WHERE email LIKE :email"),{"email": email},).fetchone()
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

        Q = db.execute(text("SELECT * FROM NguoiDung WHERE email LIKE :email AND ten_dang_nhap LIKE :ten_dang_nhap"), {"email": form_email , "ten_dang_nhap" : form_dang_nhap}).fetchone()
        db.commit()
        
        if Q is None:
            return render_template("error.html", message="User doesn't exists")
        if not check_password_hash( Q.mat_khau, form_password):
            return  render_template("error.html", message = "Invalid password")
        
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
    if request.method == "GET":
        return render_template("search.html")
    else:
        query = request.form.get("input-search")
        if query is None:
            return render_template("error.html", message="Search field can not be empty!")
        try:
            result = db.execute(text('SELECT * FROM tuvung WHERE LOWER(tu) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=e)
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list.html", result=result)
    
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


if __name__ == "__main__":
    app.run(debug=True)
