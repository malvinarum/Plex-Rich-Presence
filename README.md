# PlexRPC - Advanced Discord Rich Presence for Plex

<img src="https://raw.githubusercontent.com/malvinarum/Plex-Rich-Presence/refs/heads/main/icon.png" width="300"> 

**PlexRPC** is a modern, lightweight, and user-friendly application that syncs your Plex media status to your Discord profile. 

Unlike other scripts that require editing complex JSON config files, PlexRPC features a **Unified Setup Wizard** that handles everything for you—from logging in to selecting your specific user profile.

## 🌟 Key Features (v1.2)

* **🧙‍♂️ Unified Setup Wizard:** A beautiful, guided GUI walks you through Login, Server Selection, User Profile, and Library setup. No text files required!
* **🔒 Secure & Private:** Uses Plex OAuth for secure login. Your password never touches our app.
* **☁️ Cloud Metadata API:** Powered by a custom backend to fetch high-quality covers from TMDB (Movies/TV) and Google Books (Audiobooks)
* **🎧 Audiobook Support:** Automatically detects audiobook libraries and fetches book covers and author details instead of generic Plex metadata.
* **👥 Multi-User Support:** Works perfectly with Plex Home / Managed Users. You pick exactly which profile to track.
* **🚀 "Pro" Architecture:** Runs silently in the System Tray with live status tooltips. Configuration is safely stored in your `%APPDATA%` folder.

## 📥 Installation

1.  Download the latest **`PlexRPC.exe`** from the [Releases Page](https://github.com/malvinarum/Plex-Rich-Presence/releases).
2.  Double-click to run.
3.  Follow the on-screen **Setup Wizard**:
    * **Login:** A browser window will open to link your Plex account.
    * **Server:** Choose which Plex Media Server to track.
    * **User:** Select your specific user profile (great for shared family servers).
    * **Libraries:** (Optional) Check any libraries that contain Audiobooks.
4.  **Done!** The app will minimize to your system tray and start updating your Discord status.

## 🛠️ Troubleshooting

**"I want to reset my settings"**
* Since v1.2, settings are stored in your Windows AppData folder.
* To reset, simply **delete** the file: `C:\Users\%USERNAME%\AppData\Roaming\PlexRPC\session.json`
* Restart the app, and the wizard will reappear.

**"It says Idle when I'm playing something"**
* This usually means you selected the wrong **User Profile** during setup.
* If your server has "Malvin" (Admin) and "Kids" (Managed User), make sure you select the one you actually watch on.

## 🧑‍💻 Development

If you want to run from source or build it yourself:

1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/malvinarum/Plex-Rich-Presence.git](https://github.com/malvinarum/Plex-Rich-Presence.git)
    cd Plex-Rich-Presence
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run locally:**
    ```bash
    python main.py
    ```

4.  **Build .exe (PyInstaller):**
    ```bash
    pyinstaller --noconsole --onefile --clean --name "PlexRPC" --icon="icon.ico" --add-data "icon.png;." --add-data "icon.ico;." main.py
    ```

## 📜 License

This project is open-source. Feel free to fork, modify, and distribute.
