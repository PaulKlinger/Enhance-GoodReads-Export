import requests
from bs4 import BeautifulSoup
import urllib.parse
import backoff
import csv
import datetime
import dateutil.parser
import argparse
from typing import List, NewType, Union, Tuple

AbsoluteUrl = NewType("AbsoluteUrl", str)
RelativeUrl = NewType("RelativeUrl", str)
IsoDateStr = NewType("IsoDateStr", str)
Path = NewType("Path", str)

BOOK_URL = AbsoluteUrl("https://www.goodreads.com/book/show/")
SIGNIN_URL = AbsoluteUrl("https://www.goodreads.com/user/sign_in")


parser = argparse.ArgumentParser(description=
                                 """Adds genre and (re)reading dates information to a goodreads export file.""")
parser.add_argument("--csv", required=True)
parser.add_argument("--email", required=True)
parser.add_argument("--password", required=True)

options = parser.parse_args()

STANDARD_FIELDNAMES = ["Book Id", "Title", "Author", "Author l-f", "Additional Authors", "ISBN", "ISBN13", "My Rating",
                       "Average Rating", "Publisher", "Binding", "Number of Pages", "Year Published",
                       "Original Publication Year", "Date Read", "Date Added", "Bookshelves",
                       "Bookshelves with positions", "Exclusive Shelf", "My Review", "Spoiler", "Private Notes",
                       "Read Count", "Recommended For", "Recommended By", "Owned Copies", "Original Purchase Date",
                       "Original Purchase Location", "Condition", "Condition Description", "BCID"]


def sign_in(email: str, password: str) -> requests.Session:
    session = requests.Session()
    print("Getting login page")
    response = session.get(SIGNIN_URL)
    soup = BeautifulSoup(response.content, "html.parser")
    auth_token = soup.find(attrs={"name": "authenticity_token"})["value"]
    n_token = soup.find(attrs={"name": "n"})["value"]

    form_data = {"authenticity_token": auth_token, "user[email]": email, "user[password]": password,
                 "next": "Sign in", "n": n_token, "remember_me": "on", "utf8": "✓"}
    print("Logging in")
    login_response = session.post(SIGNIN_URL, data=form_data)
    login_response.raise_for_status()
    return session


def parse_csv(filename: Path):
    with open(filename, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if set(reader.fieldnames) < set(STANDARD_FIELDNAMES):
            raise ValueError("CSV file does not contain the standard fieldnames!")
        return list(reader)


def write_csv(data: List[dict], fieldnames: List[str], filename: Path):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,
                                delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(data)


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=10)
def get_with_retry(session, *args, **kwargs) -> requests.Response:
    resp = session.get(*args, timeout=10, **kwargs)
    resp.raise_for_status()
    return resp


def make_book_url(book_id: str) -> AbsoluteUrl:
    return AbsoluteUrl(urllib.parse.urljoin(BOOK_URL, book_id))


def get_read_dates(soup: BeautifulSoup) -> List[Tuple[datetime.datetime, datetime.datetime]]:
    allReadingSessions = soup.find(id="allReadingSessions")
    if allReadingSessions is None:
        return []
    timeline = allReadingSessions.find(class_="readingTimeline")

    status_updates = []
    for entry in timeline.findAll(class_="readingTimeline__text"):
        lines = entry.get_text().split("\n")
        state = None
        date = None
        for line in lines:
            if "Finished Reading" in line:
                state = "end"
            elif "Started Reading" in line:
                state = "start"
            else:
                try:
                    date = dateutil.parser.parse(line)
                except ValueError:
                    continue
        if (state is not None) and (date is not None):
            status_updates.append((date, state))

    status_updates.reverse()
    date_started = None
    readings = []
    for date, state in status_updates:
        if state == "end":
            readings.append((date_started, date))
            date_started = None
        elif state == "start":
            date_started = date
    return readings


def get_genres(soup):
    genrelinks = soup.find_all(class_="bookPageGenreLink")
    genres = []
    genre = []
    for text in (l.get_text() for l in genrelinks):
        if "users" in text:
            genres.append((genre, int("".join(c for c in text if c.isdigit()))))
            genre = []
        else:
            genre.append(text)

    return genres


def main():
    options = parser.parse_args()
    books = parse_csv(options.csv)
    session = sign_in(options.email, options.password)

    books_to_process = [b for b in books if not b.get("genres", None)]
    for i, book in enumerate(books_to_process):
        print(f"Book {i+1} of {len(books_to_process)}: {book['Title']} ({book['Author']})")
        page = get_with_retry(session, make_book_url(book["Book Id"]))
        soup = BeautifulSoup(page.content, 'html.parser')
        read_dates = get_read_dates(soup)
        genres = get_genres(soup)

        book["read_dates"] = ";".join(",".join(d.strftime("%Y-%m-%d") if d else "" for d in reading)
                                      for reading in read_dates)
        book["genres"] = ";".join(f"{','.join(genre[0])}|{genre[1]}" for genre in genres)
        #print(f"read dates: {read_dates}")
        #print(f"genres: {genres}")

        if i % 20 == 0 or i == len(books_to_process) - 1:
            print("saving csv")
            write_csv(books, STANDARD_FIELDNAMES + ["read_dates", "genres"], "export_enhanced.csv")

main()
