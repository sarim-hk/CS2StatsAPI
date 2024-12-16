from flask import Flask, g
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from .jobs.set_player_of_the_week import set_player_of_the_week
import mysql.connector
import json
import os
import multiprocessing

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    config_path = os.path.join(app.instance_path, "config.json")
    with open(config_path) as config_file:
        app.config.update(json.load(config_file))

    CORS(app)

    # Register blueprint
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Database connection
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

    # Scheduler setup
    scheduler = BackgroundScheduler()

    def start_scheduler():
        if app.debug:
            print("Starting scheduler in debug mode...")
            scheduler.add_job(func=set_player_of_the_week, trigger="cron", day_of_week="mon", hour=17, minute=10, args=[app, get_db_connection])
            scheduler.start()
            
        else:
            if multiprocessing.current_process().name == "MainProcess":
                print("Starting scheduler in production mode (master process)...")
                scheduler.add_job(func=set_player_of_the_week, trigger="cron", day_of_week="mon", hour=0, minute=0, args=[app, get_db_connection])
                scheduler.start()
            else:
                print("Skipping scheduler startup in worker process...")

    # Start the scheduler
    start_scheduler()

    # Graceful shutdown of the scheduler
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        if scheduler.running:
            scheduler.shutdown(wait=False)

    return app
