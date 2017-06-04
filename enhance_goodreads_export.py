import requests
from bs4 import BeautifulSoup
import urllib.parse
import backoff
import csv
import datetime
import dateutil.parser
import argparse

import multiprocessing
import queue
import sys

from typing import List, NewType, Tuple

AbsoluteUrl = NewType("AbsoluteUrl", str)
RelativeUrl = NewType("RelativeUrl", str)
IsoDateStr = NewType("IsoDateStr", str)
Path = NewType("Path", str)

BOOK_URL = AbsoluteUrl("https://www.goodreads.com/book/show/")
SIGNIN_URL = AbsoluteUrl("https://www.goodreads.com/user/sign_in")

parser = argparse.ArgumentParser(description=
                                 """Adds genre and (re)reading dates information to a GoodReads export file.""")
parser.add_argument("-c", "--csv", help="path of your GoodReads export file")
parser.add_argument("-e", "--email", help="the email you use to login to GoodReads")
parser.add_argument("-p", "--password", help="your GoodReads Password")

parser.add_argument("-f", "--force", action="store_true",
                    help="process all books (by default only those without genre information are processed)")

parser.add_argument("-g", "--gui", action="store_true", help="show GUI")

STANDARD_FIELDNAMES = ["Book Id", "Title", "Author", "Author l-f", "Additional Authors", "ISBN", "ISBN13", "My Rating",
                       "Average Rating", "Publisher", "Binding", "Number of Pages", "Year Published",
                       "Original Publication Year", "Date Read", "Date Added", "Bookshelves",
                       "Bookshelves with positions", "Exclusive Shelf", "My Review", "Spoiler", "Private Notes",
                       "Read Count", "Recommended For", "Recommended By", "Owned Copies", "Original Purchase Date",
                       "Original Purchase Location", "Condition", "Condition Description", "BCID"]


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

    except requests.RequestException as e:
        print(f"Error logging in: {e}")
        sys.exit()

    except KeyError:
        print(f"error parsing login page, maybe layout changed?")
        sys.exit()

    return session


def parse_csv(filename: Path):
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if set(reader.fieldnames) < set(STANDARD_FIELDNAMES):
                raise ValueError("CSV file does not contain the standard fieldnames!")
            return list(reader)
    except (ValueError, csv.Error, IOError) as e:
        print(f"Error reading export file: {e}")
        sys.exit()


def write_csv(data: List[dict], fieldnames: List[str], filename: Path):
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(data)
    except (IOError, csv.Error):
        print(f"Error writing export file: {e}")


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


def enhance_export(options: dict):
    books = parse_csv(options["csv"])
    session = sign_in(options["email"], options["password"])
    books_to_process = [b for b in books if (options["force"] or not b.get("genres", None))]
    for i, book in enumerate(books_to_process):
        print(f"Book {i+1} of {len(books_to_process)}: {book['Title']} ({book['Author']})")
        page = get_with_retry(session, make_book_url(book["Book Id"]))
        soup = BeautifulSoup(page.content, 'html.parser')
        read_dates = get_read_dates(soup)
        genres = get_genres(soup)

        book["read_dates"] = ";".join(",".join(d.strftime("%Y-%m-%d") if d else "" for d in reading)
                                      for reading in read_dates)
        book["genres"] = ";".join(f"{','.join(genre[0])}|{genre[1]}" for genre in genres)

        if i % 20 == 0 or i == len(books_to_process) - 1:
            print("saving csv")
            write_csv(books, STANDARD_FIELDNAMES + ["read_dates", "genres"], "export_enhanced.csv")


class IOQueue(object):  # only used for gui, needs to be defined outside of launch_gui for multiprocessing
    def __init__(self, queue: queue.Queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


def task(options: dict, stdout_queue: queue.Queue):
    sys.stdout = IOQueue(stdout_queue)
    enhance_export(options)


def launch_gui():
    import tkinter as tk
    from tkinter import ttk
    from tkinter.filedialog import askopenfilename

    class IOText(ttk.Frame):
        def __init__(self, text_queue: multiprocessing.Queue, *args, **kwargs):
            ttk.Frame.__init__(self, *args, **kwargs)

            self.text = tk.Text(self, height=6, width=100)
            self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
            self.text.configure(yscrollcommand=self.vsb.set)
            self.vsb.pack(side="right", fill="y")
            self.text.pack(side="left", fill="both", expand=True)
            self.queue = text_queue
            self.update()

        def update(self):
            try:
                text = self.queue.get_nowait()
            except queue.Empty:
                text = None

            if text:
                scroll = False
                if self.text.dlineinfo('end-1chars') is not None:  # autoscroll if at end
                    scroll = True
                self.text.insert("end", text)
                if scroll:
                    self.text.see("end")

            self.after(100, self.update)

    def ask_for_filename():
        filename = askopenfilename()
        pathlabel.config(text=filename)

    def start_processing():
        options = {
            "csv": pathlabel["text"],
            "force": forceentry.instate(["selected"]),
            "email": emailentry.get(),
            "password": passwordentry.get()
        }

        process = multiprocessing.Process(target=task, args=(options, stdout_queue), daemon=True)
        process.start()

        def check_if_finished():
            if process.is_alive():
                root.after(300, check_if_finished)
            else:
                change_all_state(tk.NORMAL)

        change_all_state(tk.DISABLED)
        check_if_finished()

    def change_all_state(new_state):
        filebutton["state"] = new_state
        emailentry["state"] = new_state
        passwordentry["state"] = new_state
        forceentry["state"] = new_state
        if new_state == tk.NORMAL:
            forceentry.state(["!alternate", "!selected"])
        start_button["state"] = new_state

    root = tk.Tk()
    root.wm_title("Enhance GoodReads Export Tool")
    frame = ttk.Frame(root, padding="3m")
    frame.pack(fill=tk.BOTH)
    filebutton = ttk.Button(frame, text="export file", command=ask_for_filename)
    filebutton.grid(row=0, column=0)
    pathlabel = ttk.Label(frame, anchor=tk.W)
    pathlabel.grid(row=0, column=1, columnspan=10, sticky=tk.W)

    emaillabel = ttk.Label(frame, text="email:")
    emailentry = ttk.Entry(frame)
    emaillabel.grid(row=1, column=0)
    emailentry.grid(row=1, column=1)
    passwordlabel = ttk.Label(frame, text="password")
    passwordentry = ttk.Entry(frame)
    passwordlabel.grid(row=2, column=0)
    passwordentry.grid(row=2, column=1)
    forcelabel = ttk.Label(frame, text="process all")
    forceentry = ttk.Checkbutton(frame)
    forceentry.state(["!alternate", "!selected"])
    forcehelp = ttk.Label(frame, text="(by default only books without genre information are processed)")
    forcelabel.grid(row=3, column=0)
    forceentry.grid(row=3, column=1)
    forcehelp.grid(row=3, column=2)

    start_button = ttk.Button(frame, text="start processing", command=start_processing)
    start_button.grid(row=4, column=0, columnspan=2, pady=5)

    frame.grid_columnconfigure(0, weight=0)
    frame.grid_columnconfigure(1, weight=0)
    frame.grid_columnconfigure(2, weight=0)
    frame.grid_columnconfigure(3, weight=1)

    stdout_queue = multiprocessing.Queue()
    stdout_queue.cancel_join_thread()
    info = IOText(stdout_queue, frame)
    info.grid(row=10, column=0, columnspan=10, sticky=tk.N + tk.S + tk.E + tk.W)

    root.mainloop()


def main():
    options = vars(parser.parse_args())
    if options["gui"]:
        launch_gui()
        return

    if not all((options["email"], options["password"], options["csv"])):
        print("You need to provide the path to the export file, an email address and a password!")
        parser.print_help()
        return

    enhance_export(options)


if __name__ == "__main__":
    main()
