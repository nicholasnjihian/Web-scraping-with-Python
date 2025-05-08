#!/usr/bin/env python3

import json
import os
import time

import asyncio
import threading

import logging

import glob


from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster


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


# profile_path = "/home/nicknjihia/.mozilla/firefox/tu9fim1g.default-release"
# firefox_profile = FirefoxProfile(profile_path)


tournament_games = []


countries = ["England","Spain","Italy","Germany","France",
             "Netherlands","Türkiye","Portugal","Belgium","Scotland"]


club_leagues = ["Premier League","LaLiga","Serie A","Bundesliga","Ligue 1",
                "Eredivisie","Super Lig","LaLiga 2","Championship","2.Bundesliga",
                "Serie B","Ligue 2","Liga Portugal Betclic","First Division A","Premiership"]



# Class to handle mitmproxy events
class ApiCapture:
    def __init__(self, target_url=None):
        """Initialize with an optional target URL filter"""
        self.target_url = target_url
        self.captured_responses = []

    def response(self, flow: http.HTTPFlow) -> None:
        """Process responses and capture JSON data"""
        # Check if this is a response we want to capture
        if self.target_url and self.target_url not in flow.request.url:
            return

        # Check for JSON content
        if flow.response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Decode the response content
                json_data = json.loads(flow.response.content.decode('utf-8'))

                # Store the captured data
                self.captured_responses.append({
                    "url": flow.request.url,
                    "method": flow.request.method,
                    "status_code": flow.response.status_code,
                    "data": json_data
                })

                logger.debug(f"📍✅  Captured JSON from {flow.request.url}")
            except json.JSONDecodeError:
                logger.error(f"❌ Failed to decode JSON from {flow.request.url}")
            except Exception as e:
                logger.error(f"❌ Error processing response:\n{e}", exc_info=True)


async def start_mitmproxy(host, port, api_capture):
    """Start mitmproxy with our custom handler"""
    options = Options(listen_host=host, listen_port=port)
    master = DumpMaster(options)
    master.addons.add(api_capture)

    try:
        await master.run()
    except KeyboardInterrupt:
        master.shutdown()


def configure_firefox_for_proxy(proxy_host, proxy_port, use_default_profile=False):
    """Configure Firefox to use mitmproxy"""
    # Set up Firefox options with proxy settings
    firefox_options = FirefoxOptions()

    # Set up the proxy
    firefox_options.set_preference("network.proxy.type", 1)  # Manual proxy configuration
    firefox_options.set_preference("network.proxy.http", proxy_host)
    firefox_options.set_preference("network.proxy.http_port", proxy_port)
    firefox_options.set_preference("network.proxy.ssl", proxy_host)
    firefox_options.set_preference("network.proxy.ssl_port", proxy_port)
    firefox_options.set_preference("network.proxy.no_proxies_on", "")

    # Accept untrusted certificates (for mitmproxy's SSL interception)
    firefox_options.set_preference("security.cert_pinning.enforcement_level", 0)
    firefox_options.set_preference("security.enterprise_roots.enabled", True)
    firefox_options.accept_insecure_certs = True

    # Create and return the WebDriver
    service = FirefoxService(GeckoDriverManager().install())
    if use_default_profile:
        # Use the default Firefox profile
        from pathlib import Path


        # Determine the Firefox profile directory based on OS
        if os.name == 'nt':  # Windows
            profile_path = os.path.join(os.getenv('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
        elif os.name == 'posix':  # macOS/Linux
            if os.path.exists(os.path.expanduser('~/Library/Application Support/Firefox')):  # macOS
                profile_path = os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
            else:  # Linux
                profile_path = os.path.expanduser('~/.mozilla/firefox')
        else:
            raise OSError("Unsupported operating system")

        # Find default profile (usually ends with .default or .default-release)
        profiles_dir = Path(profile_path)
        default_profile = None


        if profiles_dir.exists():
            for profile in profiles_dir.iterdir():
                if profile.is_dir() and (profile.name.endswith('.default') or
                                        profile.name.endswith('.default-release')):
                    default_profile = profile
                    break

        if default_profile:
            print(f"Using default Firefox profile: {default_profile}")
            firefox_options.set_preference('profile', str(default_profile))
            # Use Firefox profile
            driver = webdriver.Firefox(
                service=service,
                options=firefox_options,
                firefox_profile=webdriver.FirefoxProfile(str(default_profile))
            )
        else:
            print("Default profile not found, using temporary profile")
            driver = webdriver.Firefox(service=service, options=firefox_options)
    else:
        # Create a new temporary profile
        driver = webdriver.Firefox(service=service, options=firefox_options)


    return driver


def run_mitmproxy(host, port, api_capture):
    """Run mitmproxy in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_mitmproxy(host, port, api_capture))


def main():
    # Configuration
    PROXY_HOST = '127.0.0.1'
    PROXY_PORT = 8080
    DATE_TODAY = "2025-04-21"


    logger.info("Started!😄🙌😃 ")
    TARGET_WEBSITE = f"https://www.sofascore.com/football/{DATE_TODAY}"
    logger.info(f"▶️   Visiting: {TARGET_WEBSITE}")

    SCHEDULED_DATE_API_URL = "/api/v1/sport/football/scheduled-events/" + DATE_TODAY



    # Create our API capture addon
    api_capture = ApiCapture(target_url=SCHEDULED_DATE_API_URL)


    # Start mitmproxy in a separate thread
    proxy_thread = threading.Thread(
        target=run_mitmproxy,
        args=(PROXY_HOST, PROXY_PORT, api_capture),
        daemon=True
    )
    proxy_thread.start()


    logger.debug(f"Starting mitmproxy on {PROXY_HOST}:{PROXY_PORT}")


    try:
        # Give mitmproxy a moment to start
        time.sleep(2)


        # Set up Firefox with our proxy
        driver = configure_firefox_for_proxy(PROXY_HOST, PROXY_PORT)


        # Navigate to the target site
        logger.debug(f"Navigating to {TARGET_WEBSITE}")

        driver.get(TARGET_WEBSITE)


        # Allow some time for page interactions and API calls to complete
        # You can add more specific interactions here
        time.sleep(5)


        # Output captured API responses
        logger.debug("\nCaptured API Responses:")
        for i, response in enumerate(api_capture.captured_responses):
            logger.debug(f"\n--- Response {i+1} ---")
            logger.debug(f"URL: {response['url']}")
            logger.debug(f"Method: {response['method']}")
            logger.debug(f"Status: {response['status_code']}")
            logger.debug("Data:", json.dumps(response['data'], indent=2)[:200] + "..."
                  if len(json.dumps(response['data'], indent=2)) > 200 else json.dumps(response['data'], indent=2))


        # Save to file (optional)
        if api_capture.captured_responses:
            with open('captured_api_data.json', 'w') as f:
                json.dump(api_capture.captured_responses, f, indent=2)
            logger.debug(f"\nSaved {len(api_capture.captured_responses)} responses to captured_api_data.json")


    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()
        logger.debug("\nTest completed")


if __name__ == "__main__":
    main()

