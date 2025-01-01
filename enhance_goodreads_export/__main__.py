import argparse

from .enhance_export import enhance_export
from .enhance_export import EnhanceExportException


def main():
    argument_parser = argparse.ArgumentParser(
        prog="python -m enhance_goodreads_export",
        description="""Adds genre and (re)reading dates information to a GoodReads export file.""",
    )
    argument_parser.add_argument(
        "-c",
        "--csv",
        help=(
            "path of your GoodReads export file (the new columns will be "
            "added to this file)"
        ),
    )
    argument_parser.add_argument(
        "-u",
        "--update",
        help=(
            "(optional) path of previously enhanced GoodReads export file to update "
            "(output will still be written to the file specified in --csv)"
        ),
    )

    argument_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=(
            "process all books "
            "(by default only those without genre information are processed)"
        ),
    )

    argument_parser.add_argument(
        "-i",
        "--ignore_errors",
        action="store_true",
        help="ignore errors updating individual books and keep processing",
    )

    argument_parser.add_argument(
        "--genre_votes",
        default=argparse.SUPPRESS,
        help=(
            "min number of votes needed to add a genre, either integer or percentage of"
            ' highest voted genre in the book (e.g. "11" or "10%%")'
        ),
    )

    argument_parser.add_argument("-g", "--gui", action="store_true", help="show GUI")

    options = vars(argument_parser.parse_args())

    if options["gui"]:
        from .gui import launch_gui

        launch_gui()
        return

    if not options["csv"]:
        print("You need to provide the path to the export file!")
        print()
        argument_parser.print_help()
        return

    try:
        enhance_export(options)
    except EnhanceExportException as e:
        print(e.message)


if __name__ == "__main__":
    main()
