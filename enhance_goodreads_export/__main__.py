import argparse

from .enhance_goodreads_export import enhance_export
from .enhance_goodreads_export import EnhanceExportException


def main():
    argument_parser = argparse.ArgumentParser(
        description="""Adds genre and (re)reading dates information to a GoodReads export file."""
    )
    argument_parser.add_argument(
        "-c",
        "--csv",
        help="path of your GoodReads export file (the new columns will be "
        "added to this file)",
    )
    argument_parser.add_argument(
        "-u",
        "--update",
        help="(optional) path of previously enhanced GoodReads export file "
        "to update (output will still be written to the file "
        "specified in --csv)",
    )
    argument_parser.add_argument(
        "-e", "--email", help="the email you use to login to GoodReads"
    )
    argument_parser.add_argument("-p", "--password", help="your GoodReads Password")

    argument_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="process all books (by default only those without genre information are processed)",
    )

    argument_parser.add_argument("-g", "--gui", action="store_true", help="show GUI")

    options = vars(argument_parser.parse_args())

    if options["gui"]:
        from .enhance_goodreads_export_gui import launch_gui

        launch_gui()
        return

    if not all((options["email"], options["password"], options["csv"])):
        print(
            "You need to provide the path to the export file, an email address and a password!"
        )
        print()
        argument_parser.print_help()
        return

    try:
        enhance_export(options)
    except EnhanceExportException as e:
        print(e.message)


if __name__ == "__main__":
    main()
