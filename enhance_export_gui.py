import multiprocessing

from enhance_goodreads_export.gui import launch_gui

if __name__ == "__main__":
    # Workaround for multiprocessing when using pyinstaller
    # see https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
    multiprocessing.freeze_support()

    launch_gui()
