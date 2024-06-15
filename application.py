import random
from random import shuffle
import os , re , logging
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, jsonify, session, render_template, redirect, request, url_for, flash
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
from datetime import datetime

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

def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    elif not any(char.isdigit() for char in password):
        return "Password must contain at least one number"
    elif not any(char.isalpha() for char in password):
        return "The password must contain at least one letter"
    elif not re.search('[^a-zA-Z0-9]', password):
        return "The password must contain at least one special character"
    return None

def get_random_question():
    with engine.connect() as db:
        question = db.execute(text("SELECT * FROM Vocabulary ORDER BY RANDOM() LIMIT 1")).fetchone()
        return question
def process_multiple_choice(user_choice, correct_answer, start_time):
    end_time = datetime.now()
    if user_choice == correct_answer:
        if (end_time - start_time).total_seconds() <= 5:
            session['score'] += 1
        else:
            session['score'] += 0.12
        flash(f"Correct!", "success")
    else:
        flash(f"Incorrect. The correct answer is: {correct_answer}", "danger")
    session['question_number'] += 1

def get_random_choices(correct_answer,column):
    with engine.connect() as db:
        choices = db.execute(
            text(f'SELECT {column} FROM Vocabulary WHERE {column} != :correct_answer ORDER BY RANDOM() LIMIT 3'),
            {"correct_answer": correct_answer}
        ).fetchall()
        return [choice[0] for choice in choices]

# Hàm render câu hỏi
def render_question(question_text, correct_answer, choices):
    random.shuffle(choices)
    return render_template('multiple_choice.html', question_text=question_text, choices=choices, correct_answer=correct_answer, question_number=session['question_number'])

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
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        for field in [full_name , username , email , password1, password2]:
            if not field:
                return render_template("register.html", message="All fields must be filled in") 
        
         # Kiểm tra xem mật khẩu có hợp lệ không    
        password_error = validate_password(password1)
        if password_error:
            return render_template("register.html", message=password_error)

        # Kiểm tra đồng bộ
        if password1 != password2:
            return render_template("register.html", message="Password mismatch")

        existing_user = db.execute(text("SELECT * FROM Users WHERE email = :email"), {"email": email}).fetchone()
        if existing_user:
            return render_template("register.html", message="Email used")
        # end validation
        else:

            try:
                db.execute(text("INSERT INTO Users(username, full_name, email, password) VALUES (:username, :full_name, :email, :password)"),
                           {"username": username, "full_name": full_name, "email": email, "password": generate_password_hash(password1)})
            except Exception as e:
                return render_template("register.html", message=e)

            db.commit()

            Q = db.execute(text("SELECT * FROM Users WHERE email LIKE :email AND full_name LIKE :full_name"), {"email": email , "full_name": full_name }).fetchone()
            print(Q.user_id)

            session["user_id"] = Q.user_id
            session["full_name"] = Q.full_name
            session["email"] = Q.email
            session["logged_in"] = True

            return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        form_log_in = request.form.get("username")
        form_email = request.form.get("email")
        form_password = request.form.get("password")

        if not form_email or not form_password:
            return render_template("error.html", message="must provide email and password")
        

        Q = db.execute(text("SELECT * FROM Users WHERE email LIKE :email AND username LIKE :username"), {"email": form_email, "username": form_log_in}).fetchone()
        db.commit()

        if Q is None:
            return render_template("error.html", message="User doesn't exists")
        if not check_password_hash(Q.password, form_password):
            return render_template("error.html", message="Invalid password")

        session["user_id"] = Q.user_id
        session["email"] = Q.email
        session["full_name"] = Q.full_name
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
        result = db.execute(text('SELECT * FROM Vocabulary ORDER BY word_id LIMIT :limit OFFSET :offset'), {"limit": ITEMS_PER_PAGE, "offset": offset}).fetchall()
        total_results = db.execute(text('SELECT COUNT(*) FROM Vocabulary')).scalar()
    except Exception as e:
        return render_template("error.html", message=str(e))

    pagination = Pagination(page=page, total=total_results, search=False, record_name='result', per_page=ITEMS_PER_PAGE)

    return render_template("list.html", result=result, pagination=pagination, display_msg=False)

@app.route('/search', methods=['GET', 'POST'], endpoint='search')
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        query = request.form.get("input-search")
        if query is None:
            return render_template("error.html", message="Search field cannot be empty!")
        try:
            result = db.execute(text('SELECT * FROM Vocabulary WHERE LOWER(word) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=str(e))
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list.html", result=result)

@app.route('/saved_words', methods=['GET', 'POST'], endpoint='search_saved_words_list')
def search_saved_words():
    if request.method == "GET":
        return render_template("saved_words.html")
    else:
        query = request.form.get("input-saved_words")
        if query is None:
            return render_template("error.html", message="Search field cannot be empty!")
        try:
            result = db.execute(text('SELECT * FROM Vocabulary WHERE LOWER(word) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=str(e))
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list_saved_words.html", result=result)
    
@app.route('/create_vocabulary_page', methods=['POST'])
@login_required
def create_vocabulary_page():
    try:
        user_id = session.get("user_id")
        data = request.json
        page_name = data.get('page_name')
        page_description = data.get('page_description', '')
        selected_words = data.get('words', [])

        if not page_name:
            return jsonify({"status": "error", "message": "Page name is required"})

        result = db.execute(text('INSERT INTO VocabularyPage (page_name, description, user_id) VALUES (:page_name, :page_description, :user_id) RETURNING page_id'),
                            {"page_name": page_name, "page_description": page_description, "user_id": user_id})
        page_id = result.fetchone()[0]

        for word in selected_words:
            db.execute(text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)'),
                       {"page_id": page_id, "user_id": user_id, "word_id": word['word_id']})
        db.commit()
        logging.debug("Vocabulary page created successfully")
        return jsonify({"status": "success", "page_id": page_id})
    except Exception as e:
        logging.exception("Error creating vocabulary page")
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/save_page', methods=['GET', 'POST'])
@login_required
def save_page():
    user_id = session.get("user_id")
    if request.method == 'POST':
        # Handle the form submission
        selected_words = request.form.getlist('selected_words')
        page_name = request.form.get('page_name')
        existing_page_id = request.form.get('existing_page_id')

        try:
            if not page_name and not existing_page_id:
                flash("Please enter a page name or select an existing page.")
                return redirect(url_for('search'))

            with engine.connect() as db:
                if page_name:
                    result = db.execute(
                        text('INSERT INTO VocabularyPage (page_name, user_id) VALUES (:page_name, :user_id) RETURNING page_id'),
                        {"page_name": page_name, "user_id": user_id})
                    page_id = result.fetchone()[0]
                else:
                    page_id = existing_page_id

                insert_query = text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)')
                for word in selected_words:
                    db.execute(insert_query, {"page_id": page_id, "user_id": user_id, "word_id": word})

                db.commit()

            session['selected_words'] = []
            flash("Words saved successfully.")
            return redirect(url_for('VocabularyPage'))
        except Exception as e:
            logging.exception("Error saving words")
            return render_template("error.html", message=str(e))

    else:
        try:
            existing_pages = db.execute(
                text('SELECT page_id, page_name FROM VocabularyPage WHERE user_id = :user_id'), 
                {"user_id": user_id}).fetchall()

            logging.debug(f"Fetched existing pages: {existing_pages}")

            return render_template('list.html', existing_pages=existing_pages)
        except Exception as e:
            logging.exception("Error fetching vocabulary pages")
            return render_template("error.html", message=str(e))

@app.route('/api/get_vocabulary_pages', methods=['GET'])
@login_required
def et_vocabulary_pages():
    try:
        user_id = session.get("user_id")
        with engine.connect() as db:
            result = db.execute(
                text('SELECT page_id, page_name FROM VocabularyPage WHERE user_id = :user_id'),
                {"user_id": user_id}
            ).fetchall()
            pages = [{"page_id": row[0], "page_name": row[1]} for row in result] 
        return jsonify({"status": "success", "pages": pages})
    except Exception as e:
        logging.exception("Error fetching vocabulary pages")
        return jsonify({"status": "error", "message": str(e)})




@app.route('/save_words_to_existing_page', methods=['POST'])
def save_words_to_existing_page():
    try:
        data = request.json
        existing_page_id = data.get('existing_page_id')
        selected_words = data.get('words', [])

        if not existing_page_id:
            return jsonify({"status": "error", "message": "Existing page ID is required"})

        with engine.connect() as db:
            word_count = db.execute(text('SELECT COUNT(*) FROM LearningProgress WHERE page_id = :page_id'), {"page_id": existing_page_id}).scalar()
            if word_count + len(selected_words) > 10:
                return jsonify({"status": "error", "message": "The page already has too many words. Please create a new page."})

            for word in selected_words:
                db.execute(text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)'),
                                   {"page_id": existing_page_id, "user_id": 1, "word_id": word['word_id']})
            db.commit()

        return jsonify({"status": "success"})
    except Exception as e:
        logging.exception("Error saving words to existing page")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/saved_words', methods=['GET', 'POST'])
@login_required
def saved_words():
    if request.method == 'POST':
        selected_words = request.form.getlist('selected_words')
        page_name = request.form.get('page_name')
        existing_page_id = request.form.get('existing_page_id')

        try:
            if not page_name and not existing_page_id:
                flash("Please enter a page name or select an existing page.")
                return redirect(url_for('saved_words'))
            user_id = session.get("user_id")

            with engine.connect() as db:
                if page_name:
                    result = db.execute(
                        text('INSERT INTO VocabularyPage (page_name, user_id) VALUES (:page_name, :user_id) RETURNING page_id'),
                        {"page_name": page_name, "user_id": user_id}
                    )
                    page_id = result.fetchone()[0]
                else:
                    page_id = existing_page_id

                word_count = db.execute(
                    text('SELECT COUNT(*) FROM PageWords WHERE page_id = :page_id'),
                    {"page_id": page_id}
                ).scalar()
                
                if word_count + len(selected_words) > 10:
                    flash("The page already has too many words. Please create a new page.")
                    return redirect(url_for('search'))

                # Chèn các từ đã chọn vào bảng PageWords
                insert_query = text('INSERT INTO PageWords (page_id, word, pronunciation, meaning) VALUES (:page_id, :word, :pronunciation, :meaning)')
                for word in selected_words:
                    db.execute(
                        insert_query,
                        {"page_id": page_id, "word": word['word'], "pronunciation": word['pronunciation'], "meaning": word['meaning']}
                    )
                db.commit()

            session['selected_words'] = []  # Xóa session sau khi lưu
            flash("Saved word successfully.")
            return redirect(url_for('vocabulary_page'))
        
        except Exception as e:
            logging.exception("Error while saving word")
            return render_template("error.html", message=str(e))
    
    # Xử lý yêu cầu GET
    return render_template('saved_words.html')

    
@app.route('/VocabularyPage')
@login_required
def VocabularyPage():
    try:
        user_id = session.get("user_id")
        if user_id is None:
            raise ValueError("User ID not found in session")

        logging.debug(f"Fetching vocabulary pages for user {user_id}")

        pages = db.execute(text('SELECT * FROM VocabularyPage WHERE user_id = :user_id'), {"user_id": user_id}).fetchall()
        logging.debug(f"Pages: {pages}")

        return render_template('VocabularyPage.html', pages=pages)
    except Exception as e:
        logging.exception("Error fetching vocabulary pages")
        return render_template("error.html", message=str(e))


@app.route('/view_page/<int:page_id>')
@login_required
def view_page(page_id):
    user_id = session.get("user_id")
    try:
        page = db.execute( text('SELECT * FROM VocabularyPage WHERE page_id = :page_id AND user_id = :user_id'),{"page_id": page_id, "user_id": user_id}).mappings().fetchone()
        
        if not page:
            flash("Page not found.")
            return redirect(url_for('VocabularyPage'))

        # Fetch the word IDs
        word_ids = db.execute(
            text('SELECT word_id FROM LearningProgress WHERE page_id = :page_id'),
            {"page_id": page_id}
        ).fetchall()
        word_ids = [word_id[0] for word_id in word_ids]

        if not word_ids:
            flash("No words found for this page.")
            return render_template('view_page.html', page=page, words=[])

        # Fetch the words using .mappings().fetchall() to get dictionary-like results
        words = db.execute( text('SELECT * FROM Vocabulary WHERE word_id IN :word_ids'), {"word_ids": tuple(word_ids)}).mappings().fetchall()

        return render_template('view_page.html', page=page, words=words)
    except Exception as e:
        logging.exception("Error viewing page")
        return render_template("error.html", message=str(e))

    
@app.route('/flashcard', methods=['GET'])
def flashcard():
    try:    
        # if 'email' in session:
        #     flashcard = db.execute(text('''
        #         SELECT LearningProgress.*, Vocabulary.pronunciation, Vocabulary.meaning 
        #         FROM LearningProgress 
        #         JOIN Vocabulary ON LearningProgress.word_id = Vocabulary.word_id 
        #         ORDER BY RANDOM() 
        #         LIMIT 1
        #     ''')).fetchone()
        # else:
        flashcard = db.execute(text("SELECT * FROM Vocabulary ORDER BY RANDOM() LIMIT 1")).fetchone()
    except Exception as e:
        return render_template("error.html", message=str(e))

    if not flashcard:
        return render_template("error.html", message="No flashcards available")
    return render_template("flashcard.html", flashcard=flashcard)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    session.setdefault('score', 0)
    session.setdefault('question_number', 0)

    if request.method == 'POST':
        quiz_type = request.form.get('quiz_type')
        if quiz_type in ['fill_in_the_blanks', 'word_to_meaning', 'meaning_to_word']:
            return redirect(url_for(quiz_type))

    return render_template('quiz.html')

@app.route('/multiple_choice', methods=['GET', 'POST'])
def multiple_choice():
    return quiz_route('meaning', 'word')


@app.route('/word_to_meaning', methods=['GET', 'POST'])
def word_to_meaning():
    return quiz_route('word', 'meaning')

@app.route('/meaning_to_word', methods=['GET', 'POST'])
def meaning_to_word():
    return quiz_route('meaning', 'word')

def quiz_route(question_col, answer_col):
    session.setdefault('score', 0)
    session.setdefault('question_number', 0)

    if request.method == 'POST':
        user_choice = request.form.get('user_choice')
        correct_answer = request.form.get('correct_answer')
        start_time = session.get('start_time')

        process_multiple_choice(user_choice, correct_answer, start_time)
        if session['question_number'] >= 10:
            return render_template("finished.html", score=session['score'])

    session['start_time'] = datetime.now()
    question = get_random_question()
    if question is None:
        return render_template("error.html", message="Không tìm thấy từ vựng nào")

    question_text = getattr(question, question_col)
    correct_answer = getattr(question, answer_col)

    choices = get_random_choices(correct_answer, answer_col)
    choices.append(correct_answer)

    return render_question(question_text, correct_answer, choices)

@app.route('/next', methods=['POST'])
def next_question():
    session['question_number'] += 1
    return redirect(url_for('multiple_choice'))

@app.route('/restart_quiz')
def restart_quiz():
    session['score'] = 0
    session['question_number'] = 0
    return redirect(url_for('quiz'))

@app.route('/fill_in_the_blanks', methods=['GET', 'POST'])
def fill_in_the_blanks():
    session.setdefault('score', 0)
    session.setdefault('question_number', 0)

    if request.method == 'POST':
        user_answer = request.form.get('user_answer')
        correct_word = request.form.get('correct_word')
        question_number = int(request.form.get('question_number', 0))

        if user_answer.lower() == correct_word.lower():
            flash("Correct!", "success")
            session['score'] += 1
        else:
            flash(f"Incorrect. The correct word is: {correct_word}", "danger")

        session['question_number'] = question_number + 1
        if session['question_number'] >= 10:
            return render_template("finished.html", score=session['score'])

        return redirect(url_for('fill_in_the_blanks'))

    question = get_random_question()
    if question is None:
        return render_template("error.html", message="No vocabulary found")

    meaning = question.meaning
    correct_word = question.word

    return render_template('fill_in_the_blanks.html', meaning=meaning, correct_word=correct_word, question_number=session['question_number'])

@app.route('/view_session', methods=['GET'])
def view_session():
    session_data = {key: session[key] for key in session.keys()}
    session.pop('score', None)
    session.pop('question_number', None)
    return jsonify(session_data)

# MATCHING GAME
@app.route('/matching_game')
@login_required
def matching_game():
    user_id = session.get("user_id")
    page_id = request.args.get('page_id')

    if not page_id:
        flash("Page ID is required.")
        return redirect(url_for('page'))

    try:
        words = db.execute(
        text('SELECT * FROM TuVung WHERE user_id IN (SELECT user_id FROM TienDoHocTu WHERE ma_trang = :page_id AND ma_nguoi_dung = :user_id) ORDER BY RANDOM() LIMIT 5'),
        {"page_id": page_id, "user_id": user_id}
    ).fetchall()

        if not words:
            flash("No words found for this page.")
            return redirect(url_for('page'))

        meanings = [word.meaning for word in words]
        random.shuffle(meanings)

        return render_template('matching_game.html', words=words, meanings=meanings)
    except Exception as e:
        logging.exception("Error fetching words for matching game")
        return render_template("error.html", message=str(e))

@app.route('/check_matching_answers', methods=['POST'])
@login_required
def check_matching_answers():
    data = request.get_json()
    user_id = session.get("user_id")

    try:
        word_ids = [item['user_id'] for item in data]
        print("Word IDs:", word_ids)  # Debug print

        # Fetch correct answers from database
        correct_answers = db.execute(
            text('SELECT user_id, meaning FROM TuVung WHERE user_id IN :word_ids'),
            {"word_ids": tuple(word_ids)}
        ).fetchall()
        print("Correct Answers from DB:", correct_answers)  # Debug print

        correct_answers_dict = {str(row.user_id): row.meaning for row in correct_answers}
        print("Correct Answers Dict:", correct_answers_dict)  # Debug print

        # Check user answers
        user_correct_answers = {}
        for item in data:
            word_id = item['user_id']
            user_answer = item['meaning']
            correct_answer = correct_answers_dict.get(str(word_id))

            if user_answer == correct_answer:
                user_correct_answers[word_id] = user_answer

        print("User Correct Answers:", user_correct_answers)  # Debug print

        return jsonify({"status": "success", "correct_answers": user_correct_answers, "message": "Answers checked successfully."})
    except Exception as e:
        logging.exception("Error checking answers")
        return jsonify({"status": "error", "message": str(e)})

from sqlalchemy.sql import text

@app.route('/update_points_matching_game', methods=['POST'])
@login_required  # Yêu cầu người dùng đăng nhập
def update_points_matching_game():
    data = request.get_json()
    user_id = session.get("user_id")
    ma_trang = data.get('ma_trang')

    try:
        # Lấy thông tin từ request JSON
        points_per_correct = data.get('points_per_correct')
        correct_answers = data.get('correct_answers')
        page_id = data.get('page_id')

        if not points_per_correct or not correct_answers or not page_id:
            raise ValueError("Missing required fields in JSON data")

        # Lấy danh sách word_ids từ correct_answers
        word_ids = list(correct_answers.keys())


        word_ids = [int(word_id) for word_id in word_ids if str(word_id).isdigit()]
        logging.debug(f"Validated Word IDs: {word_ids}")

        if not word_ids:
            raise ValueError("Invalid word_ids: All word_ids must be integers.")

        # Truy vấn điểm hiện tại từ cơ sở dữ liệu
        query = LearningProgress.query.filter(
            LearningProgress.page_id == page_id,
            LearningProgress.word_id.in_(word_ids),
            LearningProgress.user_id == user_id
        ).with_for_update().all()

        if not query:
            logging.warning(f"No existing scores found for page_id={page_id}, user_id={user_id}, word_ids={word_ids}")

        total_points_added = 0

        for word_id, correct_meaning in correct_answers.items():
            result = db.execute(
                text('SELECT score FROM TienDoHocTu WHERE ma_trang = :ma_trang AND user_id = :word_id AND ma_nguoi_dung = :user_id'),
                {"ma_trang": ma_trang, "word_id": word_id, "user_id": user_id}
            ).fetchone()

            # Thực hiện cập nhật vào cơ sở dữ liệu
            row.score = new_points
            row.last_study_date = datetime.utcnow()
            db.session.commit()

            db.execute(
                text('UPDATE TienDoHocTu SET score = :new_points, lan_cuoi_hoc = CURRENT_TIMESTAMP WHERE ma_trang = :ma_trang AND user_id = :word_id AND ma_nguoi_dung = :user_id'),
                {"new_points": new_points, "ma_trang": ma_trang, "word_id": word_id, "user_id": user_id}
            )

        return jsonify({"status": "success", "message": f"Points updated successfully. Total points added: {total_points_added}"})

    except Exception as e:
        logging.error(f"Error updating points: {e}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
