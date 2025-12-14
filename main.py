import time
import logging
import json
import sys
import os
import requests
import threading
import tkinter as tk
import webbrowser
import uuid
from tkinter import messagebox, ttk
from pypresence import Presence
from plexapi.server import PlexServer
import pystray
from PIL import Image, ImageDraw, ImageTk

# --- CONFIG ---
API_URL = "https://plexrpc-api.malvinarum.com"
SESSION_FILE = "session.json"
RUNNING = True
APP_NAME = "PlexRPC"
TRAY_ICON = None  # Global reference for updating status


# --- UTILS ---
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".venv")  # Default dev path

    path = os.path.join(base_path, relative_path)
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    return path


# --- "PRO MOVE" SESSION MANAGEMENT ---
def get_config_path():
    """Returns path to AppData/Roaming/PlexRPC"""
    app_data = os.getenv('APPDATA')
    if not app_data: app_data = os.path.expanduser("~")

    config_dir = os.path.join(app_data, APP_NAME)
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError:
            return os.path.dirname(os.path.abspath(__file__))
    return config_dir


def load_session():
    # 1. Check AppData (The new standard)
    config_dir = get_config_path()
    path = os.path.join(config_dir, SESSION_FILE)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            pass

    # 2. Check Local Folder (Legacy/Portable support)
    local_path = os.path.join(get_base_path(), SESSION_FILE)
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                return json.load(f)
        except:
            pass

    return None


def save_session(data):
    # Always save to AppData for new/updated sessions
    config_dir = get_config_path()
    path = os.path.join(config_dir, SESSION_FILE)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Session saved to {path}")
    except Exception as e:
        logging.error(f"Failed to save session: {e}")


def get_client_identifier():
    session = load_session()
    if session and session.get('client_id'): return session['client_id']
    return str(uuid.uuid4())


# --- THE UNIFIED WIZARD ---
class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PlexRPC Setup")
        self.geometry("450x550")
        self.configure(bg="#2d2d2d")
        self.attributes("-topmost", True)

        # Icon
        ico_path = resource_path("icon.ico")
        if os.path.exists(ico_path): self.iconbitmap(ico_path)

        # Data
        self.client_id = get_client_identifier()
        self.data = {"client_id": self.client_id, "settings": {"update_interval": 15}}
        self.plex_instance = None

        # Container
        self.container = tk.Frame(self, bg="#2d2d2d")
        self.container.pack(expand=True, fill="both", padx=20, pady=20)

        self.show_login_step()

    def clear_frame(self):
        for widget in self.container.winfo_children(): widget.destroy()

    def header(self, text):
        tk.Label(self.container, text=text, bg="#2d2d2d", fg="white", font=("Segoe UI", 14, "bold"),
                 wraplength=400).pack(pady=(0, 20))

    def status(self, text):
        lbl = tk.Label(self.container, text=text, bg="#2d2d2d", fg="#aaaaaa", font=("Segoe UI", 9))
        lbl.pack(side=tk.BOTTOM, pady=10)
        return lbl

    # STEP 1: LOGIN
    def show_login_step(self):
        self.clear_frame()

        png_path = resource_path("icon.png")
        if os.path.exists(png_path):
            img = Image.open(png_path).resize((80, 80), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(self.container, image=self.logo_img, bg="#2d2d2d").pack(pady=(10, 20))

        self.header("Welcome to PlexRPC")
        tk.Label(self.container,
                 text="Sync your Plex status to Discord automatically.\nClick below to link your account.",
                 bg="#2d2d2d", fg="#cccccc", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=10)

        btn = tk.Button(self.container, text="Login with Plex", command=self.start_login_flow, bg="#e5a00d", fg="white",
                        font=("Segoe UI", 11, "bold"), padx=30, pady=10, relief="flat", cursor="hand2")
        btn.pack(pady=20)
        self.status_lbl = self.status("Waiting for action...")

    def start_login_flow(self):
        self.status_lbl.config(text="Connecting to Plex.tv...")
        threading.Thread(target=self._login_thread, daemon=True).start()

    def _login_thread(self):
        try:
            headers = {'X-Plex-Client-Identifier': self.client_id, 'X-Plex-Product': APP_NAME,
                       'Accept': 'application/json'}
            pin = requests.post('https://plex.tv/api/v2/pins?strong=true', headers=headers).json()

            auth_url = f"https://app.plex.tv/auth#?clientID={self.client_id}&code={pin['code']}&context%5Bdevice%5D%5Bproduct%5D={APP_NAME}"
            webbrowser.open(auth_url)

            self.container.after(0, lambda: self.status_lbl.config(text="Browser opened. Waiting for approval..."))

            token = None
            for _ in range(60):
                try:
                    check = requests.get(f"https://plex.tv/api/v2/pins/{pin['id']}", headers=headers).json()
                    if check.get('authToken'):
                        token = check['authToken']
                        break
                except:
                    pass
                time.sleep(1)

            if token:
                self.data['plex_token'] = token
                self.container.after(0, self.show_server_step)
            else:
                self.container.after(0, lambda: messagebox.showerror("Error", "Login timed out.", parent=self))
                self.container.after(0, self.show_login_step)
        except:
            self.container.after(0, lambda: messagebox.showerror("Error", "Network error.", parent=self))

    # STEP 2: SERVER
    def show_server_step(self):
        self.clear_frame()
        self.header("Select Server")
        self.status_lbl = self.status("Fetching server list...")

        self.lb = tk.Listbox(self.container, bg="#3d3d3d", fg="white", selectbackground="#e5a00d",
                             font=("Segoe UI", 10), bd=0, highlightthickness=0)
        self.lb.pack(expand=True, fill="both", padx=10)

        self.servers_cache = []
        threading.Thread(target=self._fetch_servers, daemon=True).start()

    def _fetch_servers(self):
        try:
            headers = {'X-Plex-Token': self.data['plex_token'], 'X-Plex-Client-Identifier': self.client_id,
                       'Accept': 'application/json'}
            resources = requests.get("https://plex.tv/api/v2/resources?includeHttps=1&includeRelay=1",
                                     headers=headers).json()
            self.servers_cache = [r for r in resources if r['product'] == 'Plex Media Server']
            self.container.after(0, self._populate_servers)
        except:
            self.container.after(0, lambda: self.status_lbl.config(text="Failed to fetch servers."))

    def _populate_servers(self):
        self.lb.delete(0, tk.END)
        for s in self.servers_cache: self.lb.insert(tk.END, s['name'])
        self.status_lbl.config(text="Select a server to continue.")
        self.lb.bind('<<ListboxSelect>>', self._on_server_select)

    def _on_server_select(self, event):
        sel = self.lb.curselection()
        if not sel: return
        server = self.servers_cache[sel[0]]
        self.data['server_name'] = server['name']
        self.status_lbl.config(text=f"Connecting to {server['name']}...")
        threading.Thread(target=self._connect_server, args=(server,), daemon=True).start()

    def _connect_server(self, server_data):
        best_uri = None
        headers = {'X-Plex-Token': self.data['plex_token'], 'X-Plex-Client-Identifier': self.client_id}
        for conn in server_data.get('connections', []):
            try:
                requests.get(f"{conn['uri']}/identity", headers=headers, timeout=2)
                best_uri = conn['uri']
                break
            except:
                continue

        if best_uri:
            self.data['base_url'] = best_uri
            self.plex_instance = PlexServer(best_uri, self.data['plex_token'])
            self.container.after(0, self.show_user_step)
        else:
            self.container.after(0, lambda: messagebox.showerror("Error", "Could not connect to this server.",
                                                                 parent=self))

    # STEP 3: USER
    def show_user_step(self):
        self.clear_frame()
        self.header("Who are you?")
        self.status_lbl = self.status("Loading profiles...")

        self.lb = tk.Listbox(self.container, bg="#3d3d3d", fg="white", selectbackground="#e5a00d",
                             font=("Segoe UI", 10), bd=0, highlightthickness=0)
        self.lb.pack(expand=True, fill="both", padx=10)
        self.lb.bind('<<ListboxSelect>>', self._on_user_select)

        threading.Thread(target=self._fetch_users, daemon=True).start()

    def _fetch_users(self):
        try:
            account = self.plex_instance.myPlexAccount()
            users = [account.username]
            try:
                home = account.users()
                if home: users.extend([u.title for u in home])
            except:
                pass
            self.container.after(0, lambda: self._populate_list(users))
        except:
            pass

    def _populate_list(self, items):
        self.items_cache = items
        for i in items: self.lb.insert(tk.END, i)
        self.status_lbl.config(text="Select the profile to track.")

    def _on_user_select(self, event):
        sel = self.lb.curselection()
        if not sel: return
        self.data['user_filter'] = self.items_cache[sel[0]]
        self.show_library_step()

    # STEP 4: LIBRARIES
    def show_library_step(self):
        self.clear_frame()
        self.header("Audiobooks")
        self.status("Select libraries that contain Audiobooks (Optional)")

        canvas = tk.Canvas(self.container, bg="#2d2d2d", highlightthickness=0)
        sb = tk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg="#2d2d2d")

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)

        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        sb.pack(side=tk.RIGHT, fill="y")

        self.lib_vars = []
        for section in self.plex_instance.library.sections():
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame, text=section.title, variable=var, bg="#2d2d2d", fg="white",
                                 selectcolor="#2d2d2d", activebackground="#2d2d2d", activeforeground="white",
                                 font=("Segoe UI", 10))
            chk.pack(anchor="w", pady=2)
            self.lib_vars.append((section.title, var))

        btn = tk.Button(self, text="Finish Setup", command=self.finish, bg="#e5a00d", fg="white",
                        font=("Segoe UI", 10, "bold"), padx=20, pady=10)
        btn.pack(side=tk.BOTTOM, fill=tk.X)

    def finish(self):
        audiobooks = [name for name, var in self.lib_vars if var.get()]
        self.data['audiobook_libraries'] = audiobooks
        save_session(self.data)
        messagebox.showinfo("Success", "Setup Complete! The app will now minimize to the tray.", parent=self)
        self.destroy()

    # --- MAIN ---


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not load_session():
    app = SetupWizard()
    app.mainloop()

session = load_session()
if not session: sys.exit(0)

try:
    logging.info(f"Starting {APP_NAME}...")
    plex = PlexServer(session['base_url'], session['plex_token'])
    d_id = requests.get(f"{API_URL}/api/config/discord-id").json()['client_id']
    RPC = Presence(d_id)
    RPC.connect()
except Exception as e:
    root = tk.Tk();
    root.withdraw()
    messagebox.showerror("Error", f"Startup failed: {e}\nTry deleting session.json.")
    sys.exit(1)


# --- ENGINE ---
def get_activity():
    try:
        sessions = plex.sessions()
        if not sessions: return None
        current = next((s for s in sessions if session['user_filter'].lower() in [u.lower() for u in s.usernames]),
                       None)
        if not current: return None

        status = {"details": current.title, "state": "Playing", "large_image": "plex_logo",
                  "small_image": "playing_icon",
                  "buttons": [{"label": "Get PlexRPC", "url": "https://github.com/malvinarum/Plex-Rich-Presence"}]}

        if hasattr(current, 'viewOffset'):
            status['start'] = time.time() - (current.viewOffset / 1000)
            status['end'] = status['start'] + (current.duration / 1000)

        q, type_ = current.title, 'movie'
        if current.type == 'episode':
            q, type_ = current.grandparentTitle, 'tv'
            status['details'] = current.grandparentTitle
            status['state'] = f"S{current.parentIndex:02d}E{current.index:02d} - {current.title}"
        elif current.type == 'track':
            status['state'] = f"by {current.originalTitle or current.grandparentTitle}"
            if current.librarySectionTitle in session['audiobook_libraries']:
                q, type_ = f"{current.title} {current.originalTitle}", 'book'
            else:
                status['large_image'] = "music_icon"
                q = None

        if q:
            try:
                res = requests.get(f"{API_URL}/api/metadata/{type_}", params={'q': q}, timeout=3).json()
                if res.get('found'):
                    status['large_image'] = res['image']
                    if res.get('url'): status['buttons'].append({"label": "View Details", "url": res['url']})
            except:
                pass

        return status
    except:
        return None


def update_tray_status(text):
    if TRAY_ICON: TRAY_ICON.title = f"PlexRPC: {text}"


def loop():
    while RUNNING:
        act = get_activity()
        if act:
            update_tray_status(f"Playing {act['details']}")
            try:
                RPC.update(details=act['details'], state=act['state'], large_image=act['large_image'],
                           small_image=act['small_image'], start=act.get('start'), end=act.get('end'),
                           buttons=act['buttons'])
            except:
                pass
        else:
            update_tray_status("Idle")
            try:
                RPC.clear()
            except:
                pass
        time.sleep(15)


def on_quit(icon, item):
    global RUNNING
    RUNNING = False
    icon.stop()


t = threading.Thread(target=loop)
t.start()

# --- TRAY ICON ---
img = Image.new('RGB', (64, 64), "black")
ImageDraw.Draw(img).rectangle((16, 16, 48, 48), fill="#e5a00d")

icon_path = resource_path("icon.png")
if not os.path.exists(icon_path): icon_path = resource_path("icon.ico")
if os.path.exists(icon_path): img = Image.open(icon_path)

TRAY_ICON = pystray.Icon("PlexRPC", img, "PlexRPC: Initializing...", pystray.Menu(
    pystray.MenuItem('Quit', on_quit)
))
TRAY_ICON.run()
