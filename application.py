import os , re , logging
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, jsonify, session, render_template, redirect, request, url_for, flash
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
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

def get_current_user_id():
    user_id = session.get("user_id")
    if user_id:
        logging.debug(f"Current user_id from session: {user_id}")
    else:
        logging.debug("No user_id found in session")
    return user_id

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




@app.route('/')
def index():
    # if session.get("email") is not None:
    #     return render_template('index.html')
    # else:
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
        form_dang_nhap = request.form.get("username")
        form_email = request.form.get("email")
        form_password = request.form.get("password")

        if not form_email:
            return render_template("error.html", message="must provide username")
        elif not form_password:
            return render_template("error.html", message="must provide password")

        Q = db.execute(text("SELECT * FROM Users WHERE email LIKE :email AND username LIKE :username"), {"email": form_email, "username": form_dang_nhap}).fetchone()
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
        user_id = get_current_user_id()
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
                        text('INSERT INTO VocabularyPage (page_name, user_id) VALUES (:page_name, :user_id) RETURNING page_id'),
                        {"page_name": page_name, "user_id": user_id})
                    page_id = result.fetchone()[0]
                else:
                    page_id = existing_page_id

                insert_query = text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)')
                for word in selected_words:
                    connection.execute(insert_query, {"page_id": page_id, "user_id": user_id, "word_id": word})

                connection.commit()

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
        user_id = get_current_user_id()  # Thay thế bằng phương thức của bạn để lấy ID người dùng hiện tại
        with engine.connect() as connection:
            result = connection.execute(
                text('SELECT page_id, page_name FROM VocabularyPage WHERE user_id = :user_id'),
                {"user_id": user_id}
            ).fetchall()
            pages = [{"page_id": row[0], "page_name": row[1]} for row in result]  # Chuyển tuple thành dictionary
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

        with engine.connect() as connection:
            word_count = connection.execute(text('SELECT COUNT(*) FROM LearningProgress WHERE page_id = :page_id'), {"page_id": existing_page_id}).scalar()
            if word_count + len(selected_words) > 10:
                return jsonify({"status": "error", "message": "The page already has too many words. Please create a new page."})

            for word in selected_words:
                connection.execute(text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)'),
                                   {"page_id": existing_page_id, "user_id": 1, "word_id": word['word_id']})
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

        if not selected_words:
            flash("No words selected. Please select words to save.")
            return redirect(url_for('saved_words'))

        if not page_name and not existing_page_id:
            flash("Please enter a page name or select an existing page.")
            return redirect(url_for('saved_words'))

        try:
            with engine.connect() as connection:
                if page_name:
                    # Create a new vocabulary page
                    result = connection.execute(
                        text('INSERT INTO VocabularyPage (page_name, user_id) VALUES (:page_name, :user_id) RETURNING page_id'),
                        {"page_name": page_name, "user_id": user_id}
                    )
                    page_id = result.fetchone()[0]
                else:
                    # Use the existing page
                    page_id = int(existing_page_id)

                # Check the current number of words in the page
                word_count = connection.execute(
                    text('SELECT COUNT(*) FROM PageWords WHERE page_id = :page_id'),
                    {"page_id": page_id}
                ).scalar()

                if word_count + len(selected_words) > 10:
                    flash("The page already has too many words. Please create a new page.")
                    return redirect(url_for('saved_words'))

                # Insert selected words into the PageWords table
                insert_query = text(
                    'INSERT INTO PageWords (page_id, word, pronunciation, meaning) VALUES (:page_id, :word, :pronunciation, :meaning)'
                )
                for word_data in selected_words:
                    word = word_data['word']
                    pronunciation = word_data['pronunciation']
                    meaning = word_data['meaning']
                    connection.execute(insert_query, {
                        "page_id": page_id,
                        "word": word,
                        "pronunciation": pronunciation,
                        "meaning": meaning
                    })
                
                connection.commit()

            # Clear session after saving
            session['selected_words'] = []
            flash("Words saved successfully.")
            return redirect(url_for('saved_words'))

        except Exception as e:
            logging.exception("Error saving words")
            return render_template("error.html", message=str(e))

    # If GET request, show the saved words page
    return render_template('saved_words.html')

    
@app.route('/VocabularyPage')
@login_required
def VocabularyPage():
    try:
        user_id = get_current_user_id()
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
    user_id = get_current_user_id()
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
        flashcard = db.execute(text('''
            SELECT LearningProgress.*, Vocabulary.pronunciation, Vocabulary.meaning 
            FROM LearningProgress 
            JOIN Vocabulary ON LearningProgress.word_id = Vocabulary.word_id 
            ORDER BY RANDOM() 
            LIMIT 1
        ''')).fetchone()
        
    except Exception as e:
        return render_template("error.html", message=str(e))

    if not flashcard:
        return render_template("error.html", message="No flashcards available")
    return render_template("flashcard.html", flashcard=flashcard)

@app.route('/multiple_choice', methods=['GET', 'POST'])
def multiple_choice():
    if request.method == 'POST':
        page_id = request.form.get('page_id')
        user_id = request.form.get('user_id')
        word_id = request.form.get('word_id')

        try:
            Vocabulary = db.execute(text('SELECT * FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id AND word_id = :word_id'), 
                        {"page_id": page_id, "user_id": user_id, "word_id": word_id}).fetchone()
            if Vocabulary is None:
                return render_template("error.html", message="No vocabulary found")

            cau_hoi = Vocabulary.word
            correct_choice = Vocabulary.meaning

            choices = db.execute(text('SELECT meaning FROM LearningProgress WHERE meaning != :correct_choice ORDER BY RANDOM() LIMIT 3')).fetchall()
            choice_a = choices[0].meaning
            choice_b = choices[1].meaning
            choice_c = choices[2].meaning

            db.execute(text('INSERT INTO CauHoi (word, choice_a, choice_b, choice_c, correct_choice) VALUES (:cau_hoi, :choice_a, :choice_b, :choice_c, :correct_choice)'), 
                       {"cau_hoi": cau_hoi, "choice_a": choice_a, "choice_b": choice_b, "choice_c": choice_c, "correct_choice": correct_choice})
            db.commit()
        except Exception as e:
            return render_template("error.html", message=str(e))

        return redirect(url_for('page'))

    return render_template('multiple_choice.html')

#ghép từ
#lấy từ và nghĩa từ bảng tuvung


@app.route('/matching_game')
@login_required
def matching_game():
    user_id = get_current_user_id()
    page_id = request.args.get('page_id')

    if not page_id:
        flash("Page ID is required.")
        return redirect(url_for('page'))

    try:
        words = db.execute(
            text('SELECT * FROM Vocabulary WHERE word_id IN (SELECT word_id FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id) ORDER BY RANDOM() LIMIT 5'),
            {"page_id": page_id, "user_id": user_id}
        ).fetchall()

        if not words:
            flash("No words found for this page.")
            return redirect(url_for('page'))

        # Shuffle the meanings
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
    user_id = get_current_user_id()

    try:
        print("Incoming Data:", data)  # Debug print
        word_ids = [item['word_id'] for item in data]
        print("Extracted Word IDs:", word_ids)  # Debug print

        # Validate word_ids to ensure they are all integers
        word_ids = [int(word_id) for word_id in word_ids if word_id is not None and isinstance(word_id, int)]
        print("Validated Word IDs:", word_ids)  # Debug print

        if not word_ids:
            raise ValueError("Invalid word_ids: All word_ids must be integers.")

        # Fetch correct answers from database
        correct_answers = db.execute(
            text('SELECT word_id, meaning FROM Vocabulary WHERE word_id IN :word_ids'),
            {"word_ids": tuple(word_ids)}
        ).fetchall()
        print("Correct Answers from DB:", correct_answers)  # Debug print

        correct_answers_dict = {row.word_id: row.meaning for row in correct_answers}
        print("Correct Answers Dict:", correct_answers_dict)  # Debug print

        # Check user answers
        user_correct_answers = {}
        for item in data:
            word_id = item['word_id']
            user_answer = item['meaning']
            correct_answer = correct_answers_dict.get(word_id)

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
    user_id = get_current_user_id()  # Lấy ID của người dùng hiện tại từ hàm get_current_user_id()

    # Cấu hình logging
    logging.basicConfig(level=logging.DEBUG)

    try:
        # Lấy thông tin từ request JSON
        points_per_correct = data.get('points_per_correct')
        correct_answers = data.get('correct_answers')
        page_id = data.get('page_id')

        if not points_per_correct or not correct_answers or not page_id:
            raise ValueError("Missing required fields in JSON data")

        # Lấy danh sách word_ids từ correct_answers
        word_ids = list(correct_answers.keys())

        # Xác thực word_ids để đảm bảo tất cả đều là số nguyên
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

        # Cập nhật điểm cho từng từ
        for row in query:
            current_points = row.score if row.score is not None else 0
            new_points = min(current_points + points_per_correct, 10)

            # Thực hiện cập nhật vào cơ sở dữ liệu
            row.score = new_points
            row.last_study_date = datetime.utcnow()
            db.session.commit()

            total_points_added += new_points - current_points

        return jsonify({"status": "success", "message": f"Points updated successfully. Total points added: {total_points_added}"})

    except Exception as e:
        logging.error(f"Error updating points: {e}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
