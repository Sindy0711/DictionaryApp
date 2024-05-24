import os , csv

from sqlalchemy import create_engine , text
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    f = open("dataapp.csv", "r" , encoding="utf-8")  # needs to be opened during reading csv
    reader = csv.reader(f)
    next(reader)
    for id, tu, phienam, nghia, motachung in reader:
        db.execute(
            text("INSERT INTO tuvung (tu, phienam, nghia, motachung) VALUES (:tu, :phienam, :nghia, :motachung)"),
               {"tu": tu, "phienam": phienam, "nghia": nghia, "motachung": motachung})
        db.commit()
        print(f"Added word with tu: {tu} phienam: {phienam}  nghia: {nghia}  motachung: {motachung}")
    f.close()

if __name__ == '__main__':
    main()