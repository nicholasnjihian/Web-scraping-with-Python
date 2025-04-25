#!/usr/bin/env python3

from seleniumwire import webdriver # Note: this replaces regular Selenium WebDriver

from webdriver_manager.firefox import GeckoDriverManager

from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options

import json
import time

from datetime import datetime, timezone

import pytz

import logging
import os
import glob

# Enables capturing network logs
options = Options()
options.headless = False  # Set to True if you want headless mode


# GECKODRIVER_PATH="/home/nicknjihia/Downloads/geckodriver-v0.36.0-linux64/geckodriver"

service = FirefoxService(executable_path=GeckoDriverManager().install())

#driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
driver = webdriver.Firefox(seleniumwire_options={}, service=service, options=options)


tournament_games = []

countries = ["England","Spain","Italy","Germany","France",
             "Netherlands","Türkiye","Portugal","Belgium","Scotland"]


club_leagues = ["Premier League","LaLiga","Serie A","Bundesliga","Ligue 1",
                "Eredivisie","Super Lig","LaLiga 2","Championship","2.Bundesliga",
                "Serie B","Ligue 2","Liga Portugal Betclic","First Division A","Premiership"]


# Change this date as required.
todays_date = "2025-04-21"



# Configure logging

## Check if a log file exists, otherwise create file
## if one exists, create new file with number appended to filename.

def get_new_log_filename(base_name="sofascore_script.log"):
    """Check for existing log files and create a new one with an incremented number."""
    if not os.path.exists(base_name):
        return base_name  # No existing log, use default name

    # Get all log files that match "app_*.log"
    existing_logs = glob.glob("sofascore_script_*.log")

    # Extract numbers and find the highest
    numbers = [int(log.split("_")[-1].split(".")[0]) for log in existing_logs if log.split("_")[-1].split(".")[0].isdigit()]
    new_number = max(numbers) + 1 if numbers else 1
    return f"sofascore_script_{new_number}.log"

# Determine the new log filename
log_filename = get_new_log_filename()


## Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

## Set format
formatter = logging.Formatter(
    "{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
)

## Create file handler
### Append instead of overwrite
main_file_handler = logging.FileHandler(log_filename, mode="a", encoding="utf-8")
main_file_handler.setLevel(logging.DEBUG)
main_file_handler.setFormatter(formatter)
logger.addHandler(main_file_handler)


## Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("Started!😄🙌😃 ")

# Open the webpage

main_webpage = f"https://www.sofascore.com/football/{todays_date}"
logger.info(f"▶️   Visiting: {main_webpage}")


try:
    driver.get(main_webpage)
    logger.info(f"🗿 Visiting the home page URL: {main_webpage}.")
    logger.info("**************************************************************************************\n")
except Exception as err:
    logger.exception(f"😭 Failure visiting home page URL {err}.\n")


log_entries = driver.get_log("performance")

# Process logs to extract API JSON responses:

scheduled_date_api = "/api/v1/sport/football/scheduled-events/" + todays_date

for request in driver.requests:
    if request.response and scheduled_date_api in request.url:
        logger.debug(f"\n[URL] {request.url}")
        logger.debug(f"[Request Headers] {request.headers}")
        logger.debug(f"[Response Headers] {request.response.headers}")

        if 'application/json' in request.response.headers.get('Content-Type', ''):
            try:
                body = request.response.body.decode('utf-8')
                data = json.loads(body)
                logger.debug("[Parsed JSON]")
                logger.debug(json.dumps(data, indent=2))
            except Exception as err:
                logger.exception(f"Failed to load JSON from API URL {scheduled_date_api}.\n")


driver.quit()

# Force writing logs to the file
