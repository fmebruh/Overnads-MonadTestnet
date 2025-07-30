# Overnads Game Bot (Terminal Version)

A clean, robust, and terminal-only Python bot to automate playing games on the Overnads platform. It's designed for simplicity and provides clear, real-time feedback on its progress.


## Features

- **Terminal-Only:** No external dependencies like Telegram. Runs entirely in your command line.
- **Color-Coded Logging:** Easily distinguish between informational messages, successes, warnings, and critical errors.
- **Robust Error Handling:** Automatically retries on network failures and includes a self-healing mechanism for "stuck" games.
- **Graceful Shutdown:** Safely stop the bot at any time by pressing `Ctrl+C`.
- **Detailed Session Summary:** See a clear report of your points, coins, and tickets gained at the end of each run.
- **Secure:** Uses a `.gitignore` file to prevent you from accidentally committing your secret authentication token.

## Setup & Installation

Follow these steps to get the bot up and running.

### 1. Prerequisites
- [Python 3.7+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads/) (for cloning the repository)

### 2. Clone the Repository
Open your terminal or command prompt and run:
```bash
git clone <repository_url>
cd overnads-bot
```
*(If not using Git, you can download the files and place them in a folder named `overnads-bot`)*

### 3. Set Up a Virtual Environment (Recommended)
This keeps the project's dependencies isolated.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
Install the required Python library from the `requirements.txt` file.
```bash
pip install -r requirements.txt
```

### 5. Configure the Bot
The bot needs your authentication token to work.

1.  Edit the `config.json`.
2.  Open `config.json` with a text editor.
3.  Replace `"Bearer YOUR_AUTHENTICATION_TOKEN_HERE"` with your actual token. **The `Bearer ` prefix is important!**

    To get your token:
    - Open your browser and log in to `app.overnads.xyz`.
    - Open the Developer Tools (usually `F12` or `Ctrl+Shift+I`).
    - Go to the "Network" tab.
    - Perform an action on the site, like clicking your profile.
    - Find a request to the `app.overnads.xyz/api/` endpoint.
    - Look for the "Request Headers" section and copy the entire value of the `Authorization` header.

## Usage

Once setup is complete, run the bot from your terminal:
```bash
python main.py
```

The bot will start, display your initial stats, play all available games, and then print a final summary before exiting.

## Disclaimer
This script is for educational purposes only. Automating interactions with websites may be against their Terms of Service. Use this script at your own risk. The author is not responsible for any consequences of its use.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
