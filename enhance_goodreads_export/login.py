from collections.abc import Callable
from typing import Optional

import requests
from bs4 import BeautifulSoup
from bs4 import Tag

from .config import SIGNIN_POST_URL
from .config import SIGNIN_URL
from .config import USER_AGENT
from .entities import EnhanceExportException
from .metadata1 import encrypt_metadata
from .metadata1 import meta_goodreads_desktop


# Many thanks to mkb79 for his Audible library,
# the login code there was a great help
# https://github.com/mkb79/Audible/blob/master/src/audible/login.py


def human_cli_captcha_solver(captcha_data: bytes) -> str:
    with open("captcha.png", "wb") as f:
        f.write(captcha_data)
    print("Captcha saved to current directory ('captcha.jpg').")
    return input("Please enter the characters in the captcha:").strip().lower()


def get_next_action_from_soup(
    soup: BeautifulSoup, search_field: Optional[dict[str, str]] = None
) -> tuple[str, str]:
    search_field = search_field or {"name": "signIn"}
    form = soup.find("form", search_field) or soup.find("form")
    assert isinstance(form, Tag)
    method = form.get("method", "GET")
    url = form["action"]
    assert isinstance(url, str)
    assert isinstance(method, str)
    return method, url


def get_inputs_from_soup(
    soup: BeautifulSoup, search_field: Optional[dict[str, str]] = None
) -> dict[str, str]:
    """Extracts hidden form input fields from a Amazon login page."""

    search_field = search_field or {"name": "signIn"}
    form = soup.find("form", search_field) or soup.find("form")
    assert isinstance(form, Tag)
    inputs = {}
    for field in form.find_all("input"):
        try:
            inputs[field["name"]] = ""
            if field["type"] and field["type"] == "hidden":
                inputs[field["name"]] = field["value"]
        except BaseException:
            pass
    return inputs


def login(
    email: str, password: str, captcha_solver: Optional[Callable[[bytes], str]] = None
) -> requests.Session:
    if captcha_solver is None:
        captcha_solver = human_cli_captcha_solver
    try:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US",
                "Accept-Encoding": "gzip",
            }
        )
        print("Getting login page")
        response = session.get(SIGNIN_URL)
        soup = BeautifulSoup(response.content, "html.parser")
        email_signin_link = soup.find(href=lambda u: u and SIGNIN_POST_URL in u)
        assert isinstance(email_signin_link, Tag), "did not find email signin link!"
        email_signin_url = email_signin_link["href"]
        assert isinstance(email_signin_url, str)

        print(f"Getting email login page {email_signin_url}")
        response = session.get(email_signin_url)
        while True:
            soup = BeautifulSoup(response.content, "html.parser")
            if auth_error_tag := soup.find(id="auth-error-message-box"):
                print(auth_error_tag)

            magic_values = get_inputs_from_soup(soup)

            if capt_img := soup.find("img", alt=lambda x: x and "CAPTCHA" in x):
                assert isinstance(capt_img, Tag) and isinstance(
                    capt_img["src"], str
                ), "Failed to find captcha url"
                captcha_data = requests.get(capt_img["src"]).content
                captcha_guess = captcha_solver(captcha_data)
                magic_values["guess"] = captcha_guess
                magic_values["use_image_captcha"] = "true"
                magic_values["use_audio_captcha"] = "false"
                magic_values["showPasswordChecked"] = "false"

            form_data = {
                **magic_values,
                "email": email,
                "password": password,
                "create": "0",
                "encryptedPasswordExpected": "",
                "metadata1": encrypt_metadata(
                    meta_goodreads_desktop(USER_AGENT, email_signin_url)
                ),
            }
            print("Logging in")
            print(form_data)

            method, url = get_next_action_from_soup(soup)

            response = session.request(method=method, url=url, data=form_data)
            response.raise_for_status()

            if not response.url.startswith(SIGNIN_POST_URL):
                break

    except requests.RequestException as e:
        raise EnhanceExportException(f"Error logging in: {e}")

    except (KeyError, AssertionError) as e:
        raise EnhanceExportException(
            f"error parsing login page, maybe layout changed? {e}"
        )

    return session
