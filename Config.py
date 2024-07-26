import shutil
import os
import json

class Config:
    def __init__(self):
        self.cfg = None

        self.create_config()
        self.parse_config()

        if not self.cfg:
            print("Unable to read config file.")
            exit()

    def create_config(self):
        if (not os.path.isfile("CS2StatsAPI.json")):
            shutil.copy("CS2StatsAPITemplate.json", "CS2StatsAPI.json")
            print("Config file created 'CS2StatsAPI.json'. Enter your MySQL credentials and re-run.")
            exit()

    def parse_config(self):
        with open("CS2StatsAPI.json", "r") as f:
            self.cfg = json.load(f)
