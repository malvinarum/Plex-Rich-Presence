# PlexRPC - Advanced Discord Rich Presence for Plex

<img src="https://raw.githubusercontent.com/malvinarum/Plex-Rich-Presence/refs/heads/main/assets/icon.png" width="300"> 

![Version](https://img.shields.io/badge/version-v2.2-blue?style=for-the-badge&color=e5a00d)
![Downloads](https://img.shields.io/github/downloads/malvinarum/Plex-Rich-Presence/total?style=for-the-badge&color=2d2d2d)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=for-the-badge)

<a href="https://github.com/sponsors/malvinarum">
  <img src="https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?style=for-the-badge&logo=github&logoColor=white" alt="Sponsor on GitHub" />
</a>
<a href="https://www.buymeacoffee.com/malvinarum">
  <img src="https://img.shields.io/badge/Buy_Me_A_Coffee-Donate-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me A Coffee" />
</a>

---

**PlexRPC** is a modern, lightweight, and user-friendly application that syncs your Plex media status to your Discord profile. 

Unlike other scripts that require editing complex JSON config files, PlexRPC features a **Unified Setup Wizard** that handles everything for you—from secure login to custom library settings.

## ✨ New in v2.3

The latest update brings major stability improvements and user-requested features:

* **👻 Privacy Mode:** Temporarily pause your Rich Presence directly from the system tray without closing the app. Perfect for when you want some privacy.
* **🟢 Dynamic Status Icons:** The system tray icon now changes color to reflect your status instantly:
  * 🟢 **Green:** Playing
  * 🔵 **Blue:** Paused
  * ⚪ **Grey:** Privacy Mode (Paused Presence)
  * 🟠 **Orange:** Idle (No active session)
  * 🔴 **Red:** Connection Error
* **🛠️ Robust Reset:** The "Reset Config" option has been completely rewritten to prevent freezing.
* **🧹 Auto-Maintenance & Better logging:** Auto-Maintenance & Better Logs: On launch, the app automatically cleans up bloated log files ('app.log') to save space. I've also refined the logging system to cut out the noise while preserving critical debug info.
* **🆔 Identity Fix:** Improved user matching ensures the app grabs the correct session even if your "Friendly Name" differs from your username.
* **🎵 Enhanced Metadata:** Music now correctly displays "by Artist" on the second line and the **Album Name** in the hover text and 3rd line.

## ✨ Key Features

* **🧙‍♂️ Configless Setup:** A guided GUI walks you through linking your account, selecting your server, and picking your user profile.
* **☁️ Cloud Metadata API:** Powered by a custom backend to fetch high-quality covers from **TMDB** (Movies/TV), **Google Books** (Audiobooks), and **Spotify** (Music).
* **🎧 Audiobook Recognition:** Smartly detects audiobook libraries to display book covers and author details instead of generic placeholders.
* **👥 Multi-User Support:** Works perfectly with Plex Home / Managed Users. You pick exactly which profile to track (great for shared family servers).
* **🛡️ Silent & Secure:** Runs silently in the System Tray with secure API headers.
* **🚀 Run on Startup:** A true "set and forget" experience. You can now toggle **Run on Startup** directly from the System Tray menu.
* **⏯️ Smart Pause Detection:** The app now detects when you pause your media. It updates your status text to "(Paused)" and hides the progress bar so your timer doesn't drift.
* **👀 Dynamic Activity Status:** Discord now correctly displays **"Watching Plex"** for movies/series and **"Listening to Plex"** for music/audiobooks.
* **📊 Universal Progress Bar:** Added beautiful progress bars for Video content, Music tracks and Audiobooks.


## 📥 Installation

1.  Download the latest **`PlexRPC.exe`** from the [Releases Page](https://github.com/malvinarum/Plex-Rich-Presence/releases).
2.  Double-click to run.
3.  Follow the **Setup Wizard**:
    * **Login:** A browser window will open. Click "Approve" to link your account securely.
    * **Server:** Choose which Plex Media Server to track.
    * **User:** Select your specific user profile.
    * **Libraries:** (Optional) Check any libraries that contain Audiobooks for enhanced metadata.
4.  **Done!** The app will minimize to your system tray. 
5.  *(Optional)* Right-click the tray icon and check **"Run on Startup"** to have it launch automatically with Windows.

## App Screenshots
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/e0836bc7-03d5-4d0e-b181-086ab2312d5a" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/04ededdd-e8f0-43b5-b3a2-d040c6a3aea3" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/fa99768e-8904-41f2-92b4-6384a8d8bc2c" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/bda61806-d74a-4f27-aab7-f4fe06638672" />

## Rich Presence Screenshots
**TV Series**\
<img width="315" height="207" alt="image" src="https://github.com/user-attachments/assets/73ec1730-3e4c-4166-b4b1-1ad497e4b9ac" />\
**Movies**\
<img width="315" height="207" alt="image" src="https://github.com/user-attachments/assets/b15c1efa-8a65-486f-bb4f-300c7b142585" />\
**Music**\
<img width="315" height="207" alt="image" src="https://github.com/user-attachments/assets/09150d49-e6c6-4a25-bfe5-8b39e6283c2c" />\
**Audiobook**\
<img width="315" height="207" alt="image" src="https://github.com/user-attachments/assets/29122f9c-fd88-41ff-8a4e-9c435d1c2994" />


## 🛠️ Troubleshooting

**"I want to reset my settings"**
* **Option 1 (Easiest):** Right-click the PlexRPC icon in your System Tray and select **Reset Config**.
* **Option 2 (Manual):** Delete the file: `C:\Users\%USERNAME%\AppData\Roaming\PlexRPC\config.json`

**"It says Idle when I'm playing something"**
* This usually means you selected the wrong **User Profile** during setup.
* If your server has "Admin" and "Kids", make sure you select the one you actually watch on.

## 🧑‍💻 Development

If you want to run from source or build it yourself:

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/malvinarum/Plex-Rich-Presence.git
    cd Plex-Rich-Presence
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup backend (If you want to use your own API):**
    * **[PlexRPC API](https://github.com/malvinarum/plexrpc-api)** (Node.js)
    * **[PlexRPC API - Serverless](https://github.com/malvinarum/PlexRPC-API-Cloudflare-Worker)** (Cloudflare Worker - Recommended)

4.  **Run locally:**
    ```bash
    python main.py
    ```

5.  **Build .exe (PyInstaller):**
    If you want to build the standalone executable, use the provided spec file:
    ```bash
    pyinstaller PlexRPC.spec
    ```
    *(Or manually: `pyinstaller --noconsole --onefile --icon=assets/icon.ico --name=PlexRPC --add-data "assets;assets" main.py`)*

## 📜 License

This project is open-source. Feel free to fork, modify, and distribute.

## Disclaimer

**PlexRPC** is a community-developed, open-source project. It is **not** affiliated, associated, authorized, endorsed by, or in any way officially connected with **Plex, Inc.**, **Discord Inc.**, or any of their subsidiaries or affiliates.

* The official Plex website can be found at [https://www.plex.tv](https://www.plex.tv).
* The official Discord website can be found at [https://discord.com](https://discord.com).

The names "Plex", "Discord", as well as related names, marks, emblems, and images are registered trademarks of their respective owners. This application is intended for personal, non-commercial use only.
