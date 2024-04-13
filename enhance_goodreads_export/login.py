from typing import Callable

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from .config import POST_LOGIN_URL


def default_login_prompt():
    input(
        "Please log in to goodreads in the browser window that just opened and press"
        " enter"
    )


def login(login_prompt: Callable | None) -> requests.Session:
    if login_prompt is None:
        login_prompt = default_login_prompt

    print("Setting up webdriver for interactive login")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    print("Getting sign-in page and waiting for login")
    driver.get("https://www.goodreads.com/user/sign_in")

    login_prompt()

    if driver.current_url != POST_LOGIN_URL:
        raise AssertionError(
            f"Expected to be at {POST_LOGIN_URL} after login, actually at"
            f" {driver.current_url}, aborting!"
        )

    print("Getting cookies and setting up session")
    cookies = driver.get_cookies()
    user_agent = driver.execute_script("return navigator.userAgent;")
    driver.close()

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    session.headers.update({"user-agent": user_agent})

    return session
