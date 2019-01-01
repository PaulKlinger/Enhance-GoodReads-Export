import multiprocessing
import queue
import sys

import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename

from enhance_goodreads_export import enhance_export, EnhanceExportException


class IOQueue(object):
    def __init__(self, queue: queue.Queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


def task(options: dict, stdout_queue: queue.Queue):
    sys.stdout = IOQueue(stdout_queue)
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
            if self.text.dlineinfo('end-1chars') is not None:  # autoscroll if at end
                scroll = True
            self.text.insert("end", text)
            if scroll:
                self.text.see("end")

        self.after(100, self.update)


def launch_gui():
    def ask_for_filename():
        filename = askopenfilename()
        pathlabel.config(text=filename)

    def ask_for_update_filename():
        filename = askopenfilename()
        update_pathlabel.config(text=filename)

    def start_processing():
        options = {
            "csv": pathlabel["text"] if not pathlabel["text"].startswith("[") else "",
            "update": update_pathlabel["text"] if not update_pathlabel["text"].startswith("[") else "",
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
        update_filebutton["state"] = new_state
        emailentry["state"] = new_state
        passwordentry["state"] = new_state
        forceentry["state"] = new_state
        if new_state == tk.NORMAL:
            forceentry.state(["!alternate", "!selected"])
        start_button["state"] = new_state

    root = tk.Tk()
    root.wm_title("Enhance GoodReads Export Tool")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding="3m")
    frame.pack(fill=tk.BOTH)
    filebutton = ttk.Button(frame, text="export file", command=ask_for_filename)
    filebutton.grid(row=0, column=0, sticky=tk.W)
    pathlabel = ttk.Label(frame, anchor=tk.W, text="[Goodreads export file, new columns will be added to this file]")
    pathlabel.grid(row=0, column=1, columnspan=10, sticky=tk.W)

    update_filebutton = ttk.Button(frame, text="old file", command=ask_for_update_filename)
    update_filebutton.grid(row=1, column=0)
    update_pathlabel = ttk.Label(frame, anchor=tk.W, text="[previously enhanced file to copy values from (optional)]")
    update_pathlabel.grid(row=1, column=1, columnspan=10, sticky=tk.W)

    emaillabel = ttk.Label(frame, text="email:")
    emailentry = ttk.Entry(frame)
    emaillabel.grid(row=2, column=0)
    emailentry.grid(row=2, column=1)
    passwordlabel = ttk.Label(frame, text="password")
    passwordentry = ttk.Entry(frame)
    passwordlabel.grid(row=3, column=0)
    passwordentry.grid(row=3, column=1)
    forcelabel = ttk.Label(frame, text="process all")
    forceentry = ttk.Checkbutton(frame)
    forceentry.state(["!alternate", "!selected"])
    forcehelp = ttk.Label(frame, text="(by default only books without genre information are processed)")
    forcelabel.grid(row=4, column=0)
    forceentry.grid(row=4, column=1)
    forcehelp.grid(row=4, column=2)

    start_button = ttk.Button(frame, text="start processing", command=start_processing)
    start_button.grid(row=5, column=0, columnspan=2, pady=5)

    frame.grid_columnconfigure(0, weight=0)
    frame.grid_columnconfigure(1, weight=0)
    frame.grid_columnconfigure(2, weight=0)
    frame.grid_columnconfigure(3, weight=1)

    stdout_queue = multiprocessing.Queue()
    stdout_queue.cancel_join_thread()
    info = IOText(stdout_queue, frame)
    info.grid(row=10, column=0, columnspan=10, sticky=tk.N + tk.S + tk.E + tk.W)

    root.mainloop()


if __name__ == "__main__":
    # Workaround for multiprocessing when using pyinstaller
    # see https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
    multiprocessing.freeze_support()

    launch_gui()
