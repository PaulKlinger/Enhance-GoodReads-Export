import requests
from bs4 import BeautifulSoup
import urllib.parse
import backoff
import csv
import datetime
import dateutil.parser
import argparse

from typing import List, NewType, Tuple

AbsoluteUrl = NewType("AbsoluteUrl", str)
RelativeUrl = NewType("RelativeUrl", str)
IsoDateStr = NewType("IsoDateStr", str)
Path = NewType("Path", str)

BOOK_URL = AbsoluteUrl("https://www.goodreads.com/book/show/")
BASE_URL = AbsoluteUrl("https://www.goodreads.com")
SIGNIN_URL = AbsoluteUrl("https://www.goodreads.com/user/sign_in")

STANDARD_FIELDNAMES = ["Book Id", "Title", "Author", "Author l-f", "Additional Authors", "ISBN", "ISBN13", "My Rating",
                       "Average Rating", "Publisher", "Binding", "Number of Pages", "Year Published",
                       "Original Publication Year", "Date Read", "Date Added", "Bookshelves",
                       "Bookshelves with positions", "Exclusive Shelf", "My Review", "Spoiler", "Private Notes",
                       "Read Count", "Recommended For", "Recommended By", "Owned Copies", "Original Purchase Date",
                       "Original Purchase Location", "Condition", "Condition Description", "BCID"]


class EnhanceExportException(Exception):
    def __init__(self, message):
        self.message = message


def sign_in(email: str, password: str) -> requests.Session:
    try:
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
        if login_response.url == SIGNIN_URL:
            raise EnhanceExportException("Error logging in, check email / password.")

    except requests.RequestException as e:
        raise EnhanceExportException(f"Error logging in: {e}")

    except KeyError:
        raise EnhanceExportException(f"error parsing login page, maybe layout changed?")

    return session


def parse_csv(filename: Path):
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if set(reader.fieldnames) < set(STANDARD_FIELDNAMES):
                raise ValueError("CSV file does not contain the standard fieldnames!")
            return list(reader)
    except (ValueError, csv.Error, IOError) as e:
        raise EnhanceExportException(f"Error reading export file: {e}")


def write_csv(data: List[dict], fieldnames: List[str], filename: Path):
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(data)
    except (IOError, csv.Error):
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


def get_read_dates(soup: BeautifulSoup) -> List[Tuple[datetime.datetime, datetime.datetime]]:
    timeline = soup.find(class_="readingTimeline")
    if timeline is None:
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
                    date = dateutil.parser.parse(line, default=datetime.datetime(1900, 1, 1))
                except ValueError:
                    continue
        if (state is not None) and (date is not None):
            status_updates.append((date, state))

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


def enhance_export(options: dict):
    books = parse_csv(options["csv"])
    session = sign_in(options["email"], options["password"])
    if options["update"]:
        old_books_by_id = {b["Book Id"]: b for b in parse_csv(options["update"])}
        for b in books:
            # Update read_dates and genres from the old file for books that didn't change shelf and weren't re-read.
            ob = old_books_by_id.get(b["Book Id"], None)
            if ob and ob["Exclusive Shelf"] == b["Exclusive Shelf"] and ob["Date Read"] == b["Date Read"]:
                b["read_dates"] = old_books_by_id[b["Book Id"]]["read_dates"]
                b["genres"] = old_books_by_id[b["Book Id"]]["genres"]

    books_to_process = [b for b in books if (options["force"] or (not b.get("genres", None)
                                                                  and not b.get("read_dates", None)))]
    for i, book in enumerate(books_to_process):
        print(f"Book {i+1} of {len(books_to_process)}: {book['Title']} ({book['Author']})")
        page = get_with_retry(session, make_book_url(book["Book Id"]))
        soup = BeautifulSoup(page.content, 'html.parser')
        genres = get_genres(soup)
        book["genres"] = ";".join(f"{','.join(genre[0])}|{genre[1]}" for genre in genres)
        book["read_dates"] = ""
        review_link = soup.find("a", string="My Activity")["href"]
        if review_link:
            review_page = get_with_retry(session, make_review_url(review_link))
            review_soup = BeautifulSoup(review_page.content, 'html.parser')
            read_dates = get_read_dates(review_soup)
            book["read_dates"] = ";".join(",".join(d.strftime("%Y-%m-%d") if d else "" for d in reading)
                                          for reading in read_dates)
        else:
            print(f"Error: Can't find link to review.")

        if i % 20 == 0 or i == len(books_to_process) - 1:
            print("saving csv")
            write_csv(books, STANDARD_FIELDNAMES + ["read_dates", "genres"], options["csv"])


def main():
    argument_parser = argparse.ArgumentParser(
        description="""Adds genre and (re)reading dates information to a GoodReads export file.""")
    argument_parser.add_argument("-c", "--csv", help="path of your GoodReads export file (the new columns will be "
                                                     "added to this file)")
    argument_parser.add_argument("-u", "--update", help="(optional) path of previously enhanced GoodReads export file "
                                                        "to update (output will still be written to the file "
                                                        "specified in --csv)")
    argument_parser.add_argument("-e", "--email", help="the email you use to login to GoodReads")
    argument_parser.add_argument("-p", "--password", help="your GoodReads Password")

    argument_parser.add_argument(
        "-f", "--force", action="store_true",
        help="process all books (by default only those without genre information are processed)")

    argument_parser.add_argument("-g", "--gui", action="store_true", help="show GUI")

    options = vars(argument_parser.parse_args())

    if options["gui"]:
        from enhance_goodreads_export_gui import launch_gui
        launch_gui()
        return

    if not all((options["email"], options["password"], options["csv"])):
        print("You need to provide the path to the export file, an email address and a password!")
        print()
        argument_parser.print_help()
        return

    try:
        enhance_export(options)
    except EnhanceExportException as e:
        print(e.message)


if __name__ == "__main__":
    main()
