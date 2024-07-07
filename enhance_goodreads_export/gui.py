import functools
import io
import multiprocessing
import queue
import sys
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename

from .enhance_export import enhance_export
from .entities import EnhanceExportException


class IOQueue:
    def __init__(self, queue: queue.Queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


def human_tk_captcha_solver(
    captcha_data_queue: queue.Queue,
    captcha_guess_queue: queue.Queue,
) -> str:
    captcha_data_queue.put(True)
    return captcha_guess_queue.get(block=True)


def task(
    options: dict,
    stdout_queue: queue.Queue,
    captcha_data_queue: queue.Queue,
    captcha_guess_queue: queue.Queue,
):
    sys.stdout = IOQueue(stdout_queue)  # type: ignore

    try:
        enhance_export(
            options,
            login_prompt=functools.partial(
                human_tk_captcha_solver,
                captcha_data_queue=captcha_data_queue,
                captcha_guess_queue=captcha_guess_queue,
            ),
        )
    except EnhanceExportException as e:
        print(e.message)


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
            if self.text.dlineinfo("end-1chars") is not None:  # autoscroll if at end
                scroll = True
            self.text.insert("end", text)
            if scroll:
                self.text.see("end")

        self.after(100, self.update)


class EnhanceExportGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.wm_title("Enhance GoodReads Export Tool")
        self.resizable(False, False)
        self.frame = ttk.Frame(self, padding="3m")
        self.frame.pack(fill=tk.BOTH)
        self.filebutton = ttk.Button(
            self.frame, text="export file", command=self.ask_for_filename
        )
        self.filebutton.grid(row=0, column=0, sticky=tk.W)
        self.pathlabel = ttk.Label(
            self.frame,
            anchor=tk.W,
            text="[Goodreads export file, new columns will be added to this file]",
        )
        self.pathlabel.grid(row=0, column=1, columnspan=10, sticky=tk.W)

        self.update_filebutton = ttk.Button(
            self.frame, text="old file", command=self.ask_for_update_filename
        )
        self.update_filebutton.grid(row=1, column=0)
        self.update_pathlabel = ttk.Label(
            self.frame,
            anchor=tk.W,
            text="[previously enhanced file to copy values from (optional)]",
        )
        self.update_pathlabel.grid(row=1, column=1, columnspan=10, sticky=tk.W)

        self.forcelabel = ttk.Label(self.frame, text="process all")
        self.forceentry = ttk.Checkbutton(self.frame)
        self.forceentry.state(["!alternate", "!selected"])
        forcehelp = ttk.Label(
            self.frame,
            text="(by default only books without genre information are processed)",
        )
        self.forcelabel.grid(row=4, column=0)
        self.forceentry.grid(row=4, column=1)
        forcehelp.grid(row=4, column=2)

        self.ignoreerrorslabel = ttk.Label(self.frame, text="ignore errors")
        self.ignoreerrorsentry = ttk.Checkbutton(self.frame)
        self.ignoreerrorsentry.state(["!alternate", "!selected"])
        self.ignoreerrorslabel.grid(row=5, column=0)
        self.ignoreerrorsentry.grid(row=5, column=1)

        self.genrelabel = ttk.Label(self.frame, text="min genre votes")
        self.genreentry = ttk.Entry(self.frame, width=5)
        self.genreentry.insert(0, "10")
        self.genreentry.state(["!alternate"])
        genrehelp = ttk.Label(
            self.frame,
            text=(
                '(number of votes, or % most voted genre, to add a genre, e.g. "10"'
                ' or "11%")'
            ),
        )
        self.genrelabel.grid(row=6, column=0)
        self.genreentry.grid(row=6, column=1)
        genrehelp.grid(row=6, column=2)

        self.start_button = ttk.Button(
            self.frame, text="start processing", command=self.start_processing
        )
        self.start_button.grid(row=7, column=0, columnspan=2, pady=5)

        self.frame.grid_columnconfigure(0, weight=0)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=0)
        self.frame.grid_columnconfigure(3, weight=1)

        self.stdout_queue = multiprocessing.Queue()
        self.stdout_queue.cancel_join_thread()
        info = IOText(self.stdout_queue, self.frame)
        info.grid(row=10, column=0, columnspan=10, sticky=tk.N + tk.S + tk.E + tk.W)

        self.captcha_data_queue = multiprocessing.Queue()
        self.captcha_guess_queue = multiprocessing.Queue()

    def submit_captcha(self):
        self.captcha_guess_queue.put(True)
        self.wm_attributes("-disabled", False)
        self.toplevel_dialog.destroy()
        self.deiconify()

    def captcha_window(self) -> None:
        self.wm_attributes("-disabled", True)
        self.toplevel_dialog = tk.Toplevel(self)
        self.toplevel_dialog.geometry(f"+{self.winfo_x()}+{self.winfo_y()}")
        self.toplevel_dialog.minsize(300, 50)
        self.toplevel_dialog.transient(self)
        self.toplevel_dialog.protocol("WM_DELETE_WINDOW", self.submit_captcha)

        self.toplevel_submit = ttk.Button(
            self.toplevel_dialog, text="I've logged in", command=self.submit_captcha
        )
        self.toplevel_submit.pack(side="bottom")
        self.toplevel_dialog_label = ttk.Label(
            self.toplevel_dialog,
            text="Please log in to GoodReads \n in the browser window that just opened",
        )
        self.toplevel_dialog_label.pack(side="bottom")

    def ask_for_filename(self) -> None:
        filename = askopenfilename()
        self.pathlabel.config(text=filename)

    def ask_for_update_filename(self) -> None:
        filename = askopenfilename()
        self.update_pathlabel.config(text=filename)

    def start_processing(self) -> None:
        options = {
            "csv": self.pathlabel["text"]
            if not self.pathlabel["text"].startswith("[")
            else "",
            "update": self.update_pathlabel["text"]
            if not self.update_pathlabel["text"].startswith("[")
            else "",
            "force": self.forceentry.instate(["selected"]),
            "ignore_errors": self.ignoreerrorsentry.instate(["selected"]),
            "genre_votes": self.genreentry.get() or None,
        }

        process = multiprocessing.Process(
            target=task,
            args=(
                options,
                self.stdout_queue,
                self.captcha_data_queue,
                self.captcha_guess_queue,
            ),
            daemon=True,
        )
        process.start()

        def check_if_finished_or_captcha():
            if process.is_alive():
                try:
                    self.captcha_data_queue.get_nowait()
                except queue.Empty:
                    pass
                else:
                    self.captcha_window()
                self.after(300, check_if_finished_or_captcha)
            else:
                self.change_all_state(tk.NORMAL)

        self.change_all_state(tk.DISABLED)
        check_if_finished_or_captcha()

    def change_all_state(self, new_state) -> None:
        self.filebutton["state"] = new_state
        self.update_filebutton["state"] = new_state
        self.forceentry["state"] = new_state
        self.ignoreerrorsentry["state"] = new_state
        self.genreentry["state"] = new_state
        if new_state == tk.NORMAL:
            self.forceentry.state(["!alternate", "!selected"])
            self.ignoreerrorsentry.state(["!alternate", "!selected"])
        self.start_button["state"] = new_state


def launch_gui() -> None:
    gui = EnhanceExportGui()
    gui.mainloop()
