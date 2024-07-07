# Enhance GoodReads Export

A small tool to add additional data to a GoodReads library export file (.csv) by parsing the website.

Currently adds reading dates (start and finish, including re-readings) and genres.

When analyzing the export file in [Bookstats](https://almoturg.com/bookstats/) this data is used to show
additional / more accurate graphs (e.g. favorite genres, better pages / day stats,...).

To login, the tool will open a browser window on the goodreads login page. Log in with your account details and then
press "I've logged in" (if you're using the GUI version), or press enter in the terminal (if you're on the command line).

**[Windows users can click here to download a standalone executable version with a basic graphical user interface.](https://github.com/PaulKlinger/Enhance-GoodReads-Export/releases/latest/download/enhance_export_gui.exe)**

All others can use the module directly. This requires python 3.12 and the
dependencies specified in "requirements/requirements.txt". I.e., clone the repository, switch into the the repository
root folder, run
```bash
python -m pip install -r requirements/requirements.txt
```
in a python 3.12 venv and then run
```bash
python -m enhance_goodreads_export -c my_export_file.csv
```


Usage instructions for the command line version (output of "python -m enhance_goodreads_export --help"):

```commandline
usage: python -m enhance_goodreads_export [-h] [-c CSV] [-u UPDATE] [-f] [-i] [--genre_votes GENRE_VOTES] [-g]

Adds genre and (re)reading dates information to a GoodReads export file.

options:
  -h, --help            show this help message and exit
  -c CSV, --csv CSV     path of your GoodReads export file (the new columns will be added to this file)
  -u UPDATE, --update UPDATE
                        (optional) path of previously enhanced GoodReads export file to update (output will still be written to the file specified in --csv)
  -f, --force           process all books (by default only those without genre information are processed)
  -i, --ignore_errors   ignore errors updating individual books and keep processing
  --genre_votes GENRE_VOTES
                        min number of votes needed to add a genre, either integer or percentage of highest voted genre in the book (e.g. "11" or "10%")
  -g, --gui             show GUI
```

The tool adds two additional columns to the .csv file: "read_dates" and "genres"
Their format is as follows:

* read_dates: "START_DATE_1,END_DATE_1;START_DATE_2,END_DATE_2;..." where the dates are in YYYY-MM-DD format. Readings are sorted in ascending order of the end date.
* genres: "GENRE,SUBGENRE,SUBSUBGENRE,(...)|NUM_USERS;GENRE,..." where NUM_USERS is the number of users that have
added the book to that shelf
