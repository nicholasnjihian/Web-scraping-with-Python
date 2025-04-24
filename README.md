# Web scraping using Selenium Python scripts/code.

This hobby project attempts to scrape the sofascore webpage using Selenium and
Python. The scripts simply pull games for a specific day that are constrained
to a given list of leagues (EPL, LaLiga, LaLiga2, Bundesliga, Ligue 1 & 2,
etc - see code) and attempt to pull a given number of previous games for each
team in the matchup, i.e. say Malaga and Atletico Madrid are facing off, the script
will pull the last say 10 games of Malaga & last 10 games of Atletico Madrid.

The Selenium automation script utilizes the Google Chrome and Mozilla firefox
web browsers. Sofascore exposes api endpoints such as `/api/v1/event/{match_ID}/pregame-form` which I use to get and parse JSON output and filter for data that I want.

This hobby project is solely for the purpose of learning.


## Initial setup.

To get the project to execute, the following pre-conditions need to be met.

* Create a Python virtual environment (venv) (Assuming Ubuntu 24.04).
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv

python3 -m venv .soccer_venv
source .soccer_venv/bin/activate
```
* Install [Selenium](https://www.selenium.dev/downloads/)
* Install [webdriver_manager](https://pypi.org/project/webdriver-manager/)
* Install [GeckoDriver](https://github.com/mozilla/geckodriver/releases)
* Install [selenium-wire](https://pypi.org/project/selenium-wire/)

### Browsers
In order for Selenium to be able to communicate with any browser, a browser
driver is required. For Google Chrome, that'll be (as of writing this) ChromeDriver and for
Firefox, that'll be GeckoDriver. The browser driver is required to interface
between the WebDriver-enabled clients and the browser (Firefox, Chrome, Safari, Opera, Edge, IE) to execute the automation test scripts written in various programming languages (Python, Java, Ruby, JavaScript, .NET/C#, etc).

Selenium-wire extends Selenium’s Python bindings to give you access to the
underlying requests made by the browser. You get extra APIs for inspecting
requests and responses and making changes to them on the fly. Since
GeckoDriverManager doesn't help with intercepting or capturing network
traffic, reading request/response headers or bodies or monitoring the DevTools
Network tab, Selenium-wire will be used here. Selenium-wire adds network
traffic capture. It can work with both Google Chrome and Firefox too.

