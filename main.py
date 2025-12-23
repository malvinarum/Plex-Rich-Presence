import sys
import os
import time
import json
import threading
import webbrowser
import requests
import logging
import uuid
import subprocess
import ctypes  # For Dark Title Bar
from datetime import datetime
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from pypresence import Presence
import pystray
from PIL import Image, ImageTk  # ImageTk needed for Window Icon
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
API_URL = "https://plexrpc-api.malvinarum.com"
APP_NAME = "PlexRPC"
VERSION = "2.0.0"


# --- ASSET RESOURCE HELPER (Fixes Icon Issue) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)

CONFIG_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(CONFIG_DIR, 'app.log')

# Icons (Using resource_path for bundled access)
ICON_ICO = resource_path(os.path.join('assets', 'icon.ico'))
ICON_PNG = resource_path(os.path.join('assets', 'icon.png'))

# Logging Setup
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# --- HELPER: FETCH DISCORD ID ---
def fetch_discord_id():
    try:
        res = requests.get(f"{API_URL}/api/config/discord-id", timeout=5)
        res.raise_for_status()
        return res.json().get('client_id')
    except Exception as e:
        logging.error(f"Failed to fetch Discord Client ID: {e}")
        return None


# --- DARK MODE TITLE BAR ---
def dark_title_bar(window):
    """
    Forces Windows 10/11 Title Bar to Dark Mode using DWM API.
    """
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ctypes.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    value = 2
    value = ctypes.c_int(value)
    set_window_attribute(hwnd, rendering_policy, ctypes.byref(value), ctypes.sizeof(value))


# --- SETUP WIZARD (GUI) ---
class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("500x550")  # Taller for lists

        # --- DARK THEME STYLING ---
        self.bg_color = "#1f1f1f"
        self.fg_color = "#ffffff"
        self.accent_color = "#e5a00d"  # Plex Orange-ish

        self.root.configure(bg=self.bg_color)
        try:
            dark_title_bar(self.root)
        except:
            pass

        # Custom Styles
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' allows easier color customization

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)

        style.configure("TButton", background="#333333", foreground="white", borderwidth=0,
                        focuscolor=self.accent_color)
        style.map("TButton", background=[('active', self.accent_color), ('disabled', '#333333')])

        style.configure("TCombobox", fieldbackground="#333333", background="#333333", foreground="white",
                        arrowcolor="white")
        style.map("TCombobox", fieldbackground=[('readonly', '#333333')])

        # Icon Setup
        if os.path.exists(ICON_ICO):
            self.root.iconbitmap(ICON_ICO)

        self.account = None
        self.servers = []
        self.selected_server = None
        self.selected_user = None
        self.audiobook_libs = []

        self.client_identifier = str(uuid.uuid4())

        self.build_ui()

    def build_ui(self):
        # Main Container
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        # Header
        ttk.Label(self.main_frame, text=f"Welcome to {APP_NAME}", style="Header.TLabel").pack(pady=(0, 20))

        self.status_lbl = ttk.Label(self.main_frame, text="Please sign in to link your Plex account.", wraplength=450)
        self.status_lbl.pack(pady=10)

        # Dynamic Content Area
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        self.login_btn = ttk.Button(self.content_frame, text="Sign in with Plex", command=self.start_oauth)
        self.login_btn.pack(pady=20)

    def start_oauth(self):
        self.login_btn.config(state="disabled")
        self.status_lbl.config(text="Browser opened. Please approve the login...")

        def oauth_thread():
            try:
                headers = {
                    'X-Plex-Product': APP_NAME,
                    'X-Plex-Client-Identifier': self.client_identifier,
                    'Accept': 'application/json'
                }

                # 1. Request PIN
                res = requests.post("https://plex.tv/api/v2/pins?strong=true", headers=headers)
                if res.status_code != 201: raise Exception("Could not generate PIN")
                pin_data = res.json()

                # 2. Open Auth URL
                auth_url = (
                    f"https://app.plex.tv/auth#?clientID={self.client_identifier}&code={pin_data['code']}&context%5Bdevice%5D%5Bproduct%5D={APP_NAME}")
                webbrowser.open(auth_url)

                # 3. Poll
                auth_token = None
                for _ in range(60):
                    time.sleep(2)
                    check = requests.get(f"https://plex.tv/api/v2/pins/{pin_data['id']}", headers=headers)
                    if check.json().get('authToken'):
                        auth_token = check.json()['authToken']
                        break

                if not auth_token: raise Exception("Timed out.")

                self.account = MyPlexAccount(token=auth_token)
                self.root.after(0, self.show_server_selection)

            except Exception as e:
                logging.error(f"Login Failed: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.login_btn.config(state="normal"))

        threading.Thread(target=oauth_thread, daemon=True).start()

    def show_server_selection(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        self.status_lbl.config(text=f"Logged in as {self.account.username}. Fetching servers...")

        def fetch_servers():
            try:
                self.servers = [r for r in self.account.resources() if r.product == 'Plex Media Server']
                self.root.after(0, self._render_server_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=fetch_servers, daemon=True).start()

    def _render_server_list(self):
        if not self.servers:
            self.status_lbl.config(text="No servers found.")
            return

        ttk.Label(self.content_frame, text="Select a Server:", font=("Segoe UI", 10, "bold")).pack(anchor="w",
                                                                                                   pady=(10, 5))

        self.server_var = tk.StringVar()
        self.server_combo = ttk.Combobox(self.content_frame, textvariable=self.server_var, state="readonly")
        self.server_combo['values'] = [f"{s.name}" for s in self.servers]
        self.server_combo.current(0)
        self.server_combo.pack(fill="x", pady=5)

        ttk.Button(self.content_frame, text="Next", command=self.select_user).pack(pady=20)

    def select_user(self):
        # Connect to server to get users
        self.selected_server = self.servers[self.server_combo.current()]

        for w in self.content_frame.winfo_children(): w.destroy()
        self.status_lbl.config(text=f"Connecting to {self.selected_server.name}...")

        def fetch_users():
            try:
                self.plex_instance = self.selected_server.connect()
                # Get all users (Main account + Home users)
                try:
                    # Try fetching home users if admin
                    self.users = self.plex_instance.myPlexAccount().users()
                    # Add admin self
                    self.users.insert(0, self.plex_instance.myPlexAccount())
                except:
                    # Fallback if not admin or error, just use current user
                    self.users = [self.plex_instance.myPlexAccount()]

                self.root.after(0, self._render_user_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Connection Error", str(e)))

        threading.Thread(target=fetch_users, daemon=True).start()

    def _render_user_list(self):
        self.status_lbl.config(text="Who are you watching as?")

        ttk.Label(self.content_frame, text="Select User:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 5))

        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(self.content_frame, textvariable=self.user_var, state="readonly")

        # Display list: Username (or Title)
        user_names = []
        for u in self.users:
            name = u.title if hasattr(u, 'title') else u.username
            user_names.append(name)

        self.user_combo['values'] = user_names
        self.user_combo.current(0)
        self.user_combo.pack(fill="x", pady=5)

        ttk.Button(self.content_frame, text="Next", command=self.select_libraries).pack(pady=20)

    def select_libraries(self):
        # We need this step to restore "Audiobook" selection manually
        idx = self.user_combo.current()
        self.selected_user = self.user_combo.get()  # Store string name for config

        for w in self.content_frame.winfo_children(): w.destroy()
        self.status_lbl.config(text="Select your Audiobook Libraries (Optional)")

        # Fetch Libraries
        sections = self.plex_instance.library.sections()

        self.lib_vars = {}

        scroll_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        scroll_frame.pack(fill="both", expand=True, pady=10)

        for section in sections:
            # Only show music/artist libraries as candidates usually, but show all to be safe
            var = tk.BooleanVar()
            # Check if name contains 'audiobook' or 'book' to auto-check
            if 'book' in section.title.lower():
                var.set(True)

            chk = tk.Checkbutton(scroll_frame, text=section.title, variable=var,
                                 bg=self.bg_color, fg=self.fg_color, selectcolor="#444444",
                                 activebackground=self.bg_color, activeforeground=self.fg_color)
            chk.pack(anchor="w")
            self.lib_vars[section.title] = var

        ttk.Button(self.content_frame, text="Finish Setup", command=self.save_config).pack(pady=20)

    def save_config(self):
        # Gather Audiobook libs
        audiobook_libs = [name for name, var in self.lib_vars.items() if var.get()]

        config_data = {
            "auth_token": self.account.authenticationToken,
            "server_name": self.selected_server.name,
            "user_filter": self.selected_user,
            "audiobook_libraries": audiobook_libs
        }

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)

        messagebox.showinfo("Success", "Setup Complete! PlexRPC will now restart.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# --- MAIN PRESENCE LOGIC ---
class PlexPresence:
    def __init__(self):
        self.running = True
        self.rpc = None
        self.plex = None
        self.config = self.load_config()
        self.discord_client_id = None

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return None
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None

    def connect_plex(self):
        try:
            account = MyPlexAccount(token=self.config['auth_token'])
            resource = account.resource(self.config['server_name'])
            self.plex = resource.connect()
            logging.info(f"Connected to Plex: {self.config['server_name']}")
            return True
        except Exception as e:
            logging.error(f"Plex Connect Error: {e}")
            return False

    def connect_discord(self):
        try:
            if not self.discord_client_id:
                self.discord_client_id = fetch_discord_id()
            if not self.discord_client_id: return

            self.rpc = Presence(self.discord_client_id)
            self.rpc.connect()
            logging.info("Connected to Discord RPC")
        except Exception as e:
            logging.error(f"Discord RPC Error: {e}")

    def get_activity(self):
        try:
            sessions = self.plex.sessions()
            if not sessions: return None

            # Filter User
            current = next(
                (s for s in sessions if self.config['user_filter'].lower() in [u.lower() for u in s.usernames]), None)
            if not current: return None

            status = {
                "details": current.title,
                "state": "Playing",
                "large_image": "plex_logo",
                "small_image": "playing_icon",
                "buttons": [{"label": "Get PlexRPC", "url": "https://github.com/malvinarum/Plex-Rich-Presence"}]
            }

            if hasattr(current, 'viewOffset') and current.type != 'track':
                status['start'] = time.time() - (current.viewOffset / 1000)
                status['end'] = status['start'] + (current.duration / 1000)

            q, type_ = current.title, 'movie'

            if current.type == 'episode':
                q, type_ = current.grandparentTitle, 'tv'
                status['details'] = current.grandparentTitle
                status['state'] = f"S{current.parentIndex:02d}E{current.index:02d} - {current.title}"

            elif current.type == 'track':
                artist = current.originalTitle or current.grandparentTitle
                status['state'] = f"by {artist}"

                # Check config for manual audiobook libs OR fall back to name check
                is_audiobook = False
                if current.librarySectionTitle in self.config.get('audiobook_libraries', []):
                    is_audiobook = True
                elif 'book' in current.librarySectionTitle.lower():
                    is_audiobook = True

                if is_audiobook:
                    q, type_ = f"{current.title} {artist}", 'book'
                    status['large_image'] = "book_icon"
                else:
                    status['large_image'] = "plex_logo"
                    q = f"{artist} {current.title}"
                    type_ = 'music'

            if q:
                try:
                    res = requests.get(f"{API_URL}/api/metadata/{type_}", params={'q': q}, timeout=3).json()
                    if res.get('found'):
                        status['large_image'] = res['image']
                        status['large_text'] = res.get('title', q)
                        if res.get('url'):
                            btn_label = "View Details"
                            if type_ == 'music':
                                btn_label = "Listen on Spotify"
                            elif type_ == 'book':
                                btn_label = "View Book"
                            elif type_ in ['movie', 'tv']:
                                btn_label = "View on TMDB"
                            status['buttons'].insert(0, {"label": btn_label, "url": res['url']})
                            status['buttons'] = status['buttons'][:2]
                except:
                    pass

            return status
        except Exception as e:
            logging.error(f"Activity Error: {e}")
            return None

    def update_loop(self):
        while self.running:
            if not self.plex:
                if not self.connect_plex():
                    time.sleep(30)
                    continue
            if not self.rpc:
                self.connect_discord()

            activity = self.get_activity()
            if activity:
                try:
                    self.rpc.update(**activity)
                except:
                    self.rpc = None
            else:
                try:
                    self.rpc.clear()
                except:
                    pass

            time.sleep(15)

    def stop(self):
        self.running = False
        if self.rpc: self.rpc.close()


# --- SYSTEM TRAY ---
def create_tray(app):
    # Use resource_path for tray icon too
    if os.path.exists(ICON_PNG):
        image = Image.open(ICON_PNG)
    elif os.path.exists(ICON_ICO):
        image = Image.open(ICON_ICO)
    else:
        image = Image.new('RGB', (64, 64), color=(255, 165, 0))

    def on_quit(icon, item):
        icon.stop()
        app.stop()
        os._exit(0)

    def on_reset(icon, item):
        # FIX: Explicit restart logic
        if messagebox.askyesno("Reset Config", "This will delete your login and restart. Continue?"):
            if os.path.exists(CONFIG_FILE):
                try:
                    os.remove(CONFIG_FILE)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete config: {e}")
                    return

            icon.stop()
            app.stop()
            # Restart Application
            python = sys.executable
            os.execl(python, python, *sys.argv)

    menu = pystray.Menu(
        pystray.MenuItem(f"{APP_NAME} v{VERSION}", None, enabled=False),
        pystray.MenuItem("Reset Config", on_reset),
        pystray.MenuItem("Quit", on_quit)
    )

    icon = pystray.Icon(APP_NAME, image, f"{APP_NAME} (Running)", menu)
    icon.run()


# --- ENTRY POINT ---
if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        wizard = SetupWizard()
        wizard.run()
        if not os.path.exists(CONFIG_FILE):
            sys.exit()

    app = PlexPresence()
    t = threading.Thread(target=app.update_loop)
    t.daemon = True
    t.start()
    create_tray(app)