from flask import Flask, g
from flask_cors import CORS
import mysql.connector
import json
import os

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    config_path = os.path.join(app.instance_path, "config.json")
    with open(config_path) as config_file:
        app.config.update(json.load(config_file))

    CORS(app)

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    def get_db_connection():
        if "db" not in g:
            g.db = mysql.connector.connect(
                host=app.config["MySQLServer"],
                database=app.config["MySQLDatabase"],
                user=app.config["MySQLUsername"],
                password=app.config["MySQLPassword"]
            )
        return g.db

    @app.before_request
    def before_request():
        g.db = get_db_connection()

    @app.teardown_request
    def teardown_request(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app
