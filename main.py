import time
import logging
import json
import sys
import os
import requests
import threading
import shutil
import tkinter as tk
from tkinter import messagebox
from pypresence import Presence
from plexapi.server import PlexServer
from tmdbv3api import TMDb, Movie, TV
import pystray
from PIL import Image, ImageDraw

# --- GLOBAL FLAGS ---
running = True


# --- UTILS ---
def get_base_path():
    """
    Determines the path where the application is running.
    Used for external files like config.json.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """
    Get absolute path to resource.
    Used for embedded files like icon.png inside the exe.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".venv")

    return os.path.join(base_path, relative_path)


def show_error(title, message):
    """Shows a native popup window (works even if compiled noconsole)"""
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    root.attributes("-topmost", True)  # Make sure it appears on top
    messagebox.showerror(title, message)
    root.destroy()


def validate_config(cfg):
    """Checks if the user has actually filled in the config"""
    placeholders = [
        "YOUR_DISCORD_APP_ID",
        "YOUR_PLEX_TOKEN",
        "YOUR_TMDB_API_KEY",
        "YOUR_GOOGLE_BOOKS_KEY"
    ]

    issues = []

    # Check key fields
    if cfg['discord']['client_id'] in placeholders:
        issues.append("Discord Client ID")
    if cfg['plex']['token'] in placeholders:
        issues.append("Plex Token")
    if cfg['tmdb']['api_key'] in placeholders:
        issues.append("TMDB API Key")

    if issues:
        msg = "The following settings are still set to default:\n\n"
        msg += "\n".join([f"- {i}" for i in issues])
        msg += "\n\nPlease open config.json and fill in your real keys.\nCheck README.md for instructions."
        show_error("Configuration Invalid", msg)
        return False
    return True


def load_config():
    base_path = get_base_path()
    config_path = os.path.join(base_path, 'config.json')
    example_path = os.path.join(base_path, 'config.example.json')

    # 1. Check if config.json exists
    if not os.path.exists(config_path):
        # 2. If not, try to copy example
        if os.path.exists(example_path):
            try:
                shutil.copy(example_path, config_path)
                show_error("First Run",
                           "A new 'config.json' has been created.\n\nPlease open it and fill in your keys before running this again.")
                sys.exit(0)  # Exit so they can edit it
            except Exception as e:
                show_error("Error", f"Could not create config.json: {e}")
                sys.exit(1)
        else:
            show_error("Missing Config",
                       "Neither 'config.json' nor 'config.example.json' was found.\n\nPlease reinstall or restore the files.")
            sys.exit(1)

    # 3. Load the config
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)

        # 4. Validate the config
        if not validate_config(cfg):
            sys.exit(1)

        return cfg

    except json.JSONDecodeError:
        show_error("JSON Error", "Your config.json is not valid JSON.\nDid you miss a comma or quote?")
        sys.exit(1)
    except Exception as e:
        show_error("Startup Error", f"Unexpected error loading config: {e}")
        sys.exit(1)


# --- INITIALIZATION ---
config = load_config()

# Logging Setup
log_level = getattr(logging, config['settings']['log_level'].upper(), logging.INFO)
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

# API Setup
tmdb = TMDb()
tmdb.api_key = config['tmdb']['api_key']
tmdb_movie = Movie()
tmdb_tv = TV()

# Discord Setup
RPC = Presence(config['discord']['client_id'])
try:
    RPC.connect()
    logging.info("Connected to Discord RPC")
except Exception as e:
    logging.error(f"Could not connect to Discord: {e}")

# Plex Setup
try:
    plex = PlexServer(config['plex']['base_url'], config['plex']['token'])
    logging.info(f"Connected to Plex Server: {plex.friendlyName}")
except Exception as e:
    show_error("Connection Failed",
               f"Could not connect to Plex.\n\nError: {e}\n\nCheck your IP and Token in config.json")
    sys.exit(1)


# --- HELPERS ---
def fetch_tmdb_image(query, media_type):
    """
    Fetches image and content URL from TMDB.
    Returns: (image_url, link_url)
    """
    try:
        if media_type == 'movie':
            results = tmdb_movie.search(query)
            if results and results[0].poster_path:
                img = f"https://image.tmdb.org/t/p/w500{results[0].poster_path}"
                url = f"https://www.themoviedb.org/movie/{results[0].id}"
                return img, url
        else:
            results = tmdb_tv.search(query)
            if results and results[0].poster_path:
                img = f"https://image.tmdb.org/t/p/w500{results[0].poster_path}"
                url = f"https://www.themoviedb.org/tv/{results[0].id}"
                return img, url
    except Exception as e:
        logging.error(f"TMDB Error: {e}")
    return "plex_logo", None


def fetch_book_metadata(query):
    """
    Fetches image and content URL from Google Books.
    Returns: (image_url, link_url)
    """
    api_key = config['google_books']['api_key']
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"
        response = requests.get(url).json()
        if "items" in response and len(response["items"]) > 0:
            book = response["items"][0]["volumeInfo"]
            img = book.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
            url = book.get("infoLink", "") # Google Books info page
            return img, url
    except Exception as e:
        logging.error(f"Google Books Error: {e}")
    return "plex_logo", None


def get_plex_activity():
    try:
        sessions = plex.sessions()
        if not sessions:
            return None

        target_user = config['plex'].get('user_filter')
        current_session = None

        if target_user:
            for session in sessions:
                if session.usernames[0].lower() == target_user.lower():
                    current_session = session
                    break
        else:
            if sessions:
                current_session = sessions[0]

        if not current_session:
            return None

        media = current_session
        status = {
            "state": "Idle",
            "details": "",
            "large_image": "plex_logo",
            "small_image": "playing_icon",
            "small_text": "Playing",
            "start": None,
            "end": None,
            "button_url": None,
            "button_label": "View Details"
        }

        # Timer Logic
        if hasattr(media, 'duration') and hasattr(media, 'viewOffset'):
            now = time.time()
            duration_sec = media.duration / 1000
            offset_sec = media.viewOffset / 1000
            status["start"] = now - offset_sec
            status["end"] = status["start"] + duration_sec

        # Type Logic
        if media.type == 'movie':
            status["details"] = media.title
            status["state"] = str(media.year)
            status["large_image"], status["button_url"] = fetch_tmdb_image(media.title, 'movie')
            status["button_label"] = "View on TMDB"

        elif media.type == 'episode':
            show_title = media.grandparentTitle
            episode_title = media.title
            season_ep = f"S{media.parentIndex:02d}E{media.index:02d}"
            status["details"] = show_title
            status["state"] = f"{season_ep} - {episode_title}"
            status["large_image"], status["button_url"] = fetch_tmdb_image(show_title, 'show')
            status["button_label"] = "View on TMDB"

        elif media.type == 'track':
            lib_name = media.librarySectionTitle
            if lib_name in config['plex']['audiobook_libraries']:
                status["details"] = media.title
                status["state"] = f"by {media.originalTitle or media.grandparentTitle}"
                query = f"{media.title} {media.originalTitle or media.grandparentTitle}"
                status["large_image"], status["button_url"] = fetch_book_metadata(query)
                status["button_label"] = "View Book"
            else:
                status["details"] = media.title
                status["state"] = f"by {media.originalTitle or media.grandparentTitle}"
                status["large_image"] = "music_icon"
                status["button_url"] = None

        return status

    except Exception as e:
        logging.error(f"Error loop: {e}")
        return None


# --- BACKGROUND WORKER ---
def presence_loop():
    interval = config['settings']['update_interval']
    logging.info(f"Starting background loop. Updating every {interval}s...")

    while running:
        activity = get_plex_activity()

        if activity:
            # Build Buttons
            buttons = []

            # Button 1: Static
            buttons.append({"label": "Get PlexRPC", "url": "https://github.com/malvinarum/Plex-Rich-Presence"})

            # Button 2: Dynamic (Only if URL exists)
            if activity.get("button_url"):
                buttons.append({"label": activity["button_label"], "url": activity["button_url"]})

            try:
                RPC.update(
                    details=activity["details"],
                    state=activity["state"],
                    large_image=activity["large_image"],
                    large_text=activity["details"],
                    small_image=activity["small_image"],
                    small_text=activity["small_text"],
                    start=activity["start"],
                    end=activity["end"],
                    buttons=buttons
                )
                logging.debug(f"Updated: {activity['details']}")
            except Exception as e:
                logging.error(f"RPC Update Failed: {e}")
        else:
            try:
                RPC.clear()
            except:
                pass

        for _ in range(interval):
            if not running: break
            time.sleep(1)


# --- SYSTEM TRAY ---
def create_image():
    # Looks for icon embedded inside the exe
    icon_path = resource_path(".venv/icon.png")

    if os.path.exists(icon_path):
        return Image.open(icon_path)

    # Fallback generator
    width = 64
    height = 64
    color1 = "black"
    color2 = "#e5a00d"
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color2)
    return image


def on_quit(icon, item):
    global running
    running = False
    icon.stop()
    logging.info("Stopping PlexRPC...")


def run_tray():
    image = create_image()
    menu = pystray.Menu(pystray.MenuItem('Quit', on_quit))
    icon = pystray.Icon("PlexRPC", image, "Plex Rich Presence", menu)
    icon.run()


if __name__ == "__main__":
    t = threading.Thread(target=presence_loop)
    t.start()
    run_tray()
    t.join()
    sys.exit(0)