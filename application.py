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
            session['score'] += 0.72
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
        
        password_error = validate_password(password1)
        if password_error:
            return render_template("register.html", message=password_error)

        if password1 != password2:
            return render_template("register.html", message="Password mismatch")

        existing_user = db.execute(text("SELECT * FROM Users WHERE email = :email"), {"email": email}).fetchone()
        if existing_user:
            return render_template("register.html", message="Email used")
        else:
            try:
                db.execute(text("INSERT INTO Users(username, full_name, email, password) VALUES (:username, :full_name, :email, :password)"),
                           {"username": username, "full_name": full_name, "email": email, "password": generate_password_hash(password1)})
            except Exception as e:
                return render_template("register.html", message=e)

            db.commit()

            Q = db.execute(text("SELECT * FROM Users WHERE email LIKE :email AND full_name LIKE :full_name"), {"email": email , "full_name": full_name }).fetchone()

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
        return jsonify({"status": "error", "message": str(e)})

#xóa trang

@app.route('/delete_vocabulary_page/<int:page_id>', methods=['DELETE'])
@login_required
def delete_vocabulary_page(page_id):
    try:
        user_id = session.get("user_id")
        logging.info(f"Deleting page_id: {page_id} for user_id: {user_id}")
        with engine.connect() as db:
            db.execute(text('DELETE FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id'), {"page_id": page_id, "user_id": user_id})
            logging.info(f"Deleted from LearningProgress")
            db.execute(text('DELETE FROM VocabularyPage WHERE page_id = :page_id AND user_id = :user_id'), {"page_id": page_id, "user_id": user_id})
            logging.info(f"Deleted from VocabularyPage")
            db.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/get_vocabulary_pages', methods=['GET'])
@login_required
def get_vocabulary_pages():
    user_id = session.get("user_id")
    try:
        with engine.connect() as db:
            pages = db.execute(
                text('SELECT page_id, page_name FROM VocabularyPage WHERE user_id = :user_id'),
                {"user_id": user_id}
            ).fetchall()
            pages = [{"page_id": page.page_id, "page_name": page.page_name} for page in pages]
            return jsonify({"status": "success", "pages": pages})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
#lưu từ vào trang

@app.route('/save_words_to_existing_page', methods=['POST'])
@login_required
def save_words_to_existing_page():
    try:
        data = request.get_json()
        existing_page_id = data.get('existing_page_id')
        words = data.get('words')

        if not existing_page_id or not words:
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        user_id = session.get("user_id")

        with engine.connect() as db:
            word_count = db.execute(
                text('SELECT COUNT(*) FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id'),
                {"page_id": existing_page_id, "user_id": user_id}
            ).scalar()

            if word_count + len(words) > 10:
                return jsonify({"status": "error", "message": "The page already has too many words. Please create a new page."}), 400

            insert_query = text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)')
            for word in words:
                try:
                    db.execute(
                        insert_query,
                        {"page_id": existing_page_id, "user_id": user_id, "word_id": word['word_id']}
                    )
                except Exception as e:
                    if "duplicate key value violates unique constraint" in str(e):
                        return jsonify({"status": "error", "message": f"Word with ID {word['word_id']} already exists on this page."}), 400
                    else:
                        raise e
            db.commit()

        return jsonify({"status": "success", "message": "Words saved successfully!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/saved_words', methods=['GET', 'POST'])
@login_required
def saved_words():
    pass

#xóa từ
@app.route('/delete_words/<int:page_id>', methods=['GET'])
@login_required
def delete_words(page_id):
    user_id = session.get("user_id")
    try:
        with engine.connect() as db:
            # Truy vấn thông tin các từ trong learningprogress
            words = db.execute(
                text('SELECT v.word, v.pronunciation, v.meaning, lp.word_id '
                     'FROM LearningProgress lp '
                     'JOIN Vocabulary v ON lp.word_id = v.word_id '
                     'WHERE lp.page_id = :page_id AND lp.user_id = :user_id'),
                {"page_id": page_id, "user_id": user_id}
            ).fetchall()
        
        return render_template('delete_words.html', page_id=page_id, words=words)
    except Exception as e:
        return render_template("error.html", message=str(e))
    

@app.route('/confirm_delete/<int:page_id>', methods=['POST'])
@login_required
def confirm_delete(page_id):
    user_id = session.get("user_id")
    selected_words = request.form.getlist('selected_words')
    if not selected_words:
        flash("No words selected for deletion.")
        return redirect(url_for('delete_words', page_id=page_id))

    try:
        with engine.connect() as db:
            delete_query = text('DELETE FROM LearningProgress '
                                'WHERE page_id = :page_id AND user_id = :user_id AND word_id = :word_id')
            for word_id in selected_words:
                db.execute(delete_query, {"page_id": page_id, "user_id": user_id, "word_id": word_id})
            db.commit()
        flash("Selected words deleted successfully.")
        return redirect(url_for('view_page', page_id=page_id))
    except Exception as e:
        return render_template("error.html", message=str(e))


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
        return render_template("error.html", message=str(e))
    
#RECOMMAND
@app.route('/recommend/<int:page_id>', methods=['GET'])
@login_required
def recommend(page_id):
    try:
        user_id = session.get("user_id")
        
        # Step 1: Get the current page's name
        current_page = db.execute(
            text('SELECT page_name FROM VocabularyPage WHERE page_id = :page_id AND user_id = :user_id'),
            {"page_id": page_id, "user_id": user_id}
        ).fetchone()

        if not current_page:
            flash("Page not found.")
            return redirect(url_for('VocabularyPage'))

        page_name = current_page.page_name

        # Step 2: Find other pages with the same name but different user_id
        similar_pages = db.execute(
            text('SELECT page_id FROM VocabularyPage WHERE page_name = :page_name AND user_id != :user_id'),
            {"page_name": page_name, "user_id": user_id}
        ).fetchall()

        if not similar_pages:
            flash("No similar pages found.")
            return redirect(url_for('view_page', page_id=page_id))

        similar_page_ids = [page.page_id for page in similar_pages]

        # Step 3: Get words from these pages
        word_ids = db.execute(
            text('SELECT DISTINCT word_id FROM LearningProgress WHERE page_id IN :page_ids'),
            {"page_ids": tuple(similar_page_ids)}
        ).fetchall()

        if not word_ids:
            flash("No words found from similar pages.")
            return redirect(url_for('view_page', page_id=page_id))

        word_ids = [word.word_id for word in word_ids]

        # Step 4: Fetch word details, excluding words already in the current page
        current_page_word_ids = db.execute(
            text('SELECT word_id FROM LearningProgress WHERE page_id = :page_id'),
            {"page_id": page_id}
        ).fetchall()
        
        current_page_word_ids = [word.word_id for word in current_page_word_ids]

        filtered_word_ids = [word_id for word_id in word_ids if word_id not in current_page_word_ids]

        if not filtered_word_ids:
            flash("No new words found.")
            return redirect(url_for('view_page', page_id=page_id))

        # Limit to 10 words
        filtered_word_ids = filtered_word_ids[:10]

        suggested_words = db.execute(
            text('SELECT * FROM Vocabulary WHERE word_id IN :word_ids'),
            {"word_ids": tuple(filtered_word_ids)}
        ).fetchall()

        return render_template('recommend.html', page={"page_id": page_id, "page_name": page_name}, suggested_words=suggested_words)
    except Exception as e:
        return render_template("error.html", message=str(e))

@app.route('/save_suggestions/<int:page_id>', methods=['POST'])
@login_required
def save_suggestions(page_id):
    try:
        user_id = session.get("user_id")
        selected_words = request.form.getlist('selected_words')

        if not selected_words:
            flash("No words selected.")
            return redirect(url_for('recommend', page_id=page_id))

        for word_id in selected_words:
            db.execute(
                text('INSERT INTO LearningProgress (page_id, user_id, word_id, score) VALUES (:page_id, :user_id, :word_id, 0)'),
                {"page_id": page_id, "user_id": user_id, "word_id": word_id}
            )
        db.commit()

        flash("Words saved successfully.")
        return redirect(url_for('view_page', page_id=page_id))
    except Exception as e:
        return render_template("error.html", message=str(e))

@app.route('/view_page/<int:page_id>')
@login_required
def view_page(page_id):
    user_id = session.get("user_id")
    try:
        page = db.execute(
            text('SELECT * FROM VocabularyPage WHERE page_id = :page_id AND user_id = :user_id'),
            {"page_id": page_id, "user_id": user_id}
        ).mappings().fetchone()
        
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

        # Fetch the words with score
        words = db.execute(
            text('''
                SELECT v.word, v.pronunciation, v.meaning, lp.score
                FROM Vocabulary v
                JOIN LearningProgress lp ON v.word_id = lp.word_id
                WHERE v.word_id IN :word_ids AND lp.page_id = :page_id
            '''),
            {"word_ids": tuple(word_ids), "page_id": page_id}
        ).mappings().all()

        # Convert RowMapping to dictionary and calculate percentages
        words = [dict(word) for word in words]
        for word in words:
            word['percentage'] = min((word['score'] / 100) * 100, 100)
        
        return render_template('view_page.html', page=page, words=words)
    except Exception as e:
        return render_template("error.html", message=str(e))
    
# FLASHCARD 
    
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
        if quiz_type in ['fill_in_the_blanks', 'word_to_meaning', 'meaning_to_word' , 'flashcard']:
            return redirect(url_for(quiz_type))

    return render_template('quiz.html')


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
        return render_template("error.html", message="No vocabulary found")

    question_text = getattr(question, question_col)
    correct_answer = getattr(question, answer_col)

    choices = get_random_choices(correct_answer, answer_col)
    choices.append(correct_answer)

    return render_question(question_text, correct_answer, choices)

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

@app.route('/next', methods=['POST'])
def next_question():
    session['question_number'] += 1
    return redirect(url_for('multiple_choice'))

@app.route('/restart_quiz')
def restart_quiz():
    session['score'] = 0
    session['question_number'] = 0
    return redirect(url_for('quiz'))

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
        return redirect(url_for('VocabularyPage'))

    try:
        words = db.execute(
            text('SELECT * FROM Vocabulary WHERE word_id IN (SELECT word_id FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id) ORDER BY RANDOM() LIMIT 5'),
            {"page_id": page_id, "user_id": user_id}
        ).fetchall()

        if not words:
            flash("No words found in the selected vocabulary page. Please add words before playing the game.")
            return redirect(url_for('VocabularyPage'))

        meanings = [word.meaning for word in words]
        random.shuffle(meanings)

        return render_template('matching_game.html', words=words, meanings=meanings, page_id=page_id)
    except Exception as e:
        flash("An error occurred while fetching words for the matching game. Please try again.")
        return redirect(url_for('VocabularyPage'))

@app.route('/check_matching_answers', methods=['POST'])
@login_required
def check_matching_answers():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No data provided or invalid JSON format.")

        results = data.get('results', [])
        page_id = data.get('page_id')

        if not results or not page_id:
            raise ValueError("Missing results or page_id in the request data.")

        user_id = session.get('user_id')
        word_ids = [item['word_id'] for item in results]

        correct_answers = db.execute(
            text('SELECT word_id, meaning FROM Vocabulary WHERE word_id IN :word_ids'),
            {"word_ids": tuple(word_ids)}
        ).fetchall()

        correct_answers_dict = {row.word_id: row.meaning for row in correct_answers}

        user_correct_answers = {}
        for item in results:
            word_id = item['word_id']
            user_answer = item['meaning']
            correct_answer = correct_answers_dict.get(word_id)

            if user_answer == correct_answer:
                user_correct_answers[word_id] = user_answer

        return jsonify({"status": "success", "correct_answers": user_correct_answers, "message": "Answers have been checked successfully.", "page_id": page_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_points_matching_game', methods=['POST'])
@login_required
def update_points_matching_game():
    data = request.get_json()
    user_id = session.get('user_id')

    try:
        correct_answers = data.get('correct_answers')
        page_id = data.get('page_id')
        time_left = data.get('time_left')  # Lấy thời gian còn lại

        print(f"Received page_id: {page_id}")  # In ra để kiểm tra giá trị page_id
        print(f"Time left: {time_left}")  # In ra để kiểm tra thời gian còn lại

        if not isinstance(page_id, int):
            page_id = int(page_id)  # Chuyển đổi page_id thành số nguyên nếu cần

        points_per_correct = 0  # Giá trị mặc định

        if 31 <= time_left <= 60:
            points_per_correct = 0.82
        elif 0 <= time_left <= 30:
            points_per_correct = 0.75

        if points_per_correct == 0:
            raise ValueError("Time left out of valid range.")

        # Update score in LearningProgress table
        for word_id, meaning in correct_answers.items():
            db.execute(
                text('''
                    UPDATE LearningProgress
                    SET score = score + :points_per_correct
                    WHERE page_id = :page_id AND user_id = :user_id AND word_id = :word_id
                '''),
                {
                    "points_per_correct": points_per_correct,
                    "page_id": page_id,
                    "user_id": user_id,
                    "word_id": word_id
                }
            )

        db.commit()
        flash(f"Correct! You earned {points_per_correct} points for each correct answer.", "success")
        return jsonify({"status": "success", "message": "Points have been successfully updated."})
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
