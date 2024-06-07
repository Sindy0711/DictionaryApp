import os , csv
import re
import html

from sqlalchemy import create_engine , text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError

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
    try:
        with open("dataapp.csv", "r" , encoding="utf-8",  errors='ignore') as f:
            reader = csv.reader(f)
            next(reader)
            for ma_tu_vung, tu, phienam, nghia, motachung in reader:
                
                tu = convert_html_chars(replace_br_and_plus(clean_html(tu)))
                phienam = convert_html_chars(replace_br_and_plus(clean_html(phienam)))
                nghia = convert_html_chars(replace_br_and_plus(clean_html(nghia)))
                motachung = convert_html_chars(replace_br_and_plus(clean_html(motachung)))

                try:
                    db.execute(
                        text("INSERT INTO TuVung (tu, phienam, nghia, motachung) VALUES (:tu, :phienam, :nghia, :motachung)"), {"tu": tu, "phienam": phienam, "nghia": nghia, "motachung" : motachung})
                    db.commit()
                    
                    print(f"Added word with tu: {tu} phienam: {phienam}  nghia: {nghia} motachung: {motachung} ")
                except IntegrityError:
                    print(f"Word {tu} already exists in the database.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
