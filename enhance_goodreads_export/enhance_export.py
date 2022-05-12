import csv
import datetime
import urllib.parse

import backoff
import dateutil.parser
import requests
from bs4 import BeautifulSoup
from bs4 import Tag

from .config import BASE_URL
from .config import BOOK_URL
from .config import STANDARD_FIELDNAMES
from .entities import AbsoluteUrl
from .entities import CaptchaSolver
from .entities import EnhanceExportException
from .entities import Path
from .login import login


def parse_csv(filename: Path):
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValueError("Could not read csv column names")
            if set(reader.fieldnames) < set(STANDARD_FIELDNAMES):
                raise ValueError("CSV file does not contain the standard fieldnames!")
            return list(reader)
    except (ValueError, csv.Error, OSError) as e:
        raise EnhanceExportException(f"Error reading export file: {e}")


def write_csv(data: list[dict], fieldnames: list[str], filename: Path):
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            writer.writerows(data)
    except (OSError, csv.Error) as e:
        raise EnhanceExportException(f"Error writing export file: {e}")


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=10)
def get_with_retry(session, *args, **kwargs) -> requests.Response:
    resp = session.get(*args, timeout=10, **kwargs)
    resp.raise_for_status()
    return resp


def make_book_url(book_id: str) -> AbsoluteUrl:
    return AbsoluteUrl(urllib.parse.urljoin(BOOK_URL, book_id))


def make_review_url(review_link: str) -> AbsoluteUrl:
    return AbsoluteUrl(urllib.parse.urljoin(BASE_URL, review_link))


def get_read_dates(
    soup: BeautifulSoup,
) -> list[tuple[datetime.datetime | None, datetime.datetime]]:
    timeline = soup.find(class_="readingTimeline")
    if not isinstance(timeline, Tag):
        print("Error finding read dates, skipping.")
        return []

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
                    # dateutil.parser replaces undetermined fields with those in the default.
                    # this way dates which just give the year (e.g. "2007") are set to e.g. "2007-01-01".
                    # Without this they would be set to the current day and month in the given year.
                    # This is usefull as dates on the first of january can be automatically distributed over the year
                    # in bookstats.
                    # (Might be useful to handle these differently but afaik goodreads previously automatically set
                    # "2007" to "2007-01-01", so could be tricky.)
                    date = dateutil.parser.parse(
                        line, default=datetime.datetime(1900, 1, 1)
                    )
                except ValueError:
                    continue
        if (state is not None) and (date is not None):
            status_updates.append((date, state))

    date_started: datetime.datetime | None = None
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


def enhance_export(options: dict, captcha_solver: CaptchaSolver | None = None):
    books = parse_csv(options["csv"])
    session = login(
        options["email"], options["password"], captcha_solver=captcha_solver
    )
    if options["update"]:
        old_books_by_id = {b["Book Id"]: b for b in parse_csv(options["update"])}
        for b in books:
            # Update read_dates and genres from the old file for books that didn't change shelf and weren't re-read.
            ob = old_books_by_id.get(b["Book Id"], None)
            if (
                ob
                and ob["Exclusive Shelf"] == b["Exclusive Shelf"]
                and ob["Date Read"] == b["Date Read"]
            ):
                b["read_dates"] = old_books_by_id[b["Book Id"]]["read_dates"]
                b["genres"] = old_books_by_id[b["Book Id"]]["genres"]

    books_to_process = [
        b
        for b in books
        if (
            options["force"]
            or (not b.get("genres", None) and not b.get("read_dates", None))
        )
    ]
    for i, book in enumerate(books_to_process):
        print(
            f"Book {i+1} of {len(books_to_process)}: {book['Title']} ({book['Author']})"
        )
        page = get_with_retry(session, make_book_url(book["Book Id"]))
        soup = BeautifulSoup(page.content, "html.parser")
        genres = get_genres(soup)
        book["genres"] = ";".join(
            f"{','.join(genre[0])}|{genre[1]}" for genre in genres
        )
        book["read_dates"] = ""
        review_link_tag = soup.find("a", string="My Activity")

        if not isinstance(review_link_tag, Tag):
            print(
                "Couldn't find review link, this sometimes means login didn't work, try running again"
            )
            print("If this continues the page layout might have changed :(")
            return

        review_link = review_link_tag["href"]

        if review_link and isinstance(review_link, str):
            review_page = get_with_retry(session, make_review_url(review_link))
            review_soup = BeautifulSoup(review_page.content, "html.parser")
            read_dates = get_read_dates(review_soup)
            book["read_dates"] = ";".join(
                ",".join(d.strftime("%Y-%m-%d") if d else "" for d in reading)
                for reading in read_dates
            )
        else:
            print(f"Error: Can't find link to review.")

        if i % 20 == 19 or i == len(books_to_process) - 1:
            print("saving csv")
            write_csv(
                books, STANDARD_FIELDNAMES + ["read_dates", "genres"], options["csv"]
            )
    print("Finished processing!")
