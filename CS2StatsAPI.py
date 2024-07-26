from Config import Config
from flask import Flask
import mysql.connector

app = Flask(__name__)

@app.route("/")
def ratio():
    return "Hello World!"

if __name__ == "__main__":
    cfg = Config()

    try:
        connection = mysql.connector.connect(
            host = cfg.cfg['MySQLServer'],
            database = cfg.cfg['MySQLDatabase'],
            user = cfg.cfg['MySQLUsername'],
            password = cfg.cfg['MySQLPassword']
        )

    except Exception as e:
        print("Failed to connect to the MySQL database.")
        print(e)
        exit()

    app.run(debug=True)