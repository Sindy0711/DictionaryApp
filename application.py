import logging
import os
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, session, render_template, redirect, request, url_for, flash, jsonify
from flask_session import Session
from flask_paginate import Pagination
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print(result.fetchone())

# Tạo bảng SavedWords nếu chưa tồn tại
with engine.connect() as connection:
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS SavedWords (
            id SERIAL PRIMARY KEY,
            tu TEXT NOT NULL,
            phienam TEXT NOT NULL,
            nghia TEXT NOT NULL
        )
    '''))
    connection.commit()
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
    return render_template('index.html')

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
        offset = (page - 1) * 20
        query_like = f"%{query.lower()}%"
        total = db.execute(text('SELECT COUNT(*) FROM tuvung WHERE LOWER(tu) LIKE :query'), {"query": query_like}).scalar()
        result = db.execute(text('SELECT * FROM tuvung WHERE LOWER(tu) LIKE :query ORDER BY tu LIMIT :limit OFFSET :offset'), 
                             {"query": query_like, "limit": per_page, "offset": offset}).fetchall()
        pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

        selected_words = session.get('selected_words', [])
        return render_template("list.html", result=result, pagination=pagination, selected_words=selected_words)
    except Exception as e:
        logging.exception("Error during search")
        return render_template("error.html", message=str(e))

@app.route('/save_words', methods=['POST'])
def save_words():
    try:
        selected_words = session.get('selected_words', [])
        if not selected_words:
            flash("No words to save.")
            return redirect(url_for('search'))

        for word in selected_words:
            db.execute(text('INSERT INTO SavedWords (tu, phienam, nghia) VALUES (:tu, :phienam, :nghia)'),
                       {"tu": word['tu'], "phienam": word['phienam'], "nghia": word['nghia']})
        db.commit()
        session['selected_words'] = []  # Clear session after saving
        flash("Words saved successfully.")
        return redirect(url_for('saved_words'))  # Redirect to saved_words
    except Exception as e:
        logging.exception("Error saving words")
        return render_template("error.html", message=str(e))

@app.route('/saved_words')
def saved_words():
    try:
        saved_words = db.execute(text('SELECT * FROM SavedWords')).fetchall()
        return render_template('saved_words.html', saved_words=saved_words)
    except Exception as e:
        logging.exception("Error fetching saved words")
        return render_template("error.html", message=str(e))

@app.route('/save_selected_words', methods=['POST'])
def save_selected_words():
    selected_words = request.get_json()
    session['selected_words'] = selected_words
    return jsonify({'status': 'success'})

@app.route('/delete_word/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    try:
        db.execute(text('DELETE FROM SavedWords WHERE id = :id'), {"id": word_id})
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.exception("Error deleting word")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == "__main__":
    app.run(debug=True)
