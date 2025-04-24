#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


from webdriver_manager.firefox import GeckoDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


import json
import time

from datetime import datetime, timezone

import pytz

import logging
import os
import glob




# Enables capturing network logs
options = webdriver.ChromeOptions()
options.set_capability(
    'goog:loggingPrefs',{"performance":"ALL","browser":"ALL"}
)

# Disable GPU and Use Software Rendering
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")  # Forces software rendering

# Disable Unnecessary Chrome Features
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
# options.add_argument("--no-sandbox")

# The argument '--disable-dev-shm-usage' forces Chrome to use the /tmp directory.
# This may slow down the execution though since disk will be used instead of memory:
# options.add_argument("--disable-dev-shm-usage")

options.add_argument("--disable-popup-blocking")  # Block pop-ups
# options.add_argument("--auto-open-devtools-for-tabs") # Open DevTools by default

# Load the Page in Headless Mode (Page is resource-heavy).
#options.add_argument("--headless")


options.add_experimental_option(
    "prefs", {"profile.default_content_setting_values.notifications": 2}
)

options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Optional to suppress warnings

GECKODRIVER_PATH="/home/nicknjihia/Downloads/geckodriver-v0.36.0-linux64/geckodriver"

service = FirefoxService(executable_path=GECKODRIVER_PATH)

#driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
driver = webdriver.Firefox(service=service)


driver.set_page_load_timeout(60)

driver.execute_cdp_cmd("Network.enable", {})

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


driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
# Extract Network Logs
log_entries = driver.get_log("performance")

# Process logs to extract API JSON responses:

scheduled_date_api = "/api/v1/sport/football/scheduled-events/" + todays_date

logs = [json.loads(log["message"])["message"] for log in log_entries]
for log in logs:
    api_path = log["params"].get('headers',{}).get(':path','')
    if scheduled_date_api == api_path:
        logger.info(f"Match {api_path} == {scheduled_date_api}")
        break
try:
    events = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
except Exception as err:
    logger.exception("😭 Failed to load JSON from API URL {scheduled_date_api}.\n")

# Need to make sure the UNIX timestamps for the games is matching the date specified by 'todays_date'
def convert_unix_to_time(unix_timestamp):
    # Convert UNIX timestamp to timezone="Africa/Nairobi"
    date_utc = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    target_timezone = pytz.timezone("Africa/Nairobi")
    local_time = date_utc.astimezone(target_timezone)
    local_time = local_time.isoformat()

    # Format time in 24-hour format (HH:MM:SS)
    date = local_time.split("T")[0]
    time = (local_time.split("T")[1]).split("+")[0]
    return (date, time)


for scheduled_games in events['events']:
    tournament_game = dict()
    league_name = scheduled_games["tournament"]["name"]
    logger.info(f"League Name: {league_name}")
    try:
        category = scheduled_games["tournament"]["category"]
        country = category["country"]["name"]
        logger.info(f"Country: {country}")
    except KeyError:
        logger.error("Key not found -> category['country']['name']")
        continue
    except Exception as e:
        logger.error(f"Tournament is likely irrelevant. Check error:\n{e}",
                     exc_info=True )


    date_value, time_value = convert_unix_to_time(scheduled_games["startTimestamp"])
    printed_datetime = f"{date_value}\t{time_value}"

    if country in countries and league_name in club_leagues and date_value == todays_date:
        tournament_game['League'] = league_name

        tournament_game['Custom ID'] = scheduled_games['customId']
        tournament_game['Home Team'] = scheduled_games["homeTeam"]['name']
        tournament_game['Away Team'] = scheduled_games["awayTeam"]['name']
        tournament_game['ID'] = scheduled_games['id']
        tournament_game['MatchUp'] = scheduled_games["slug"]
    if len(tournament_game) != 0:
        tournament_games.append(tournament_game)

logger.info(f"\nTournament Games: {tournament_games}\n")



redirect_base_url = "https://www.sofascore.com/football/match/"

# Initialize a counter for the array storing the game details/attrs above so as to append new attrs
counter = 0


# Iterate through the array above using the attrs to go through the individual web pages for the match-ups.
## TODO: Needs to be efficient somehow.

for match in tournament_games:
    match_ID = match['ID']

    redirect_url = f"{redirect_base_url}{match['MatchUp']}/{match['Custom ID']}#id:{match_ID}"

    try:

        driver.get(redirect_url)
        logger.info(f"\tRedirecting to the Standings Web page (for the upcoming match):=> \n📌\t{redirect_url}\n")
        logger.info("************************************************************************************\n")

    except Exception as err:
        logger.exception(f"😫 Could not redirect to URL: {redirect_url}. \tError {err}\n")

    try:
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button pBEmc')]")
        close_button.click()
        logger.info("Popup was closed.\n")

    except Exception as err:
        logger.error(f"Popup not present or popup didn't close.\nSee Error: {err}\n\n")

    # Filter and Extract JSON Responses from Multiple Endpoints

    # API URL for standings
    standings_url = f"/api/v1/event/{match_ID}/pregame-form"

    driver.find_element("tag name", "body").send_keys(Keys.CONTROL, "r")
    driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


    # Get all Performance Logs
    log_entries_rankings_raw = driver.get_log("performance")

    # Filter and Extract JSON Responses from Multiple Endpoints
    logs_standings = [json.loads(log_er_raw['message'])['message'] for log_er_raw in log_entries_rankings_raw]
    for log in logs_standings:
        api_path = log['params'].get('headers',{}).get(':path','')
        if standings_url == api_path:
            logger.debug(f"📍✅   Match {standings_url}  :----->  {api_path}\n")
            break
        else:
            logger.debug(f"❌ No Match -> API URL: {standings_url};\t{api_path}")

    try:
        pregame_rank_json = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
    except Exception as error:
        logger.exception(f"⚠️  Could not retrieve response: {error}")

    tournament_games[counter]["Home Team Rank"] = pregame_rank_json["homeTeam"]["position"]
    tournament_games[counter]["Away Team Rank"] = pregame_rank_json["awayTeam"]["position"]

    driver.refresh()
    driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")


    try:
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button pBEmc')]")
        close_button.click()
        logger.info("Popup closed.")

    except Exception as err:
        logger.error(f"Popup not present or popup didn't close. See Error: {err}\n")

    time.sleep(3)

    driver.find_element("tag name", "body").send_keys(Keys.CONTROL, "r")
    driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")

    api_base_url_team_info = f"/api/v1/event/{match_ID}"

    log_entries_team_info_raw = driver.get_log("performance")

    logs_team_info = [json.loads(log_eti_raw['message'])['message'] for log_eti_raw in log_entries_team_info_raw]

    for log in logs_team_info:
        api_path = log['params'].get('headers',{}).get(':path','')
        if api_base_url_team_info == api_path:
            logger.debug(f"📍✅   Match {api_base_url_team_info}:----> {api_path}\n")
            break
        else:
            logger.debug(f"❌ No match with API URL: {api_base_url_team_info};\t{api_path}")

    try:
        team_info_json = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
    except Exception as e:
        logger.exception(f"⚠️  Could not retrieve response from URL {api_base_url_team_info}.\nError: {e}\n")


    team_names = []
    team_ids = []
    team_names.append(team_info_json['event']['homeTeam']['slug'])
    team_ids.append(team_info_json['event']['homeTeam']['id'])
    team_names.append(team_info_json["event"]["awayTeam"]["slug"])
    team_ids.append(team_info_json['event']['awayTeam']['id'])


    logger.debug("Standings:")
    logger.debug(f"{tournament_games[counter]}")
    logger.debug("\nTeam Info:")
    logger.debug(f"Team Names: {team_names}; Team IDs{team_ids}\n")

    # Home & Away Team Web pages:

    team_base_url = "https://www.sofascore.com/team/football/"

    home_team_redirect_url = team_base_url + team_names[0] + "/" + str(team_ids[0]) + "#tab:matches"
    away_team_redirect_url = team_base_url + team_names[1] + "/" + str(team_ids[1]) + "#tab:matches"

    # Get JSON body with previous match results.
    # Ensure are matches of the league in question (Premier League or EPL, LaLiga, LaLiga 2, Championship, etc).
    # Get at least 10 of last matchups.
    # Maybe ensure there are at least 4 (previous) home matches for the home team &
    # 4 (previous) matches for away team.

    # The JSON output has the latest matchups at the bottom and the oldest at the top

    # Retrieve the following info from the matchups:
    # 1. Is team Home / Away?
    # 2. Score:
    #    a. Goals Scored
    #    b. Goals Conceded
    # 3. Actual Result (W/D/L)
    # 4. Team Standing
    # 5. Opponent Standing

    ## Home Team:

    try:
        driver.get(home_team_redirect_url)
        logger.info(f"📶🛜 Redirecting to the Web page of Home Team: {home_team_redirect_url}")
        logger.info("********************************************************************************\n\n")

    except Exception as err:
        logger.error(f"😫 Failure redirecting to {home_team_redirect_url}."
                     "\nError:\t{err}\n",
                     exc_info=True)

    driver.refresh()

    try:
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button pBEmc')]")
        close_button.click()
        logger.info("Popup was closed.\n")

    except Exception as err:
        logger.error(f"Popup not present or popup didn't close."
                     f"\nSee Error: {err}\n\n", exc_info=True)

    try:
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button gTStrj')]")
        close_button.click()
        logger.info("'Add to Favourites' popup was closed.\n")

    except Exception as err:
        logger.error(f"'Add to Favourites' popup isn't present or the popup didn't close."
                     f"\nSee Error: {err}\n\n", exc_info=True)

    driver.refresh()
    time.sleep(2)
    home_team_performance_api_url = f"/api/v1/team/{team_ids[0]}/performance"

    driver.find_element("tag name", "body").send_keys(Keys.CONTROL, "r")
    driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(3)

    log_entries_home_team = driver.get_log("performance")

    logs = [json.loads(log_entry_ht["message"])["message"] for log_entry_ht in log_entries_home_team]

    for log in logs:
        api_path = log["params"].get('headers',{}).get(':path','')
        if home_team_performance_api_url == api_path:
            logger.debug(f"📍✅   Match {home_team_performance_api_url}:---> {api_path}\n")
            break
        else:
            logger.debug(f"❌ No match with API URL: {home_team_performance_api_url};\t{api_path}")



    # The JSON output list needs to be reversed as the bottom values are the most recent matchups
    # Reverse in-place

    #max_retries = 2  # Set the number of retries
    #attempt = 0

    try:
        ht_prev_matches_json = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
    except Exception as e:
        logger.error("😫 Failed to get JSON output from API"
                         f" {home_team_performance_api_url}."
                         f" See error:\n{e}", exc_info=True)

    ht_prev_matches_json = ht_prev_matches_json['events'].reverse()
    ## The previous matches will be stored in arrays/lists of dictionaries, one array/list per home or away team - 2 arrays in total.

    ## [{'A/H': '<>', 'Result': '<W/D/L>', 'Scored': <num>, 'Conceded': <num>, 'Team Ranking': <num>, 'Opponent Rank': <num>}]

    prev_records_home_team_total = []

    # Going to use this URL to get the ranking from the pregame_form API URL endpoint.
    previous_game_base_url = "https://www.sofascore.com/football/match/"
    home_games_counter = 0

    for record in ht_prev_matches_json:
        # Only last four Home matches are required to be tracked:
        logger.debug(f"Counter: {home_games_counter}\n")

        individual_prev_home_team_record = {
            'A/H': None,
            'Result': None,
            'Scored': None,
            'Conceded': None,
            "Team Ranking": None,
            "Opponent Rank": None
        }

        if home_games_counter == 1:
            logger.debug(f"Record Output:\n%s", json.dumps(record, indent=3))

        if home_games_counter == 4:
            break

        if match['League'] != record['tournament']['name']:
            continue
        elif match['League'] == record['tournament']['name']:

            if match["Home Team"] == record['homeTeam']['name']:

                logger.debug(f"{match['Home Team']} was playing at home "
                      f"{record['homeTeam']['name']} against"
                      f" {record['awayTeam']['name']}. League =>"
                      f" {match['League']} matches {record['tournament']['name']}."
                     )

                home_games_counter += 1

                individual_prev_home_team_record["A/H"] = 'Home'

                if record["winnerCode"] == 1:
                    individual_prev_home_team_record['Result'] = 'Win'
                elif record["winnerCode"] == 3:
                    individual_prev_home_team_record['Result'] = 'Draw'
                elif record["winnerCode"] == 2:
                    individual_prev_home_team_record['Result'] = 'Loss'

                individual_prev_home_team_record['Scored'] = record['homeScore']['current']
                individual_prev_home_team_record['Conceded'] = record['awayScore']['current']

                previous_game_url = (previous_game_base_url + record['slug'] + '/' +
                str(record["customId"]) + "#id:" + str(record["id"]) + ",tab:standings")

                try:
                    driver.get(previous_game_url)
                    logger.info(f"🎯 Accessing URL: {previous_game_url}")
                    logger.info("******************************************************************\n")
                except Exception as err:
                    logger.error(f"😫 Failed getting rankings for a previous matchup.\n",
                                exc_info=True)

                time.sleep(3)
                driver.refresh()
                time.sleep(1)

                try:
                    close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button pBEmc')]")
                    close_button.click()
                    logger.info("Popup closed.\n")
                except Exception as err:
                    logger.error(f"Popup not present or popup didn't close."
                                 f"\nSee Error: {err}", exc_info=True)

                driver.find_element("tag name", "body").send_keys(Keys.CONTROL, "r")
                driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

                log_entries = driver.get_log("performance")

                prev_game_pregame_form_api_url = f"/api/v1/event/{record['id']}/pregame-form"

                for log in logs:
                    api_path = log["params"].get('headers',{}).get(':path','')
                    if prev_game_pregame_form_api_url == api_path:
                        logger.debug(f"📍✅   Match {prev_game_pregame_form_api_url}:---> {api_path}\n")
                        break
                    else:
                        logger.debug(f"❌ No match with API URL: {prev_game_pregame_form_api_url};\t{api_path}")


                try:
                    prev_matchup_event_json = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
                    individual_prev_home_team_record['Team Ranking'] = prev_matchup_event_json["homeTeam"]["position"]
                    individual_prev_home_team_record['Opponent Rank'] = prev_matchup_event_json["awayTeam"]["position"]
                except Exception as err:
                    logger.error(f"😫 Failed to get JSON from API URL: "
                                 "{prev_game_pregame_form_api_url}."
                                 "\nSee Error: {err}\n", exc_info=True)


            elif match['Home Team'] == record["awayTeam"]["name"]:
                logger.debug(f"\n{match['Home Team']} was playing away "
                      f"{record['awayTeam']['name']} against {record['homeTeam']['name']}"
                      f"{record['awayTeam']['name']}. League =>"
                      f" {match['League']} matches {record['tournament']['name']}."
                     )

                individual_prev_home_team_record["A/H"] = "Away"
                if record["winnerCode"] == 1:
                    individual_prev_home_team_record['Result'] = "Loss"
                elif record["winnerCode"] == 3:
                    individual_prev_home_team_record['Result'] = "Draw"
                elif record["winnerCode"] == 2:
                    individual_prev_home_team_record['Result'] = "Win"

                individual_prev_home_team_record["Conceded"] = record["homeScore"]["current"]
                individual_prev_home_team_record["Scored"] = record["awayScore"]["current"]

                previous_game_url = (previous_game_base_url + record["slug"] +
                "/" + str(record["customId"]) + "#id:" + str(record["id"]) + ",tab:standings")

                try:
                    driver.get(previous_game_url)
                    logging.info(f"🎯 Accessing the URL: {previous_game_url}")
                    logger.info("************************************************************************************\n")
                except Exception as err:
                    logger.error(f"😫 Failure getting rankings for a previous"
                                 " match. See Error:\n{err}\n", exc_info=True)

                time.sleep(3)
                driver.refresh()

                try:
                    close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Button pBEmc')]")
                    close_button.click()
                    logger.info("Popup was closed.\n")

                except Exception as err:
                    logger.error(f"Popup not present or popup didn't close."
                                 f" See Error: {err}\n", exc_info=True)

                driver.find_element("tag name", "body").send_keys(Keys.CONTROL, "r")
                driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

                prev_game_pregame_form_api_url = f"/api/v1/event/{record['id']}/pregame-form"

                log_entries = driver.get_log('performance')

                for log in logs:
                    api_path = log['params'].get('headers',{}).get(':path','')
                    if prev_game_pregame_form_api_url == api_path:
                        logger.debug(f"📍✅   Match {prev_game_pregame_form_api_url}:----> {api_path}\n")
                        break
                    else:
                        logger.debug(f"❌ No match with API:{prev_game_pregame_form_api_url}.\t{api_path}")

                try:
                    prev_matchup_event_json = json.loads(driver.execute_cdp_cmd('Network.getResponseBody',{'requestId': log['params']['requestId']})['body'])
                    individual_prev_home_team_record["Team Ranking"] = prev_matchup_event_json["awayTeam"]["position"]
                    individual_prev_home_team_record['Opponent Rank'] = prev_matchup_event_json["homeTeam"]["position"]
                except Exception as e:
                    logger.error(f"😫 Failed to get JSON from API"
                                 " {prev_game_pregame_form_api_url}. "
                                 "See error: {e}\n", exc_info=True)


        prev_records_home_team_total.append(individual_prev_home_team_record)
        logger.debug(f"\nPrevious Records [HT]:"
                      " {prev_records_home_team_total}\n")


    counter+=1

    # Get the Standings in the JSON output
    # Store the standings in the same array of dictionaries above taking into account which match they belong to.


driver.quit()

# Force writing logs to the file
