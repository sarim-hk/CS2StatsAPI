from flask import Flask, g
from flask_cors import CORS
import mysql.connector
import json
import os

def get_db_connection(config):
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=config["MySQLServer"],
            database=config["MySQLDatabase"],
            user=config["MySQLUsername"],
            password=config["MySQLPassword"]
        )
    return g.db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    with open(os.path.join(app.instance_path, "config.json")) as config_file:
        app.config.update(json.load(config_file))

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    @app.before_request
    def before_request():
        get_db_connection(app.config)

    @app.teardown_request
    def teardown_request(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app