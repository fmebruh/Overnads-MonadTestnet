import requests
import time
import json
import logging
import random
import re

# --- 1. Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# --- 2. Configuration & Global State ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    AUTH_TOKEN = config['auth_token']
    TELEGRAM_TOKEN = config.get('telegram_bot_token')
    TELEGRAM_CHAT_ID = config.get('telegram_chat_id')
    USER_AGENTS = config.get('user_agents', ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"])
except Exception as e:
    logging.error(f"FATAL: Could not load config.json. Make sure it exists and is correctly formatted. Error: {e}")
    exit()

API = {
    "user_profile": "https://app.overnads.xyz/api/auth/me",
    "game_start": "https://app.overnads.xyz/api/game/start",
    "game_end": "https://app.overnads.xyz/api/game/end",
    "game_cancel": "https://app.overnads.xyz/api/game/cancel"
}
account_stats = {}

# --- 3. Helper Functions ---
def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")

def get_headers():
    return {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': AUTH_TOKEN,
        'content-type': 'application/json',
        'origin': 'https://app.overnads.xyz',
        'priority': 'u=1, i',
        'referer': 'https://app.overnads.xyz/home',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': random.choice(USER_AGENTS)
    }

def send_request_with_retry(url, method="POST", payload=None, retries=3, backoff_factor=3):
    for i in range(retries):
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=get_headers(), json=payload, timeout=25)
            else:
                response = requests.get(url, headers=get_headers(), timeout=25)

            if response.status_code == 401:
                logging.error("CRITICAL: Auth token is expired or invalid. Please get a new one.")
                send_telegram_message("🔴 **CRITICAL ERROR** 🔴\nYour `auth_token` has expired! The bot is stopping. Please get a new token.")
                exit()

            if response.status_code < 500:
                return response

            logging.warning(f"Server error ({response.status_code}). Retrying in {backoff_factor * (i + 1)}s...")
            time.sleep(backoff_factor * (i + 1))

        except requests.exceptions.RequestException as e:
            logging.error(f"A network exception occurred: {e}. Retrying in {backoff_factor * (i + 1)}s...")
            time.sleep(backoff_factor * (i + 1))
            
    logging.error(f"Request failed after {retries} retries for URL: {url}")
    return None

# --- 4. Core Bot Logic ---
def fetch_account_stats():
    global account_stats
    logging.info("Fetching account stats...")
    response = send_request_with_retry(API['user_profile'], method="GET")
    if response and response.status_code == 200:
        account_stats = response.json()
        logging.info(f"Stats updated: {account_stats.get('overPoints', 0)} Points, {account_stats.get('coins', 0)} Coins, {account_stats.get('tickets', 0)} Tickets")
        return True
    return False

def handle_stuck_game(error_response):
    try:
        error_json = error_response.json()
        error_message = error_json.get("error", "")
        stuck_game_id_match = re.search(r'Game ID: ([a-f0-9\-]+)', error_message)
        
        if stuck_game_id_match:
            stuck_game_id = stuck_game_id_match.group(1)
            logging.info(f"Found stuck game ID: {stuck_game_id}. Sending end request to clear it.")
            
            end_payload = {
                "gameId": stuck_game_id,
                "overPoints": random.randint(90, 110),
                "collectedItems": []
            }
            
            end_response = send_request_with_retry(API['game_end'], payload=end_payload)
            
            if end_response and end_response.status_code in [200, 201]:
                logging.info("Successfully cleared stuck game.")
                return True
            else:
                logging.error(f"Failed to clear stuck game. Server responded with: {end_response.text if end_response else 'No Response'}")
                return False
        else:
            logging.error("Could not parse stuck game ID. Cannot clear.")
            return False
    except json.JSONDecodeError:
        logging.error("Could not parse JSON from stuck game error response.")
        return False

def play_all_games():
    initial_tickets = account_stats.get('tickets', 0)
    if initial_tickets == 0:
        logging.info("No game tickets available to play.")
        return

    logging.info(f"Starting game sequence for {initial_tickets} tickets...")
    games_played_successfully = 0
    
    for i in range(initial_tickets):
        logging.info("\n" + "-"*50)
        logging.info(f"--- Attempting to use ticket {i + 1} of {initial_tickets} ---")
        
        start_response = send_request_with_retry(API['game_start'])
        
        # ** THE DEFINITIVE FIX: A resilient state machine for handling errors **
        
        # State 1: Check for stuck game
        if start_response and start_response.status_code == 400 and "You already have an active game" in start_response.text:
            logging.warning("Stuck game session detected. Attempting self-healing process...")
            send_telegram_message("⚠️ Stuck game session detected. Attempting to self-heal...")
            
            if handle_stuck_game(start_response):
                logging.info("Self-heal successful. Waiting 10s before retrying to start a new game...")
                time.sleep(10)
                start_response = send_request_with_retry(API['game_start']) # Retry starting
            else:
                logging.error("Self-heal failed. Skipping this ticket.")
                send_telegram_message("❌ Self-heal failed for one ticket. Continuing to the next.")
                continue # Skip to the next ticket

        # State 2: Check for successful start (either first try or after healing)
        if start_response and start_response.status_code in [200, 201]:
            logging.info("Successfully started game. Simulating gameplay for 30 seconds...")
            time.sleep(30)
            
            points = random.randint(90, 110)
            coins = random.randint(1, 4)
            tickets = random.randint(0, 4)
            collected_items = [{"type": "coin", "count": coins}, {"type": "ticket", "count": tickets}]
            
            end_payload = {"overPoints": points, "collectedItems": collected_items}
            
            logging.info(f"Ending game. Submitting payload: {end_payload}")
            send_request_with_retry(API['game_end'], payload=end_payload)
            games_played_successfully += 1
            
        # State 3: Handle any other failure
        else:
            if start_response is not None:
                logging.error(f"Could not start game for this ticket. Server responded with Status Code: {start_response.status_code} and Message: {start_response.text}")
            else:
                logging.error("Could not start game for this ticket. The request may have failed to send.")
            logging.warning("Skipping this ticket and continuing to the next.")
            send_telegram_message("❗️ Could not start a game for one ticket. Continuing...")

        # Wait before the next ticket is used
        if i < initial_tickets - 1:
            sleep_duration = random.randint(15, 20)
            logging.info(f"Waiting for {sleep_duration} seconds before using the next ticket...")
            time.sleep(sleep_duration)
            
    logging.info(f"Game playing sequence finished. Successfully played {games_played_successfully} games.")

# --- 5. Main Execution Loop ---
if __name__ == "__main__":
    logging.info("--- Overnads Game-Only Bot Started ---")
    send_telegram_message("🤖 **Overnads Bot Started (Game-Only Mode)**")

    if not fetch_account_stats():
        logging.error("Could not fetch initial stats. Please check your auth_token. Stopping.")
        exit()
    
    initial_message = (
        f"👋 Welcome, *{account_stats.get('username', 'N/A')}*!\n\n"
        f"**Starting Balance:**\n"
        f"🏅 Points: {account_stats.get('overPoints', 0)}\n"
        f"🪙 Coins: {account_stats.get('coins', 0)}\n"
        f"🎟️ Tickets: {account_stats.get('tickets', 0)}"
    )
    send_telegram_message(initial_message)
    
    play_all_games()
        
    logging.info("All tasks for this cycle are complete. Fetching final stats...")
    time.sleep(5)
    fetch_account_stats()
    
    summary_message = (
        f"✅ **Bot Run Complete** ✅\n\n"
        f"**Final Balance:**\n"
        f"🏅 Points: {account_stats.get('overPoints', 0)}\n"
        f"🪙 Coins: {account_stats.get('coins', 0)}\n"
        f"🎟️ Tickets: {account_stats.get('tickets', 0)}"
    )
    send_telegram_message(summary_message)
    
    logging.info("--- Script finished. ---")
