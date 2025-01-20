from apscheduler.schedulers.background import BackgroundScheduler
from scheduler.jobs.set_player_of_the_week import set_player_of_the_week
import mysql.connector
import json
import os

def get_db_connection(config):
    return mysql.connector.connect(
        host=config["MySQLServer"],
        database=config["MySQLDatabase"],
        user=config["MySQLUsername"],
        password=config["MySQLPassword"]
    )

def create_scheduler():
    with open(os.path.join("instance", "config.json")) as config_file:
        config = json.load(config_file)
    
    scheduler = BackgroundScheduler()
    
    try:
        print("Scheduler is running...")
        db = get_db_connection(config)
        scheduler.add_job(func=set_player_of_the_week, trigger="cron", day_of_week="mon", hour=0, minute=0, args=[db])

    except Exception as e:
        print(e)
    
    return scheduler
