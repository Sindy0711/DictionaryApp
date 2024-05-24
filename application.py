import os
from functools import wraps
from sqlalchemy import create_engine, text
from flask import Flask, session, render_template, redirect, request, url_for
from flask_session import Session

from dotenv import load_dotenv
load_dotenv() 

app = Flask(__name__)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
# db = scoped_session(sessionmaker(bind=engine))



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
    if request.method == 'POST':
        query = request.form.get('query')
        with engine.connect() as connection:
            result = connection.execute(text("SELECT tu, phienam, nghia, motachung FROM tuvung WHERE tu LIKE :query"), {"query": f"%{query}%"})
            results = result.fetchall()
        return render_template('search.html', results=results, query=query)
    return render_template('search.html')
if __name__ == "__main__":
    app.run(debug=True)