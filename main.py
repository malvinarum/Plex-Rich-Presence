import sys
import os
import time
import json
import threading
import webbrowser
import requests
import logging
import uuid
import ctypes
import winreg
from plexapi.myplex import MyPlexAccount
from pypresence import Presence, ActivityType
import pystray
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
API_URL = "YOUR_API_URL_HERE"
APP_NAME = "PlexRPC"
VERSION = "2.3.0"


# --- ASSET RESOURCE HELPER ---
def resource_path(relative_path):
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

ICON_ICO = resource_path(os.path.join('assets', 'icon.ico'))
ICON_PNG = resource_path(os.path.join('assets', 'icon.png'))

# --- LOGGING SETUP ---
if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)

if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
    try:
        os.remove(LOG_FILE)
    except Exception:
        pass

log_handlers = [logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=log_handlers)


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


def set_startup(enable=True):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            exe_path = sys.executable if getattr(sys, 'frozen',
                                                 False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
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
        logging.error(f"Failed to change startup: {e}")


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except:
        return False


def fetch_config(client_uuid, app_version):
    try:
        headers = {"X-Client-UUID": client_uuid, "X-App-Version": app_version}
        res = requests.get(f"{API_URL}/api/config/discord-id", headers=headers, timeout=5)
        res.raise_for_status()
        data = res.json()
        return {"client_id": data.get('client_id'), "latest_version": data.get('latest_version', '0.0.0')}
    except Exception as e:
        logging.error(f"Failed to fetch config: {e}")
        return None


# --- DYNAMIC TRAY ICON GENERATOR ---
def create_status_icon(base_icon_path, status_color):
    try:
        base = Image.open(base_icon_path).convert("RGBA")
        colors = {
            "green": (35, 165, 89, 255),  # Playing
            "blue": (88, 101, 242, 255),  # Paused
            "orange": (250, 166, 26, 255),  # Idle
            "red": (237, 66, 69, 255),  # Error
            "yellow": (254, 231, 92, 255),  # Warning
            "grey": (153, 170, 181, 255)  # Paused/Ghost Mode
        }
        color = colors.get(status_color, (128, 128, 128, 255))
        overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = base.size
        dot_size = int(w * 0.35)
        x0, y0 = w - dot_size, h - dot_size
        draw.ellipse((x0, y0, w, h), fill=color, outline=(0, 0, 0, 255), width=2)
        return Image.alpha_composite(base, overlay)
    except Exception as e:
        logging.error(f"Icon Gen Error: {e}")
        return Image.open(base_icon_path)


class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("500x550")
        self.bg_color, self.fg_color, self.accent_color = "#1f1f1f", "#ffffff", "#e5a00d"
        self.root.configure(bg=self.bg_color)
        dark_title_bar(self.root)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)
        style.configure("TButton", background="#333333", foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', self.accent_color)])
        if os.path.exists(ICON_ICO): self.root.iconbitmap(ICON_ICO)
        self.account, self.servers, self.client_identifier = None, [], str(uuid.uuid4())
        self.build_ui()

    def build_ui(self):
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)
        if os.path.exists(ICON_PNG):
            img = Image.open(ICON_PNG).resize((100, 100), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(self.main_frame, image=self.logo_img, bg=self.bg_color).pack(pady=(0, 10))
        ttk.Label(self.main_frame, text=f"Welcome to {APP_NAME}", style="Header.TLabel").pack(pady=(0, 20))
        self.status_lbl = ttk.Label(self.main_frame, text="Please sign in to link your Plex account.", wraplength=450)
        self.status_lbl.pack(pady=10)
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)
        self.login_btn = ttk.Button(self.content_frame, text="Sign in with Plex", command=self.start_oauth)
        self.login_btn.pack(pady=20)

    def start_oauth(self):
        self.login_btn.config(state="disabled")

        def oauth_thread():
            try:
                headers = {'X-Plex-Product': APP_NAME, 'X-Plex-Client-Identifier': self.client_identifier,
                           'Accept': 'application/json'}
                res = requests.post("https://plex.tv/api/v2/pins?strong=true", headers=headers).json()
                webbrowser.open(
                    f"https://app.plex.tv/auth#?clientID={self.client_identifier}&code={res['code']}&context%5Bdevice%5D%5Bproduct%5D={APP_NAME}")
                auth_token = None
                for _ in range(60):
                    time.sleep(2)
                    check = requests.get(f"https://plex.tv/api/v2/pins/{res['id']}", headers=headers).json()
                    if check.get('authToken'):
                        auth_token = check['authToken']
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

        def fetch_servers():
            self.servers = [r for r in self.account.resources() if r.product == 'Plex Media Server']
            self.root.after(0, self._render_server_list)

        threading.Thread(target=fetch_servers, daemon=True).start()

    def _render_server_list(self):
        self.server_var = tk.StringVar()
        self.server_combo = ttk.Combobox(self.content_frame, textvariable=self.server_var, state="readonly")
        self.server_combo['values'] = [s.name for s in self.servers]
        self.server_combo.current(0)
        self.server_combo.pack(fill="x", pady=5)
        ttk.Button(self.content_frame, text="Next", command=self.select_user).pack(pady=20)

    def select_user(self):
        self.selected_server = self.servers[self.server_combo.current()]
        for w in self.content_frame.winfo_children(): w.destroy()

        def fetch_users():
            self.plex_instance = self.selected_server.connect()
            try:
                self.users = self.plex_instance.myPlexAccount().users()
                self.users.insert(0, self.plex_instance.myPlexAccount())
            except:
                self.users = [self.plex_instance.myPlexAccount()]
            self.root.after(0, self._render_user_list)

        threading.Thread(target=fetch_users, daemon=True).start()

    def _render_user_list(self):
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(self.content_frame, textvariable=self.user_var, state="readonly")
        # Step 2: The Identity Fix (Literal Username)
        self.user_combo['values'] = [u.username for u in self.users]
        self.user_combo.current(0)
        self.user_combo.pack(fill="x", pady=5)
        ttk.Button(self.content_frame, text="Next", command=self.select_libraries).pack(pady=20)

    def select_libraries(self):
        self.selected_user = self.user_combo.get()
        for w in self.content_frame.winfo_children(): w.destroy()
        sections = self.plex_instance.library.sections()
        self.lib_vars = {}
        for section in sections:
            var = tk.BooleanVar(value='book' in section.title.lower())
            tk.Checkbutton(self.content_frame, text=section.title, variable=var, bg=self.bg_color, fg=self.fg_color,
                           selectcolor="#444444").pack(anchor="w")
            self.lib_vars[section.title] = var
        ttk.Button(self.content_frame, text="Finish Setup", command=self.save_config).pack(pady=20)

    def save_config(self):
        config_data = {
            "auth_token": self.account.authenticationToken,
            "server_name": self.selected_server.name,
            "user_filter": self.selected_user,
            "audiobook_libraries": [n for n, v in self.lib_vars.items() if v.get()],
            "client_uuid": self.client_identifier
        }
        with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f, indent=4)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class PlexPresence:
    def __init__(self):
        self.running, self.rpc, self.plex, self.cache = True, None, None, {}
        self.config = self.load_config()
        self.discord_client_id, self.latest_server_version = None, None
        self.last_activity_log = None
        self.status_color = "orange"
        self.status_text = "Idle"
        self.tray_icon = None
        self.last_tray_color = None
        self.paused = False  # Ghost Mode Flag

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return None
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            if 'client_uuid' not in data:
                data['client_uuid'] = str(uuid.uuid4())
                with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)
            return data

    def connect_plex(self):
        try:
            logging.info("Connecting to Plex...")
            account = MyPlexAccount(token=self.config['auth_token'])
            self.plex = account.resource(self.config['server_name']).connect()
            logging.info(f"Connected to Plex Server: {self.config['server_name']}")
            return True
        except Exception as e:
            logging.error(f"Plex Connection Error: {e}")
            self.status_color = "red"
            self.status_text = "Plex Error"
            return False

    def connect_discord(self):
        try:
            if not self.discord_client_id:
                cfg = fetch_config(self.config.get('client_uuid', 'unknown'), VERSION)
                if cfg:
                    self.discord_client_id, self.latest_server_version = cfg['client_id'], cfg['latest_version']

            if self.discord_client_id:
                logging.info(f"Connecting to Discord RPC (ID: {self.discord_client_id})...")
                self.rpc = Presence(self.discord_client_id)
                self.rpc.connect()
                logging.info("Successfully connected to Discord RPC!")
        except Exception as e:
            logging.error(f"Discord RPC Error: {e}")
            self.status_color = "yellow"
            self.status_text = "Discord Disconnected"
            self.rpc = None

    def get_activity(self):
        try:
            sessions = self.plex.sessions()
            current = next(
                (s for s in sessions if self.config['user_filter'].lower() in [u.lower() for u in s.usernames]), None)

            if not current:
                self.status_color = "orange"
                self.status_text = "Idle"
                return None

            current_activity_type = ActivityType.WATCHING

            status = {
                "details": current.title,
                "state": "Playing",
                "large_image": "plex_logo",
                "small_image": "playing_icon",
                "small_text": "Playing",
                "buttons": [{"label": "Get PlexRPC", "url": "https://github.com/malvinarum/Plex-Rich-Presence"}]
            }

            is_paused = current.players[0].state == 'paused' if hasattr(current,
                                                                        'players') and current.players else False

            if is_paused:
                self.status_color = "blue"
                self.status_text = "Paused"
            else:
                self.status_color = "green"
                self.status_text = "Playing"

            if not is_paused and hasattr(current, 'viewOffset') and hasattr(current, 'duration'):
                status['start'] = time.time() - (current.viewOffset / 1000)
                status['end'] = status['start'] + (current.duration / 1000)
            elif is_paused:
                status['state'], status['small_text'] = "Paused", "Paused"

            q, type_ = current.title, 'movie'

            if current.type == 'episode':
                q, type_ = current.grandparentTitle, 'tv'
                status['details'] = q
                status['state'] = f"S{current.parentIndex:02d}E{current.index:02d} - {current.title}" + (
                    " (Paused)" if is_paused else "")

            elif current.type == 'track':
                current_activity_type = ActivityType.LISTENING
                artist = current.originalTitle or current.grandparentTitle or "Unknown Artist"
                album = getattr(current, 'parentTitle', '')
                status['state'] = f"by {artist}" + (" (Paused)" if is_paused else "")
                status['large_text'] = album if album else artist

                if current.librarySectionTitle in self.config.get('audiobook_libraries',
                                                                  []) or 'book' in current.librarySectionTitle.lower():
                    q, type_, status['large_image'] = f"{current.title} {artist}", 'book', "book_icon"
                else:
                    q, type_, status['large_image'] = f"{artist} {current.title}", 'music', "plex_logo"

            status['activity_type'] = current_activity_type

            if q:
                cache_key = (type_, q)
                res = self.cache.get(cache_key)
                if not res:
                    try:
                        res = requests.get(f"{API_URL}/api/metadata/{type_}", params={'q': q},
                                           headers={"X-Client-UUID": self.config.get('client_uuid', 'unknown'),
                                                    "X-App-Version": VERSION}, timeout=3).json()
                        if res.get('found'): self.cache[cache_key] = res
                    except:
                        res = {}

                if res.get('found'):
                    status['large_image'] = res['image']
                    if not status.get('large_text') or status['large_text'] == artist:
                        status['large_text'] = res.get('title', q)
                    if res.get('line1'): status['details'] = res['line1']
                    if res.get('line2') and type_ != 'music': status['state'] = res['line2']
                    if res.get('url'):
                        btn_label = "Listen on Spotify" if type_ == 'music' else "View Book" if type_ == 'book' else "View on TMDB"
                        status['buttons'].insert(0, {"label": btn_label, "url": res['url']})
                        status['buttons'] = status['buttons'][:2]

            return status
        except Exception as e:
            logging.error(f"Activity Error: {e}")
            self.status_color = "red"
            self.status_text = "Logic Error"
            return None

    def update_tray_icon(self):
        """Updates the tray icon state directly from the main loop"""
        if not self.tray_icon: return
        base_icon = ICON_PNG if os.path.exists(ICON_PNG) else ICON_ICO
        try:
            current_title = f"{APP_NAME}: {self.status_text}"
            if self.tray_icon.title != current_title:
                self.tray_icon.title = current_title

            if self.status_color != self.last_tray_color:
                new_icon = create_status_icon(base_icon, self.status_color)
                self.tray_icon.icon = new_icon
                self.last_tray_color = self.status_color
        except Exception as e:
            logging.error(f"Tray Update Error: {e}")

    def update_loop(self):
        logging.info("Starting update loop...")
        while self.running:
            # --- CHECK GHOST MODE ---
            if self.paused:
                self.status_color = "grey"
                self.status_text = "Presence Paused"
                self.update_tray_icon()

                # Clear RPC if it was active
                if self.rpc:
                    try:
                        self.rpc.clear()
                    except:
                        pass

                time.sleep(2)  # Short sleep to respond quickly to toggle
                continue

            if not self.plex:
                self.status_color = "red"
                self.status_text = "Plex Disconnected"
                if not self.connect_plex():
                    self.update_tray_icon()
                    time.sleep(30);
                    continue

            if not self.rpc:
                self.status_color = "yellow"
                self.status_text = "Connecting Discord..."
                self.update_tray_icon()
                self.connect_discord()
                if not self.rpc:
                    pass

            activity = self.get_activity()

            if activity and self.rpc:
                current_signature = (activity.get('details'), activity.get('state'))
                if current_signature != self.last_activity_log:
                    logging.info(f"Update: {activity.get('details')} - {activity.get('state')}")
                    self.last_activity_log = current_signature

                try:
                    self.rpc.update(**activity)
                except Exception as e:
                    logging.error(f"RPC Update Failed: {e}")
                    self.status_color = "yellow"
                    self.status_text = "Discord Disconnected"
                    self.rpc = None
            elif self.rpc:
                if self.last_activity_log is not None:
                    logging.info("Update: Session Ended (Idle)")
                    self.last_activity_log = None
                try:
                    self.rpc.clear()
                except:
                    pass

            self.update_tray_icon()
            time.sleep(15)

    def stop(self):
        self.running = False
        if self.rpc: self.rpc.close()


def create_tray(app):
    base_icon = ICON_PNG if os.path.exists(ICON_PNG) else ICON_ICO
    icon = pystray.Icon(APP_NAME, Image.open(base_icon), f"{APP_NAME} (Initializing...)")
    app.tray_icon = icon

    def on_quit(icon, item):
        icon.stop(); app.stop(); os._exit(0)

    # --- PAUSE TOGGLE ---
    def on_toggle_pause(icon, item):
        app.paused = not app.paused
        # Force immediate visual update in the next loop cycle

    def on_reset(icon, item):
        def reset_thread():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                if messagebox.askyesno("Reset Config", "This will delete your login and restart.\nContinue?",
                                       parent=root):
                    icon.stop()
                    app.stop()
                    if os.path.exists(CONFIG_FILE):
                        try:
                            os.remove(CONFIG_FILE)
                        except:
                            pass
                    os.execl(sys.executable, sys.executable, *sys.argv)
            finally:
                root.destroy()

        threading.Thread(target=reset_thread, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem(f"{APP_NAME} v{VERSION}", None, enabled=False),
        # Toggle Pause
        pystray.MenuItem("Pause Presence", on_toggle_pause, checked=lambda item: app.paused),
        pystray.MenuItem("Run on Startup", lambda i, v: set_startup(not is_startup_enabled()),
                         checked=lambda i: is_startup_enabled()),
        pystray.MenuItem("Reset Config", on_reset),
        pystray.MenuItem("Quit", on_quit)
    )

    icon.menu = menu
    icon.run()


if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        SetupWizard().run()
        if not os.path.exists(CONFIG_FILE): sys.exit()
    app = PlexPresence()
    threading.Thread(target=app.update_loop, daemon=True).start()
    create_tray(app)