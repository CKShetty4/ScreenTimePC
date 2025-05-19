import platform
import time
import sqlite3
from datetime import datetime

# For Windows
if platform.system() == "Windows":
    import win32gui
    import win32process
    import psutil
    import ctypes

# For macOS
if platform.system() == "Darwin":
    import subprocess

# For Linux
if platform.system() == "Linux":
    import subprocess

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
    "zoom.exe": "Learning",
    "code": "Productive",        # for macOS/Linux apps without .exe
    "pycharm": "Productive",
    "chrome": "Depends",
    "firefox": "Depends",
    "vlc": "Entertainment",
    "spotify": "Entertainment",
    "discord": "Unproductive",
    "gedit": "Productive",
    "libreoffice": "Productive",
    "zoom": "Learning",
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
    system = platform.system()
    if system == "Windows":
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
        li = LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
        millis = ctypes.windll.kernel32.GetTickCount() - li.dwTime
        return millis / 1000.0  # seconds
    elif system == "Darwin":
        try:
            output = subprocess.check_output(
                ['ioreg', '-c', 'IOHIDSystem']
            ).decode()
            import re
            idle_time_sec = 0
            # The output has "HIDIdleTime" in nanoseconds
            match = re.search(r'"HIDIdleTime" = (\d+)', output)
            if match:
                nanoseconds = int(match.group(1))
                idle_time_sec = nanoseconds / 1_000_000_000
            return idle_time_sec
        except Exception:
            return 0
    elif system == "Linux":
        try:
            output = subprocess.check_output(['xprintidle']).decode()
            millis = int(output.strip())
            return millis / 1000.0
        except Exception:
            return 0
    else:
        return 0

# ---------- ACTIVE WINDOW DETECTION ---------- #

def get_active_window():
    system = platform.system()
    if system == "Windows":
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            app_name = proc.name()
        except Exception:
            app_name = "Unknown"
        window_title = win32gui.GetWindowText(hwnd)
        return app_name, window_title

    elif system == "Darwin":
        try:
            # Get active app name
            app_name = subprocess.check_output(
                ['osascript', '-e', 'tell application "System Events" to get name of (processes where frontmost is true)']
            ).decode().strip()
            # Get active window title
            window_title = subprocess.check_output(
                ['osascript', '-e', 'tell application "System Events" to get title of front window of (processes where frontmost is true)']
            ).decode().strip()
            return app_name, window_title
        except Exception:
            return "Unknown", "Unknown"

    elif system == "Linux":
        try:
            # Use xprop to get active window id
            win_id = subprocess.check_output(['xdotool', 'getactivewindow']).decode().strip()
            # Use xprop to get WM_CLASS and WM_NAME
            wm_class = subprocess.check_output(['xprop', '-id', win_id, 'WM_CLASS']).decode()
            wm_name = subprocess.check_output(['xprop', '-id', win_id, 'WM_NAME']).decode()
            
            import re
            # Extract app name
            m = re.search(r'WM_CLASS\(STRING\) = "([^"]+)", "([^"]+)"', wm_class)
            if m:
                app_name = m.group(2).lower()
            else:
                app_name = "Unknown"

            # Extract window title
            m = re.search(r'WM_NAME\(STRING\) = "([^"]+)"', wm_name)
            window_title = m.group(1) if m else "Unknown"

            return app_name, window_title
        except Exception:
            return "Unknown", "Unknown"
    else:
        return "Unknown", "Unknown"

# ---------- CATEGORY DETECTION ---------- #

def categorize(app, title):
    app = app.lower()
    title = title.lower()
    if app in ["chrome.exe", "firefox.exe", "chrome", "firefox"]:
        if "youtube" in title:
            if any(word in title for word in ["tutorial", "course", "lesson"]):
                return "Learning"
            return "Entertainment"
        elif any(edu in title for edu in ["coursera", "udemy", "edx"]):
            return "Learning"
        elif any(dev in title for dev in ["github", "stackoverflow"]):
            return "Productive"
        elif any(ent in title for ent in ["netflix", "primevideo"]):
            return "Entertainment"
        else:
            return "Uncategorized"
    return APP_CATEGORIES.get(app, "Uncategorized")

# ---------- MAIN LOOP ---------- #

def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"

def main():
    last_app = None
    start_time = time.time()

    print(f"Starting activity tracker on {platform.system()}. Press Ctrl+C to stop.")

    try:
        while True:
            idle_time = get_idle_duration()
            if idle_time > 300:  # 5 minutes idle, skip logging
                time.sleep(5)
                continue

            app, title = get_active_window()

            if last_app is None:
                last_app = (app, title)
                start_time = time.time()

            elif app != last_app[0] or title != last_app[1]:
                end_time = time.time()
                duration = round(end_time - start_time, 2)
                category = categorize(last_app[0], last_app[1])

                c.execute(
                    "INSERT INTO activity_log (app_name, window_title, start_time, end_time, duration, category) VALUES (?, ?, ?, ?, ?, ?)",
                    (last_app[0], last_app[1],
                     datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"),
                     datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S"),
                     duration, category)
                )
                conn.commit()
                print(f"Logged: {last_app[0]} | {last_app[1]} | {category} | {format_duration(duration)}")

                last_app = (app, title)
                start_time = time.time()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping Activity Tracker.")
        conn.close()

if __name__ == "__main__":
    main()
