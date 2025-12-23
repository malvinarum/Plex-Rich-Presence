# PlexRPC - Advanced Discord Rich Presence for Plex

<img src="https://raw.githubusercontent.com/malvinarum/Plex-Rich-Presence/refs/heads/main/assets/icon.png" width="300"> 

![Version](https://img.shields.io/badge/version-v2.0-blue?style=for-the-badge&color=e5a00d)
![Downloads](https://img.shields.io/github/downloads/malvinarum/Plex-Rich-Presence/total?style=for-the-badge&color=2d2d2d)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=for-the-badge)

**PlexRPC** is a modern, lightweight, and user-friendly application that syncs your Plex media status to your Discord profile. 

Unlike other scripts that require editing complex JSON config files, PlexRPC features a **Unified Setup Wizard** that handles everything for you—from secure login to custom library settings.

## 🌟 New in v2.0

* **🎵 Music Support:** Now fully supports Plex Music! It automatically identifies tracks and fetches high-res album art and "Listen on Spotify" buttons via the Spotify API.
* **Easy Config Reset:** No more digging trough %appdata% folder to reset your config. Added easy "Reset Config" option to the system tray.

## ✨ Key Features

* **🧙‍♂️ Configless Setup:** A guided GUI walks you through linking your account, selecting your server, and picking your user profile.
* **☁️ Cloud Metadata API:** Powered by a custom backend to fetch high-quality covers from **TMDB** (Movies/TV), **Google Books** (Audiobooks), and **Spotify** (Music).
* **🎧 Audiobook Recognition:** Smartly detects audiobook libraries to display book covers and author details instead of generic placeholders.
* **👥 Multi-User Support:** Works perfectly with Plex Home / Managed Users. You pick exactly which profile to track (great for shared family servers).
* **🚀 "Pro" Architecture:** Runs silently in the System Tray. Configuration is safely stored in your `%APPDATA%` folder.

## 📥 Installation

1.  Download the latest **`PlexRPC.exe`** from the [Releases Page](https://github.com/malvinarum/Plex-Rich-Presence/releases).
2.  Double-click to run.
3.  Follow the **Setup Wizard**:
    * **Login:** A browser window will open. Click "Approve" to link your account securely.
    * **Server:** Choose which Plex Media Server to track.
    * **User:** Select your specific user profile.
    * **Libraries:** (Optional) Check any libraries that contain Audiobooks for enhanced metadata.
4.  **Done!** The app will minimize to your system tray and start updating your Discord status.

## App Screenshots
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/1bda1a28-08d3-45ee-88ba-da44da98875b" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/04ededdd-e8f0-43b5-b3a2-d040c6a3aea3" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/fa99768e-8904-41f2-92b4-6384a8d8bc2c" />
<img width="502" height="582" alt="image" src="https://github.com/user-attachments/assets/bda61806-d74a-4f27-aab7-f4fe06638672" />

## Rich Presence Screenshots
<img width="275" height="200" alt="image" src="https://github.com/user-attachments/assets/6b743d99-dc94-44ee-996b-0d592bcfc2d5" />
<img width="275" height="200" alt="image" src="https://github.com/user-attachments/assets/ee653503-4619-4a64-a653-f3fd49bb26f2" />
<img width="275" height="200" alt="image" src="https://github.com/user-attachments/assets/ab754a74-22ff-4b20-b28d-1972b1bb3bb8" />
<img width="275" height="200" alt="image" src="https://github.com/user-attachments/assets/94cabda1-08c0-40f7-8281-afab8e387b60" />


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
    git clone [https://github.com/malvinarum/Plex-Rich-Presence.git](https://github.com/malvinarum/Plex-Rich-Presence.git)
    cd Plex-Rich-Presence
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup backend (If you want to use your own api):**
https://github.com/malvinarum/plexrpc-api

4.  **Run locally:**
    ```bash
    python main.py
    ```

5.  **Build .exe (PyInstaller):**
    ```bash
    pyinstaller --noconsole --onefile --icon=assets/icon.ico --name=PlexRPC --add-data "assets;assets" main.py
    ```

## 📜 License

This project is open-source. Feel free to fork, modify, and distribute.
