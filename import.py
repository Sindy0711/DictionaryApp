import os , csv
import re
import html

from sqlalchemy import create_engine , text
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def replace_br_and_plus(text):
    text = text.replace('<br />', '\n').replace('<br>=', '\n')
    return text

def convert_html_chars(text):
    return html.unescape(text)

def main():
    f = open("dataapp.csv", "r" , encoding="utf-8",  errors='ignore')
    reader = csv.reader(f)
    next(reader)
    for id, tu, phienam, nghia, motachung in reader:
        
        tu = convert_html_chars(replace_br_and_plus(clean_html(tu)))
        phienam = convert_html_chars(replace_br_and_plus(clean_html(phienam)))
        nghia = convert_html_chars(replace_br_and_plus(clean_html(nghia)))
        motachung = convert_html_chars(replace_br_and_plus(clean_html(motachung)))

        
        existing_word = db.execute(
            text("SELECT * FROM tuvung WHERE tu = :tu"),
            {"tu": tu}).fetchone()
        
        if existing_word is None:
            db.execute(
                text("INSERT INTO tuvung (tu, phienam, nghia, motachung) VALUES (:tu, :phienam, :nghia, :motachung)"),
                {"tu": tu, "phienam": phienam, "nghia": nghia})
            db.commit()
            
            print(f"Added word with tu: {tu} phienam: {phienam}  nghia: {nghia} motachung: {motachung} ")
    f.close()

if __name__ == '__main__':
    main()
