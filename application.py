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

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        query = request.form.get("input-search")
        if query is None:
            return render_template("error.html", message="Search field can not be empty!")
        try:
            result = db.execute(text('SELECT * FROM Vocabulary WHERE LOWER(word) LIKE :query'), {"query": "%" + query.lower() + "%"}).fetchall()
        except Exception as e:
            return render_template("error.html", message=e)
        if not result:
            return render_template("error.html", message="Your query did not match any documents")
        return render_template("list.html", result=result)

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

@app.route('/api/et_vocabulary_pages', methods=['GET'])
@login_required
def et_vocabulary_pages():
    try:
        user_id = session.get("user_id")
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

        # Retrieve user_id from session
        user_id = session.get("user_id")

        with engine.connect() as connection:
            if page_name:
                result = connection.execute(text('INSERT INTO VocabularyPage (page_name, user_id) VALUES (:page_name, :user_id) RETURNING page_id'),
                                            {"page_name": page_name, "user_id": user_id})
                page_id = result.fetchone()[0]
            else:
                page_id = existing_page_id

            word_count = connection.execute(text('SELECT COUNT(*) FROM PageWords WHERE page_id = :page_id'), {"page_id": page_id}).scalar()
            if word_count + len(selected_words) > 10:
                flash("The page already has too many words. Please create a new page.")
                return redirect(url_for('search'))

            # Insert selected words into PageWords table
            insert_query = text('INSERT INTO PageWords (page_id, word, pronunciation, meaning) VALUES (:page_id, :word, :pronunciation, :meaning)')
            for word in selected_words:
                connection.execute(insert_query, {"page_id": page_id, "word": word['word'], "pronunciation": word['pronunciation'], "meaning": word['meaning']})
            connection.commit()

        session['selected_words'] = []  # Clear session after saving
        flash("Words saved successfully.")
        return redirect(url_for('VocabularyPage'))
    except Exception as e:
        logging.exception("Error saving words")
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

# @app.route('/multiple_choice', methods=['GET', 'POST'])
# def multiple_choice():
#     if request.method == 'POST':
#         page_id = request.form.get('page_id')
#         user_id = request.form.get('user_id')
#         word_id = request.form.get('word_id')

#         try:
#             Vocabulary = db.execute(text('SELECT * FROM LearningProgress WHERE page_id = :page_id AND user_id = :user_id AND word_id = :word_id'), 
#                         {"page_id": page_id, "user_id": user_id, "word_id": word_id}).fetchone()
#             if Vocabulary is None:
#                 return render_template("error.html", message="No vocabulary found")
            
#             question_text = Vocabulary.word
#             correct_answer = Vocabulary.meaning

#             # choices = db.execute(text('SELECT meaning FROM LearningProgress WHERE meaning != :correct_answer ORDER BY RANDOM() LIMIT 3')).fetchall()
#             choices = db.execute(text('SELECT meaning FROM Vocabulary WHERE meaning != :correct_answer ORDER BY RANDOM() LIMIT 3')).fetchall()
            
#             choice_a = choices[0].meaning
#             choice_b = choices[1].meaning
#             choice_c = choices[2].meaning

#             db.execute(text('INSERT INTO Questions (question_text, choice_a, choice_b, choice_c, correct_answer) VALUES (:question_text, :choice_a, :choice_b, :choice_c, :correct_answer)'), 
#                        {"question_text": question_text, "choice_a": choice_a, "choice_b": choice_b, "choice_c": choice_c, "correct_answer": correct_answer})
#             db.commit()
#         except Exception as e:
#             return render_template("error.html", message=str(e))

#         return redirect(url_for('page'))

#     return render_template('multiple_choice.html')

@app.route('/multiple_choice', methods=['GET', 'POST'])
def multiple_choice():
    if 'score' not in session:
            session['score'] = 0
    if request.method == 'POST':
        start_time = session.get('start_time')
        end_time = datetime.now()
        
        user_choice = request.form.get('user_choice')
        correct_answer = request.form.get('correct_answer')

        message = "Correct!" if user_choice == correct_answer else f"Incorrect. The correct answer is: {correct_answer}"
        
        if user_choice == correct_answer:
            session['score'] += 0.78
            if (end_time - start_time).total_seconds() <= 5:
                session['score'] += 1
        return jsonify({'message': message})

    session['start_time'] = datetime.now()

    vocabulary = db.execute(text("SELECT * FROM Vocabulary ORDER BY RANDOM() LIMIT 1")).fetchone()
    if vocabulary is None:
         return render_template("error.html", message="No vocabulary found")

    question_text = vocabulary.word
    correct_answer = vocabulary.meaning

    choices = db.execute(text('SELECT meaning FROM Vocabulary WHERE meaning != :correct_answer ORDER BY RANDOM() LIMIT 3'), 
                        {"correct_answer": correct_answer}).fetchall()

    choices = [choice.meaning for choice in choices]
    choices.append(correct_answer)

    random.shuffle(choices)

    db.execute(text('INSERT INTO Questions (question_text, choice_a, choice_b, choice_c, choice_d , correct_answer) VALUES (:question_text, :choice_a, :choice_b, :choice_c, :choice_d,  :correct_answer)'), 
        {"question_text": question_text, "choice_a": choices[0], "choice_b": choices[1], "choice_c": choices[2],"choice_d" : choices[3] , "correct_answer": correct_answer})
    db.commit()

    return render_template('multiple_choice.html', question_text=question_text, choices=choices, correct_answer=correct_answer)

@app.route('/view_session', methods=['GET'])
def view_session():
    session_data = {key: session[key] for key in session.keys()}
    return jsonify(session_data)

if __name__ == "__main__":
    app.run(debug=True)
