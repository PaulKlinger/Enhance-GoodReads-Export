# Enhance GoodReads Export

A small tool to add additional data to a GoodReads library export file (.csv) by parsing the website.

Currently adds reading dates (start and finish, including re-readings) and genres.

When analyzing the export file in [Bookstats](https://almoturg.com/bookstats/) this data is used to show
additional / more accurate graphs (e.g. favorite genres, better pages / day stats,...).

Currently only works with separate GoodReads login (i.e. email and password, not via e.g. facebook).

**[For Windows users there is a standalone executable version with a basic graphical user interface.](https://github.com/PaulKlinger/Enhance-GoodReads-Export/releases/download/v0.3/enhance_goodreads_export_gui.exe)**

All others can use the script ("enhance_goodreads_export.py") directly. This requires python 3.6 and the
dependencies specified in "requirements.txt".

Usage instructions for the command line version (output of "python enhance_goodreads_export.py --help"):

```commandline
usage: enhance_goodreads_export.py [-h] [-c CSV] [-u UPDATE] [-e EMAIL]
                                   [-p PASSWORD] [-f] [-g]

Adds genre and (re)reading dates information to a GoodReads export file.

optional arguments:
  -h, --help            show this help message and exit
  -c CSV, --csv CSV     path of your GoodReads export file (the new columns
                        will be added to this file)
  -u UPDATE, --update UPDATE
                        (optional) path of previously enhanced GoodReads
                        export file to update (output will still be written to
                        the file specified in --csv)
  -e EMAIL, --email EMAIL
                        the email you use to login to GoodReads
  -p PASSWORD, --password PASSWORD
                        your GoodReads Password
  -f, --force           process all books (by default only those without genre
                        information are processed)
  -g, --gui             show GUI
```

The tool adds two additional columns to the .csv file: "read_dates" and "genres"
Their format is as follows:

* read_dates: "START_DATE_1,END_DATE_1;START_DATE_2,END_DATE_2;..." where the dates are in YYYY-MM-DD format
* genres: "GENRE,SUBGENRE,SUBSUBGENRE,(...)|NUM_USERS;GENRE,..." where NUM_USERS is the number of users that have
added the book to that shelf