#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--proxy-server=http://localhost:8080')

driver = webdriver.Chrome(options=chrome_options)
