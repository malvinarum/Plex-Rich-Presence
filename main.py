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
import ctypes
import winreg  # Added for Registry Access
from datetime import datetime
from plexapi.myplex import MyPlexAccount
# Remove explicit PlexServer import if not used directly, but keeping it safe
from plexapi.server import PlexServer
from pypresence import Presence, ActivityType
import pystray
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
API_URL = "https://plexrpc-api.malvinarum.com"
APP_NAME = "PlexRPC"
VERSION = "2.3.0"  # Final Feature Update


# --- ASSET RESOURCE HELPER ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
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

# Icons
ICON_ICO = resource_path(os.path.join('assets', 'icon.ico'))
ICON_PNG = resource_path(os.path.join('assets', 'icon.png'))

# --- LOGGING SETUP (File + Console) ---
if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)

log_handlers = [
    logging.FileHandler(LOG_FILE),
    logging.StreamHandler(sys.stdout)
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)


# --- DARK MODE TITLE BAR ---
def dark_title_bar(window):
    try:
        window.update()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        get_parent = ctypes.windll.user32.GetParent
        hwnd = get_parent(window.winfo_id())
        value = ctypes.c_int(2)
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


# --- STARTUP REGISTRY HELPER ---
def set_startup(enable=True):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            exe_path = sys.executable
            # If running as script, use pythonw to hide console
            if not getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            logging.info("Added to startup.")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                logging.info("Removed from startup.")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        logging.error(f"Failed to change startup settings: {e}")


def is_startup_enabled():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


# --- HELPER: FETCH SERVER CONFIG ---
def fetch_config(client_uuid, app_version):
    try:
        logging.info(f"Fetching config from {API_URL}...")
        headers = {
            "X-Client-UUID": client_uuid,
            "X-App-Version": app_version
        }
        res = requests.get(f"{API_URL}/api/config/discord-id", headers=headers, timeout=5)
        res.raise_for_status()
        data = res.json()
        logging.info("Config fetched successfully.")
        return {
            "client_id": data.get('client_id'),
            "latest_version": data.get('latest_version', '0.0.0')
        }
    except Exception as e:
        logging.error(f"Failed to fetch config: {e}")
        return None


# --- SETUP WIZARD (GUI) ---
class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("500x550")

        # Styling
        self.bg_color = "#1f1f1f"
        self.fg_color = "#ffffff"
        self.accent_color = "#e5a00d"

        self.root.configure(bg=self.bg_color)
        dark_title_bar(self.root)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)
        style.configure("TButton", background="#333333", foreground="white", borderwidth=0,
                        focuscolor=self.accent_color)
        style.map("TButton", background=[('active', self.accent_color), ('disabled', '#333333')])
        style.configure("TCombobox", fieldbackground="#333333", background="#333333", foreground="white",
                        arrowcolor="white")
        style.map("TCombobox", fieldbackground=[('readonly', '#333333')])

        if os.path.exists(ICON_ICO):
            self.root.iconbitmap(ICON_ICO)

        self.account = None
        self.servers = []
        self.client_identifier = str(uuid.uuid4())

        self.build_ui()

    def build_ui(self):
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        if os.path.exists(ICON_PNG):
            try:
                img = Image.open(ICON_PNG)
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(self.main_frame, image=self.logo_img, bg=self.bg_color, borderwidth=0).pack(pady=(0, 10))
            except Exception as e:
                logging.error(f"Failed to load logo: {e}")

        ttk.Label(self.main_frame, text=f"Welcome to {APP_NAME}", style="Header.TLabel").pack(pady=(0, 20))
        self.status_lbl = ttk.Label(self.main_frame, text="Please sign in to link your Plex account.", wraplength=450)
        self.status_lbl.pack(pady=10)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        self.login_btn = ttk.Button(self.content_frame, text="Sign in with Plex", command=self.start_oauth)
        self.login_btn.pack(pady=20)

    def start_oauth(self):
        self.login_btn.config(state="disabled")
        self.status_lbl.config(text="Browser opened. Please approve the login...")

        def oauth_thread():
            try:
                headers = {'X-Plex-Product': APP_NAME, 'X-Plex-Client-Identifier': self.client_identifier,
                           'Accept': 'application/json'}

                res = requests.post("https://plex.tv/api/v2/pins?strong=true", headers=headers)
                if res.status_code != 201: raise Exception("Could not generate PIN")
                pin_data = res.json()

                webbrowser.open(
                    f"https://app.plex.tv/auth#?clientID={self.client_identifier}&code={pin_data['code']}&context%5Bdevice%5D%5Bproduct%5D={APP_NAME}")

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
        self.selected_server = self.servers[self.server_combo.current()]
        for w in self.content_frame.winfo_children(): w.destroy()
        self.status_lbl.config(text=f"Connecting to {self.selected_server.name}...")

        def fetch_users():
            try:
                self.plex_instance = self.selected_server.connect()
                try:
                    self.users = self.plex_instance.myPlexAccount().users()
                    self.users.insert(0, self.plex_instance.myPlexAccount())
                except:
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
        self.user_combo['values'] = [u.title if hasattr(u, 'title') else u.username for u in self.users]
        self.user_combo.current(0)
        self.user_combo.pack(fill="x", pady=5)
        ttk.Button(self.content_frame, text="Next", command=self.select_libraries).pack(pady=20)

    def select_libraries(self):
        self.selected_user = self.user_combo.get()
        for w in self.content_frame.winfo_children(): w.destroy()
        self.status_lbl.config(text="Select your Audiobook Libraries (Optional)")

        sections = self.plex_instance.library.sections()
        self.lib_vars = {}
        scroll_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        scroll_frame.pack(fill="both", expand=True, pady=10)

        for section in sections:
            var = tk.BooleanVar()
            if 'book' in section.title.lower(): var.set(True)
            chk = tk.Checkbutton(scroll_frame, text=section.title, variable=var, bg=self.bg_color, fg=self.fg_color,
                                 selectcolor="#444444", activebackground=self.bg_color, activeforeground=self.fg_color)
            chk.pack(anchor="w")
            self.lib_vars[section.title] = var

        ttk.Button(self.content_frame, text="Finish Setup", command=self.save_config).pack(pady=20)

    def save_config(self):
        audiobook_libs = [name for name, var in self.lib_vars.items() if var.get()]
        config_data = {
            "auth_token": self.account.authenticationToken,
            "server_name": self.selected_server.name,
            "user_filter": self.selected_user,
            "audiobook_libraries": audiobook_libs,
            "client_uuid": self.client_identifier
        }

        with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f, indent=4)
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
        self.latest_server_version = None
        self.cache = {}

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            logging.warning("Config file not found.")
            return None
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)

            if 'client_uuid' not in data:
                logging.info("Upgrading config to v2.1 (Adding UUID)")
                data['client_uuid'] = str(uuid.uuid4())
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(data, f, indent=4)

            return data
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return None

    def connect_plex(self):
        try:
            logging.info("Connecting to Plex...")
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
                logging.info("Fetching Discord Client ID...")
                config_data = fetch_config(
                    self.config.get('client_uuid', 'unknown'),
                    VERSION
                )
                if config_data:
                    self.discord_client_id = config_data['client_id']
                    self.latest_server_version = config_data['latest_version']
                else:
                    logging.warning("Could not fetch Discord Client ID from API.")
                    return

            if not self.discord_client_id:
                return

            logging.info(f"Connecting to Discord RPC with ID: {self.discord_client_id}")
            self.rpc = Presence(self.discord_client_id)
            self.rpc.connect()
            logging.info("Successfully connected to Discord RPC!")
        except Exception as e:
            logging.error(f"Discord RPC Connection Error: {e}")
            self.rpc = None

    def get_activity(self):
        try:
            sessions = self.plex.sessions()
            if not sessions:
                return None

            current = next(
                (s for s in sessions if self.config['user_filter'].lower() in [u.lower() for u in s.usernames]), None)

            if not current:
                return None

            activity_type = ActivityType.WATCHING

            status = {
                "details": current.title,
                "state": "Playing",
                "large_image": "plex_logo",
                "small_image": "playing_icon",
                "small_text": "Playing",
                "buttons": [{"label": "Get PlexRPC", "url": "https://github.com/malvinarum/Plex-Rich-Presence"}]
            }

            # --- PAUSE & TIMER LOGIC ---
            is_paused = False
            # Check player state (often in players list)
            if hasattr(current, 'players') and current.players:
                if current.players[0].state == 'paused':
                    is_paused = True

            if not is_paused:
                # ONLY show time bar if NOT paused
                if hasattr(current, 'viewOffset') and hasattr(current, 'duration'):
                    status['start'] = time.time() - (current.viewOffset / 1000)
                    status['end'] = status['start'] + (current.duration / 1000)
            else:
                # If Paused, override text
                status['state'] = "Paused"
                status['small_text'] = "Paused"
                # Note: We do NOT set 'start'/'end' here, so timer disappears.

            q, type_ = current.title, 'movie'

            if current.type == 'episode':
                q, type_ = current.grandparentTitle, 'tv'
                status['details'] = current.grandparentTitle
                # If not paused, show Episode info. If paused, we still want to see Ep info?
                # Usually yes. But status['state'] was set to "Paused" above.
                # Let's append if paused, or overwrite if playing.
                ep_text = f"S{current.parentIndex:02d}E{current.index:02d} - {current.title}"
                if is_paused:
                    status['state'] = f"{ep_text} (Paused)"
                else:
                    status['state'] = ep_text

            elif current.type == 'track':
                activity_type = ActivityType.LISTENING

                artist = current.originalTitle or current.grandparentTitle
                artist_text = f"by {artist}"

                if is_paused:
                    status['state'] = f"{artist_text} (Paused)"
                else:
                    status['state'] = artist_text

                if current.librarySectionTitle in self.config.get('audiobook_libraries',
                                                                  []) or 'book' in current.librarySectionTitle.lower():
                    q, type_ = f"{current.title} {artist}", 'book'
                    status['large_image'] = "book_icon"
                else:
                    status['large_image'] = "plex_logo"
                    q = f"{artist} {current.title}"
                    type_ = 'music'

            status['activity_type'] = activity_type

            if q:
                cache_key = (type_, q)
                if cache_key in self.cache:
                    res = self.cache[cache_key]
                else:
                    try:
                        headers = {
                            "X-Client-UUID": self.config.get('client_uuid', 'unknown'),
                            "X-App-Version": VERSION
                        }
                        res = requests.get(f"{API_URL}/api/metadata/{type_}", params={'q': q}, headers=headers,
                                           timeout=3).json()
                        if res.get('found'):
                            self.cache[cache_key] = res
                    except Exception as e:
                        logging.warning(f"Metadata fetch failed: {e}")
                        res = {}

                if res.get('found'):
                    status['large_image'] = res['image']
                    status['large_text'] = res.get('title', q)

                    # If remote API provides overrides (e.g. for bans/announcements), use them
                    # But respect local pause state for the 'state' line if needed?
                    # Usually remote lines are static. We'll prioritize remote if exists.
                    if res.get('line1'): status['details'] = res['line1']
                    if res.get('line2'): status['state'] = res['line2']

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

            return status
        except Exception as e:
            logging.error(f"Activity Generation Error: {e}")
            return None

    def update_loop(self):
        logging.info("Starting update loop...")
        while self.running:
            if not self.plex:
                if not self.connect_plex():
                    time.sleep(30)
                    continue

            if not self.rpc:
                self.connect_discord()
                if not self.rpc:
                    time.sleep(30)
                    continue

            activity = self.get_activity()
            if activity:
                try:
                    self.rpc.update(**activity)
                except Exception as e:
                    logging.error(f"RPC Update Failed (Discord might be closed): {e}")
                    self.rpc = None
            else:
                try:
                    self.rpc.clear()
                except:
                    pass
            time.sleep(15)

    def stop(self):
        logging.info("Stopping PlexRPC...")
        self.running = False
        if self.rpc:
            try:
                self.rpc.close()
            except:
                pass


# --- SYSTEM TRAY ---
def create_tray(app):
    tray_icon_path = ICON_PNG if os.path.exists(ICON_PNG) else ICON_ICO
    image = Image.open(tray_icon_path) if os.path.exists(tray_icon_path) else Image.new('RGB', (64, 64),
                                                                                        color=(255, 165, 0))

    def on_quit(icon, item):
        icon.stop()
        app.stop()
        os._exit(0)

    def on_reset(icon, item):
        if messagebox.askyesno("Reset Config", "This will delete your login and restart. Continue?"):
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)

            python = sys.executable
            os.execl(python, python, *sys.argv)

    def on_update(icon, item):
        webbrowser.open("https://github.com/malvinarum/Plex-Rich-Presence/releases")

    def toggle_startup(icon, item):
        # Toggle based on current state (item.checked is not auto-updated by pystray logic inside the callback instantly in all versions, better to check registry)
        current = is_startup_enabled()
        set_startup(not current)

    def is_update_available(local, remote):
        try:
            if not remote: return False
            l_parts = [int(x) for x in local.split('.')]
            r_parts = [int(x) for x in remote.split('.')]
            return r_parts > l_parts
        except:
            return False

    menu_items = []
    menu_items.append(pystray.MenuItem(f"{APP_NAME} v{VERSION}", None, enabled=False))

    if hasattr(app, 'latest_server_version') and is_update_available(VERSION, app.latest_server_version):
        menu_items.append(pystray.MenuItem("⚠️ Update Available!", on_update))

    # Startup Checkbox
    menu_items.append(pystray.MenuItem(
        "Run on Startup",
        toggle_startup,
        checked=lambda item: is_startup_enabled()
    ))

    menu_items.append(pystray.MenuItem("Reset Config", on_reset))
    menu_items.append(pystray.MenuItem("Quit", on_quit))

    menu = pystray.Menu(*menu_items)
    icon = pystray.Icon(APP_NAME, image, f"{APP_NAME} (Running)", menu)
    icon.run()


# --- ENTRY POINT ---
if __name__ == "__main__":
    logging.info(f"Starting {APP_NAME} v{VERSION}")

    if not os.path.exists(CONFIG_FILE):
        logging.info("Config not found, starting Wizard.")
        wizard = SetupWizard()
        wizard.run()
        if not os.path.exists(CONFIG_FILE): sys.exit()

    app = PlexPresence()

    # Pre-fetch config to ensure ID is ready before thread starts
    if not app.discord_client_id:
        cfg = fetch_config(app.config.get('client_uuid'), VERSION)
        if cfg:
            app.discord_client_id = cfg['client_id']
            app.latest_server_version = cfg['latest_version']
        else:
            logging.error(
                "Startup Warning: Could not fetch Discord Client ID. RPC will not work until API is reachable.")

    t = threading.Thread(target=app.update_loop)
    t.daemon = True
    t.start()

    create_tray(app)
