# DictionaryApp
 Project learning for school

## Proceed to download
1. Clone the repository
2. In your terminal window, navigate into the project
3. Run `pip3 install -r requirements.txt` to make sure all of the necessary Python packages (Flask, SQLAlchemy and others) are installed
4. Set the environment variables:
	* `export FLASK_APP=application.py`. On Windows, the command is instead `set FLASK_APP=application.py`
    - `DATABASE_URL` = URI for your local postgreSQL database (for example: `postgres://username:password@localhost:5432/databasename` )
5. Run `tables.sql` against your database to create the necessary tables
  
6. Run `python3 import.py` to import a spreadsheet in CSV format to your database
7. Finally execute `flask run` command in your terminal to start the server