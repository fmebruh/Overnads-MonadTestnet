"""
Overnads Game Bot - Terminal-Only Version

This script automates playing games on Overnads to earn points and items.
It's designed to run entirely within a terminal, providing clear, color-coded
feedback on its progress and any issues encountered.

Prerequisites:
- Python 3.7+
- 'requests' library (`pip install requests`)
- A 'config.json' file in the same directory.
"""
import requests
import time
import json
import random
import re
import sys

# --- 1. Terminal Output Configuration ---
class C:
    """Color constants for terminal output."""
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_info(message):
    print(f"{C.BLUE}[INFO]{C.END} {message}")

def print_success(message):
    print(f"{C.GREEN}[SUCCESS]{C.END} {message}")

def print_warning(message):
    print(f"{C.YELLOW}[WARNING]{C.END} {message}")

def print_error(message):
    print(f"{C.RED}[ERROR]{C.END} {message}")


# --- 2. Configuration & Global State ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    AUTH_TOKEN = config['auth_token']
    USER_AGENTS = config.get('user_agents', [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ])
except FileNotFoundError:
    print_error("FATAL: `config.json` not found. Please create it by renaming `config.json.example`.")
    sys.exit(1)
except KeyError:
    print_error("FATAL: `auth_token` not found in `config.json`.")
    print_info("Make sure the key 'auth_token' exists in your config file.")
    sys.exit(1)
except json.JSONDecodeError:
    print_error("FATAL: `config.json` is not formatted correctly. Please ensure it's valid JSON.")
    sys.exit(1)


API = {
    "user_profile": "https://app.overnads.xyz/api/auth/me",
    "game_start": "https://app.overnads.xyz/api/game/start",
    "game_end": "https://app.overnads.xyz/api/game/end",
}

session = requests.Session()


# --- 3. Helper Functions ---
def get_headers():
    """Constructs request headers with a random User-Agent."""
    return {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Authorization': AUTH_TOKEN,
        'Content-Type': 'application/json',
        'Origin': 'https://app.overnads.xyz',
        'Referer': 'https://app.overnads.xyz/',
        'User-Agent': random.choice(USER_AGENTS)
    }

def send_request(method, url, payload=None, retries=3, backoff=3):
    """Sends a request with automatic retries and robust error handling."""
    for attempt in range(retries):
        try:
            headers = get_headers()
            response = session.request(method, url, headers=headers, json=payload, timeout=25)

            if response.status_code == 401:
                print_error("CRITICAL: Auth token is expired or invalid. Please get a new one. Stopping.")
                sys.exit(1)

            if response.status_code < 500:
                return response

            print_warning(f"Server error ({response.status_code}). Retrying in {backoff}s... ({attempt + 1}/{retries})")

        except requests.exceptions.RequestException as e:
            print_warning(f"Network error: {e}. Retrying in {backoff}s... ({attempt + 1}/{retries})")

        time.sleep(backoff)

    print_error(f"Request failed after {retries} retries for URL: {url}")
    return None

# --- 4. Core Bot Logic ---
def fetch_account_stats():
    """Fetches and returns the user's account statistics."""
    print_info("Fetching account stats...")
    response = send_request("GET", API['user_profile'])
    if response and response.status_code == 200:
        try:
            stats = response.json()
            print_success(f"Stats updated: {C.BOLD}{stats.get('overPoints', 0)} Points, {stats.get('coins', 0)} Coins, {stats.get('tickets', 0)} Tickets{C.END}")
            return stats
        except json.JSONDecodeError:
            print_error("Failed to parse account stats from server response.")
            return None
    else:
        print_error("Could not fetch account stats.")
        return None

def handle_stuck_game(error_response_text):
    """Parses a stuck game ID from an error message and attempts to end it."""
    match = re.search(r'Game ID: ([a-f0-9\-]+)', error_response_text)
    if not match:
        print_error("Could not parse stuck game ID from error message. Cannot resolve.")
        return False

    stuck_game_id = match.group(1)
    print_warning(f"Attempting to clear stuck game ID: {stuck_game_id}")

    end_payload = {
        "gameId": stuck_game_id,
        "overPoints": random.randint(90, 110),
        "collectedItems": []
    }
    end_response = send_request("POST", API['game_end'], payload=end_payload)

    if end_response and end_response.status_code in [200, 201]:
        print_success("Successfully cleared stuck game.")
        return True
    else:
        err_text = end_response.text if end_response else "No Response"
        print_error(f"Failed to clear stuck game. Server responded with: {err_text}")
        return False

def play_all_games(tickets_available):
    """Main game-playing loop that iterates through all available tickets."""
    if tickets_available == 0:
        print_info("No game tickets available to play.")
        return

    print_info(f"Starting game sequence for {C.BOLD}{tickets_available}{C.END} tickets...")
    
    for i in range(tickets_available):
        print(f"\n{C.PURPLE}--- Playing Ticket {i + 1} of {tickets_available} ---{C.END}")

        start_response = send_request("POST", API['game_start'])

        if start_response and start_response.status_code == 400 and "active game" in start_response.text:
            print_warning("Stuck game detected. Initiating self-healing.")
            if handle_stuck_game(start_response.text):
                print_info("Self-heal successful. Waiting 10s before retrying...")
                time.sleep(10)
                start_response = send_request("POST", API['game_start'])
            else:
                print_error("Self-heal failed. Skipping this ticket.")
                continue

        if start_response and start_response.status_code in [200, 201]:
            print_info("Game started. Simulating gameplay for 30 seconds...")
            time.sleep(30)

            points = random.randint(90, 110)
            collected_items = [
                {"type": "coin", "count": random.randint(1, 4)},
                {"type": "ticket", "count": random.randint(0, 4)}
            ]
            end_payload = {"overPoints": points, "collectedItems": collected_items}

            print_info(f"Ending game. Submitting {points} points and items.")
            send_request("POST", API['game_end'], payload=end_payload)
            print_success("Game finished successfully.")
        else:
            err_text = start_response.text if start_response else "No Response"
            status_code = start_response.status_code if start_response else 'N/A'
            print_error(f"Could not start game. Status: {status_code}, Message: {err_text}")
            print_warning("Skipping ticket.")
            continue

        if i < tickets_available - 1:
            sleep_duration = random.randint(15, 25)
            print_info(f"Waiting {sleep_duration}s before next game...")
            time.sleep(sleep_duration)

    print_success(f"\nGame playing sequence finished.")

def print_summary(initial_stats, final_stats):
    """Prints a formatted summary of the bot's run."""
    print(f"\n{C.BOLD}{C.PURPLE}================== Run Summary =================={C.END}")
    if not initial_stats or not final_stats:
        print_warning("Could not generate a full summary due to missing stats.")
        return

    points_gain = final_stats.get('overPoints', 0) - initial_stats.get('overPoints', 0)
    coins_gain = final_stats.get('coins', 0) - initial_stats.get('coins', 0)
    tickets_gain = final_stats.get('tickets', 0) - initial_stats.get('tickets', 0)

    print(f"               {C.BOLD}{'Initial':<10} {'Final':<10} {'Gained':<10}{C.END}")
    print("-" * 51)
    print(f"🏅 Points:      {initial_stats.get('overPoints', 0):<10} {final_stats.get('overPoints', 0):<10} {C.GREEN}{'+' if points_gain >= 0 else ''}{points_gain}{C.END}")
    print(f"🪙 Coins:       {initial_stats.get('coins', 0):<10} {final_stats.get('coins', 0):<10} {C.GREEN}{'+' if coins_gain >= 0 else ''}{coins_gain}{C.END}")
    print(f"🎟️ Tickets:     {initial_stats.get('tickets', 0):<10} {final_stats.get('tickets', 0):<10} {C.GREEN if tickets_gain >= 0 else C.RED}{'+' if tickets_gain >= 0 else ''}{tickets_gain}{C.END}")
    print(f"{C.BOLD}{C.PURPLE}==================================================={C.END}")

# --- 5. Main Execution ---
def main():
    """Main function to orchestrate the bot's execution."""
    print(f"\n{C.BOLD}--- Overnads Game-Only Bot Started ---{C.END}")
    
    initial_stats = fetch_account_stats()
    if not initial_stats:
        print_error("Could not fetch initial stats. Please check your token and network. Stopping.")
        sys.exit(1)

    print_info(f"Welcome, {C.BOLD}{initial_stats.get('username', 'User')}{C.END}!")
    
    tickets_to_play = initial_stats.get('tickets', 0)
    play_all_games(tickets_to_play)

    print_info("All tasks for this run are complete. Fetching final stats...")
    time.sleep(5) 
    final_stats = fetch_account_stats()

    print_summary(initial_stats, final_stats)
    print(f"\n{C.BOLD}--- Script finished. ---{C.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Interrupted by user. Shutting down gracefully...{C.END}")
        sys.exit(0)
