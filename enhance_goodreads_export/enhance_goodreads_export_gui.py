import multiprocessing
import queue
import sys
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename

from .enhance_goodreads_export import enhance_export
from .entities import EnhanceExportException


class IOQueue(object):
    def __init__(self, queue: queue.Queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


def human_tk_captcha_solver(captcha_data: bytes) -> str:
    with open("captcha.jpg", "wb") as f:
        f.write(captcha_data)
    return input("Please enter the characters in the captcha:").strip().lower()


def task(options: dict, stdout_queue: queue.Queue):
    sys.stdout = IOQueue(stdout_queue)  # type: ignore
    try:
        enhance_export(options)
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

        self.emaillabel = ttk.Label(self.frame, text="email:")
        self.emailentry = ttk.Entry(self.frame)
        self.emaillabel.grid(row=2, column=0)
        self.emailentry.grid(row=2, column=1)
        self.passwordlabel = ttk.Label(self.frame, text="password")
        self.passwordentry = ttk.Entry(self.frame)
        self.passwordlabel.grid(row=3, column=0)
        self.passwordentry.grid(row=3, column=1)
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

        self.start_button = ttk.Button(
            self.frame, text="start processing", command=self.start_processing
        )
        self.start_button.grid(row=5, column=0, columnspan=2, pady=5)

        self.frame.grid_columnconfigure(0, weight=0)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=0)
        self.frame.grid_columnconfigure(3, weight=1)

        self.stdout_queue = multiprocessing.Queue()
        self.stdout_queue.cancel_join_thread()
        info = IOText(self.stdout_queue, self.frame)
        info.grid(row=10, column=0, columnspan=10, sticky=tk.N + tk.S + tk.E + tk.W)

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
            "email": self.emailentry.get(),
            "password": self.passwordentry.get(),
        }

        process = multiprocessing.Process(
            target=task, args=(options, self.stdout_queue), daemon=True
        )
        process.start()

        def check_if_finished():
            if process.is_alive():
                self.after(300, check_if_finished)
            else:
                self.change_all_state(tk.NORMAL)

        self.change_all_state(tk.DISABLED)
        check_if_finished()

    def change_all_state(self, new_state) -> None:
        self.filebutton["state"] = new_state
        self.update_filebutton["state"] = new_state
        self.emailentry["state"] = new_state
        self.passwordentry["state"] = new_state
        self.forceentry["state"] = new_state
        if new_state == tk.NORMAL:
            self.forceentry.state(["!alternate", "!selected"])
        self.start_button["state"] = new_state


def launch_gui() -> None:
    gui = EnhanceExportGui()
    gui.mainloop()


if __name__ == "__main__":
    # Workaround for multiprocessing when using pyinstaller
    # see https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
    multiprocessing.freeze_support()

    launch_gui()
