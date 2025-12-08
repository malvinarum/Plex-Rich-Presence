# Plex Discord RPC 🎬

A lightweight tool that syncs your Plex status to Discord. It displays the movie, TV show, or audiobook you are currently enjoying on your Discord profile with rich metadata and cover art.

## 📸 Preview

![Plex Rich Presence Demo](https://s12.gifyu.com/images/bEw0W.png)

## ✨ Features

* **Zero Install:** Runs as a portable executable.
* **Rich Metadata:** Shows movie posters, episode titles, and progress bars.
* **Audiobook Support:** Detects audiobooks and fetches covers from Google Books.
* **Interactive Buttons:** Direct links to "View on TMDB" or "Get PlexRPC" right from your status.
* **Smart Idle:** Automatically clears your Discord status when you stop watching.

## 🚀 Setup Guide

### 1. Download & Prepare
1.  [Download Release](https://github.com/malvinarum/Plex-Rich-Presence/releases) `PlexRPC.exe` and `config.example.json` to a folder of your choice (e.g., `C:\PlexRPC`).
2.  **Crucial:** The `.exe` and `config.json` must be in the **same folder**.

### 2. Get Your Credentials
To make this work, you need to fill in `config.json`. Here is how to find the tricky values:

#### 🔑 How to get your Plex Token
1.  Open [Plex Web](https://app.plex.tv) in your browser.
2.  Click on any Movie or TV Episode in your library.
3.  Click the **Three Dots (⋮)** icon -> **Get Info**.
4.  At the bottom of the pop-up, click **View XML**.
5.  Look at the URL in your browser address bar. The token is the text at the very end:
    * `...&X-Plex-Token=YOUR_TOKEN_HERE`

#### 🤖 How to get a Discord App ID
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Click **New Application** -> Name it (e.g., "Plex").
3.  Copy the **Application ID** (Client ID).
4.  **Important:** Go to the "Rich Presence" -> "Art Assets" tab and upload two images named exactly:
    * `plex_logo` (Large generic image)
    * `playing_icon` (Small status icon)

### 3. Edit Configuration
1.  Rename `config.example.json` to `config.json` (or just run the app once, and it will create it for you).
2.  Open `config.json` with Notepad and paste your keys:

```json
{
    "discord": {
        "client_id": "PASTE_DISCORD_APP_ID_HERE"
    },
    "plex": {
        "base_url": "http://YOUR_PLEX_IP:32400",
        "token": "PASTE_PLEX_TOKEN_HERE",
        "user_filter": "", 
        "audiobook_libraries": ["Audiobooks", "Books"]
    },
    "tmdb": {
        "api_key": "PASTE_TMDB_API_KEY_HERE"
    },
    "google_books": {
        "api_key": "PASTE_GOOGLE_BOOKS_API_KEY_HERE"
    },
    "settings": {
        "update_interval": 15,
        "log_level": "INFO"
    }
}