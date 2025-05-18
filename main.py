import win32gui
import win32process
import psutil
import ctypes
import time
import sqlite3
from datetime import datetime

# ---------- CONFIGURATION ---------- #

APP_CATEGORIES = {
    "code.exe": "Productive",
    "pycharm64.exe": "Productive",
    "chrome.exe": "Depends",
    "firefox.exe": "Depends",
    "vlc.exe": "Entertainment",
    "spotify.exe": "Entertainment",
    "discord.exe": "Unproductive",
    "notepad.exe": "Productive",
    "word.exe": "Productive",
    "excel.exe": "Productive",
    "netflix.exe": "Entertainment",
    "zoom.exe": "Learning"
}

# ---------- DATABASE SETUP ---------- #

conn = sqlite3.connect("activity_log.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT,
        window_title TEXT,
        start_time TEXT,
        end_time TEXT,
        duration REAL,
        category TEXT
    )
""")
conn.commit()

# ---------- IDLE TIME DETECTION ---------- #

def get_idle_duration():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
    millis = ctypes.windll.kernel32.GetTickCount() - li.dwTime
    return millis / 1000.0  # seconds

# ---------- ACTIVE WINDOW DETECTION ---------- #

def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        proc = psutil.Process(pid)
        app_name = proc.name()
    except Exception:
        app_name = "Unknown"
    window_title = win32gui.GetWindowText(hwnd)
    return app_name, window_title

# ---------- CATEGORY DETECTION ---------- #

def categorize(app, title):
    app = app.lower()
    if app in ["chrome.exe", "firefox.exe"]:
        title = title.lower()
        if "youtube" in title:
            if any(word in title for word in ["tutorial", "course", "lesson"]):
                return "Learning"
            return "Entertainment"
        elif "coursera" in title or "udemy" in title or "edx" in title:
            return "Learning"
        elif "github" in title or "stackoverflow" in title:
            return "Productive"
        elif "netflix" in title or "primevideo" in title:
            return "Entertainment"
        else:
            return "Uncategorized"
    return APP_CATEGORIES.get(app, "Uncategorized")

# ---------- MAIN LOOP ---------- #

last_app = None
start_time = time.time()

try:
    print("Activity Tracker Started. Press Ctrl+C to stop.")
    while True:
        idle_time = get_idle_duration()
        if idle_time > 300:  # 5 minutes
            time.sleep(5)
            continue

        app, title = get_active_window()
        if app != last_app:
            end_time = time.time()

            if last_app is not None:
                duration = round(end_time - start_time, 2)
                category = categorize(last_app[0], last_app[1])
                c.execute(
                    "INSERT INTO activity_log (app_name, window_title, start_time, end_time, duration, category) VALUES (?, ?, ?, ?, ?, ?)",
                    (last_app[0], last_app[1],
                     datetime.fromtimestamp(start_time),
                     datetime.fromtimestamp(end_time),
                     duration, category)
                )
                conn.commit()
                print(f"Logged: {last_app[0]} | {last_app[1]} | {category} | {duration}s")

            last_app = (app, title)
            start_time = time.time()

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping Activity Tracker.")
    conn.close()
