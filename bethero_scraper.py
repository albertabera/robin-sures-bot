
import os
import time
import asyncio
import logging
import re
import sys
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # Load variables from .env

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Telegram dependencies
from telethon import TelegramClient
from telethon.sessions import StringSession

# Configuration
try:
    API_ID_raw = os.environ.get("API_ID", "")
    if not API_ID_raw:
        # Try to find it in the file content manually if dotenv failed or simple format error
        print("⚠️  API_ID is empty in environment. Checking .env content directly...")
    
    API_ID = int(API_ID_raw) if API_ID_raw else 0
    API_HASH = os.environ.get("API_HASH", "")
    SESSION = os.environ.get("TELEGRAM_STRING_SESSION", "")
    DEST_CHAT_ID = int(os.environ.get("DEST_CHAT_1", "0") or "0") # Default destination
    DEST_CHAT_2 = int(os.environ.get("DEST_CHAT_2", "0") or "0") # Second destination
except ValueError as e:
    print(f"❌ Configuration Error: Could not parse integers from .env. Check API_ID, DEST_CHAT_1/2. Details: {e}")
    API_ID = 0
    DEST_CHAT_ID = 0
    DEST_CHAT_2 = 0

if API_ID == 0 or not API_HASH or not SESSION:
    print("❌ ERROR: Missing credentials in .env file.")
    print("Please ensure .env contains: API_ID, API_HASH, TELEGRAM_STRING_SESSION")
    # Don't exit yet, let it crash or return in main

# Scraper Configuration
CHECK_INTERVAL = 10 # Seconds between checks
SEEN_BETS = set() # To store IDs of sent bets

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Database Integration ---
# Use absolute path to avoid confusion
DB_NAME = os.path.abspath("surebets.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS surebets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event TEXT,
                league TEXT,
                profit REAL,
                bookies_json TEXT, -- Stores JSON list of bookmakers/markets
                raw_id TEXT UNIQUE -- To prevent duplicates in DB if needed
            )
        ''')
        # Enable WAL mode for better concurrency (Scraper writing, Bot reading)
        cursor.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        conn.close()
        logger.info(f"✅ Database initialized at: {DB_NAME}")
        print(f"📂 DATABASE LOCATION: {DB_NAME}") # Print for user to see
    except Exception as e:
        logger.error(f"❌ Database error: {e}")

def save_bet_to_db(bet):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Serialize bookmakers info to JSON
        bookies_json = json.dumps(bet['bets'], ensure_ascii=False)
        
        # We use 'event' + 'profit' + 'first_bookie_odds' as a rough unique signature,
        # but here we rely on the main loop's SEEN_BETS to filter real-time dupes.
        # For the DB, we can just insert every "alert" we sent.
        
        cursor.execute('''
            INSERT INTO surebets (event, league, profit, bookies_json, raw_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (bet['event'], bet['league'], float(bet['profit']), bookies_json, f"{bet['event']}_{bet['profit']}_{datetime.now().timestamp()}"))
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Bet saved to database.")
    except Exception as e:
        logger.error(f"❌ Failed to save to DB: {e}")

async def send_to_telegram(client, chat_id, message):
    try:
        if chat_id == 0:
            logger.warning(f"Destination chat not set, cannot send message.")
            return
        await client.send_message(chat_id, message)
        logger.info(f"✅ Message sent to {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")

def get_sport_emoji(sport_text):
    s = sport_text.lower()
    if "basketball" in s or "baloncesto" in s or "nba" in s or "ncaa" in s or "euroleague" in s:
        return "🏀"
    if "soccer" in s or "football" in s or "fútbol" in s:
        return "⚽️"
    if "tennis" in s or "tenis" in s:
        return "🎾"
    return "🏆"

def parse_surebets(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('table[role="table"] tbody[role="rowgroup"] tr[role="row"]')
    
    new_bets = []
    logger.info(f"DEBUG: Parsing {len(rows)} rows...")
    
    for i, row in enumerate(rows):
        try:
            # 1. Profit
            profit_elem = row.select_one('td:nth-child(1) .text-green-500')
            if not profit_elem:
                logger.info(f"Row {i}: No profit element found. Skipping.")
                continue
            profit = profit_elem.get_text(strip=True).replace('%', '')
            
            # 2. Event & League
            event_td = row.select_one('td:nth-child(2)')
            if not event_td:
                logger.info(f"Row {i}: No event column. Skipping.")
                continue
                
            league = event_td.select_one('.line-clamp-1').get_text(strip=True) if event_td.select_one('.line-clamp-1') else "Unknown League"
            event_name = event_td.select_one('.font-bold').get_text(strip=True) if event_td.select_one('.font-bold') else "Unknown Event"
            
            # 3. Markets (Bets)
            market_td = row.select_one('td:nth-child(3)')
            markets = [div.get_text(strip=True) for div in market_td.select('.line-clamp-2')] if market_td else []
            
            # 4. Bookmakers & Odds
            bookie_td = row.select_one('td:nth-child(4)')
            # Use a more generic selector for bookie rows in the cell
            bookie_rows = bookie_td.select('div.flex.items-center.gap-2') if bookie_td else []
            
            bookmakers = []
            for br in bookie_rows:
                # Try finding text directly if class selector fails
                # The text is usually in a div with w-12 or just text-left
                odds_div = br.select_one('div[class*="text-left"]') 
                odds = odds_div.get_text(strip=True) if odds_div else "0.0"
                
                img = br.select_one('img')
                name = "Unknown"
                if img and 'alt' in img.attrs:
                    name = img['alt'].replace(' logo', '').strip()
                
                bookmakers.append({'name': name, 'odds': odds})
            
            if not bookmakers:
                 logger.info(f"Row {i}: No bookmakers found. Skipping.")
                 continue

            # 5. Start Time
            time_td = row.select_one('td:nth-child(5)')
            start_time = time_td.get_text(strip=True) if time_td else ""
            
            # Construct Unique ID
            unique_id = f"{event_name}_{profit}_{bookmakers[0]['odds'] if bookmakers else ''}"
            
            if unique_id in SEEN_BETS:
                # logger.info(f"Row {i}: duplicate {unique_id}")
                continue
                
            SEEN_BETS.add(unique_id)
            logger.info(f"Row {i}: ✅ New Surebet found: {unique_id}")
            
            # Map markets to bookmakers (assuming order matches, checking length)
            # Table has markets stacked, bookies stacked. Usually 1-to-1.
            # Safety check
            bets_data = []
            count = min(len(markets), len(bookmakers))
            for i in range(count):
                bets_data.append({
                    'market': markets[i],
                    'bookie': bookmakers[i]['name'],
                    'odds': bookmakers[i]['odds']
                })
            
            bet_obj = {
                'profit': profit,
                'league': league,
                'event': event_name,
                'start_time': start_time,
                'bets': bets_data
            }
            new_bets.append(bet_obj)
            
        except Exception as e:
            logger.error(f"Error parsing row: {e}")
            continue
            
    return new_bets

def format_message(bet, branding="ROBINSURESHOOD"):
    # Recreate the style from bot_sures.py format_new_surebet
    # ...
    
    emoji = get_sport_emoji(bet['league'])
    
    lines = []
    lines.append("📢 ALERTA DE SUREBETS (SIN RIESGO)")
    lines.append("")
    lines.append(f"1️⃣ 🔥 -- {branding} -- 🔥")
    lines.append(f"📈 PROFIT: {bet['profit']}%")
    lines.append("")
    lines.append(f"{emoji} Liga: {bet['league']}")
    lines.append(f"📆 Fecha: {bet['start_time']}")
    lines.append(f"🏆 Partido: {bet['event']}")
    lines.append("")
    
    for i, b in enumerate(bet['bets']):
        lines.append(f"🏦 Casa {i+1}: {b['bookie']}")
        lines.append(f"   🎯 Mercado: {b['market']}")
        lines.append(f"   📊 Cuota: {b['odds']}")
        # Stake not calculated here yet, maybe add later if formula known
        # lines.append(f"   💰 % Stake: ?") 
        if i < len(bet['bets']) - 1:
            lines.append("")
            
    return "\n".join(lines)

async def main():
    print("🚀 Starting BetHero Scraper...")
    
    # 1. Initialize Telegram
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.error("Telegram session invalid. Please log in again using the main bot logic first.")
        return

    # 2. Initialize Browser
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    
    # CRITICAL FIXES FOR DOCKER / RENDER
    options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    options.add_argument("--no-sandbox") # Bypass OS security model (required for Docker)
    options.add_argument("--disable-gpu") # Disable GPU hardware acceleration
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-extensions")
    options.add_argument("--dns-prefetch-disable")
    # options.page_load_strategy = 'eager' # REMOVED: Might be causing "static" page issues
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_page_load_timeout(60) 
    driver.set_window_size(1920, 1080)
    
    # Initialize DB
    init_db()


    def ensure_auto_refresh():
        print("🔄 Scanning page for buttons...")
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"found {len(buttons)} buttons.")
            
            target_button = None
            
            for i, btn in enumerate(buttons):
                try:
                    aria = btn.get_attribute("aria-label") or ""
                    cls = btn.get_attribute("class") or ""
                    inner = btn.get_attribute("innerHTML") or ""
                    text = btn.text or ""
                    
                    # Log potential candidates
                    if "refresh" in aria.lower() or "play" in cls or "lucide-play" in inner:
                        print(f"➡️ Candidate #{i}: Aria='{aria}', Class='{cls}', Text='{text}'")
                        
                    # Target identification
                    if "Start auto refresh" in aria:
                        target_button = btn
                        print("🎯 MATCH FOUND by aria-label!")
                        break
                    elif "lucide-play" in inner and "bg-gray-100" in cls:
                         target_button = btn
                         print("🎯 MATCH FOUND by innerHTML (icon)!")
                         break
                         
                except: continue
            
            if target_button:
                print("✅ Clicking target button...")
                driver.execute_script("arguments[0].style.border='5px solid red'", target_button)
                time.sleep(0.2)
                try:
                    target_button.click()
                except:
                    print("⚠️ Standard click failed. Forcing with JS...")
                    driver.execute_script("arguments[0].click();", target_button)
                
                print("✅ CLICKED (via Auto Logic).")
                return True
            else:
                print("⚠️ Target button NOT found in list.")
                return False
                
        except Exception as e:
            print(f"⚠️ Error scanning buttons: {e}")
            return False

    try:
        driver.get("https://app.betherosports.com/surebets")
        
        # Check for cookies in ENV
        # Check for cookies in ENV or File
        cookies_env = os.environ.get("BETHERO_COOKIES")
        cookies_file = "bethero_cookies.json"
        
        cookies = None
        
        if cookies_env:
             try:
                 cookies = json.loads(cookies_env)
                 print("🍪 Found cookies in environment (BETHERO_COOKIES). Loading...")
             except: pass
             
        if not cookies and os.path.exists(cookies_file):
             try:
                 with open(cookies_file, 'r') as f:
                     cookies = json.load(f)
                 print(f"🍪 Found cookies in {cookies_file}. Loading...")
             except: pass

        if cookies:
            try:
                for cookie in cookies:
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    try:
                        driver.add_cookie(cookie)
                    except Exception as ce:
                        logger.warning(f"Could not add cookie {cookie.get('name')}: {ce}")
                
                print("✅ Cookies loaded. Refreshing page...")
                driver.refresh()
                # Reduced sleep for speed
                time.sleep(2)
                
                # Activate Auto Refresh initially
                ensure_auto_refresh()
                
            except Exception as e:
                print(f"❌ Error loading cookies: {e}")
        
        # Check if we should wait for manual login
        # If we loaded cookies, we might assume we are logged in.
        # But let's verify or provide a flag.
        # If running in a cloud env, we definitely don't want to wait for input.
        # We can check if we are "headless"-ish or just check if cookies were loaded.
        
        if not cookies:
            print("\n" + "="*50)
            print("WAITING FOR LOGIN...")
            print("Please log in to BetHero in the browser window.")
            print("Then press Enter here to start scraping loop.")
            print("="*50 + "\n")
            input("👉 Press Enter to START scraping...")
        else:
            print("🚀 Auto-login attempted via cookies. Starting loop immediately...")
            
        # Ensure we are on the correct page
        if "/surebets" not in driver.current_url:
            print("🔄 Navigating to Surebets page...")
            driver.get("https://app.betherosports.com/surebets")
            time.sleep(2)
            # Re-try auto refresh
            ensure_auto_refresh()
            
        print("✅ Scraping started! Press Ctrl+C to stop.")
        
        while True:
            try:
                # Refresh or just read? 
                # If SPA, maybe element updates automatically? 
                # Safer to just read page_source every interval.
                # Occasionally refresh if stagnant?
                # For now: just parse current DOM.
                
                html = driver.page_source
                url = driver.current_url
                title = driver.title
                
                # DEBUG: Print status
                logger.info(f"Page: {title} | URL: {url} | HTML len: {len(html)}")
                
                # ENFORCE NAVIGATION TO SUREBETS
                if "surebets" not in url.lower():
                     logger.warning(f"⚠️ Incorrect URL ({url}). Redirecting to /surebets...")
                     driver.get("https://app.betherosports.com/surebets")
                     time.sleep(5)
                     ensure_auto_refresh() # Try to click it again after redirect
                     continue

                # Check if we are stuck on login
                if "login" in url.lower() or "signin" in url.lower():
                     logger.warning("⚠️  It seems we are on a LOGIN page. Cookies might be invalid or expired.")

                # DEBUG: Analyze HTML structure
                soup = BeautifulSoup(html, 'html.parser')
                tables = soup.select('table')
                logger.info(f"DEBUG: Found {len(tables)} tables in DOM.")
                
                rows = soup.select('table[role="table"] tbody[role="rowgroup"] tr[role="row"]')
                if not rows:
                    # Print some body text to see what is happening (loading? error?)
                    body_text = soup.select_one('body').get_text(strip=True)[:200]
                    logger.info(f"DEBUG NO ROWS: Body text start: {body_text}")

                bets = parse_surebets(html)
                
                if not bets:
                    logger.info("No bets found (or parsing failed).")


                else:
                    logger.info(f"✅ Found {len(bets)} bets on page.")
                    
                for bet in bets:
                    logger.info(f"Forwarding new surebet: {bet['event']} ({bet['profit']}%)")
                    
                    # Save to DB
                    save_bet_to_db(bet)
                    
                    
                    # 1. Send to Destination 1 (ROBINSURESHOOD) -- REMOVED by user request
                    # msg1 = format_message(bet, branding="ROBINSURESHOOD")
                    # await send_to_telegram(client, DEST_CHAT_ID, msg1)
                    
                    # 2. Send to Destination 2 (SURESTABERA) -- REMOVED by user request
                    # msg2 = format_message(bet, branding="SURESTABERA")
                    # if DEST_CHAT_2 != 0:
                    #     await send_to_telegram(client, DEST_CHAT_2, msg2)
                    
                    # Small delay to avoid flood limits
                    await asyncio.sleep(2)
                
                # Check for "Auto Refresh" button? 
                # The page has an "Auto Refresh" toggle. The user should enable it.
                # Or we can click the "Refresh" button if it exists?
                # But reading valid DOM is safer.
                
            except Exception as loop_e:
                logger.error(f"⚠️ Critical Loop Error: {loop_e}")
                # If we lose connection to Chrome (Max retries exceeded), it's best to die and let Render restart us
                if "Max retries exceeded" in str(loop_e) or "WinError" in str(loop_e) or "tab crashed" in str(loop_e):
                     print("💀 Fatal driver error. Exiting to trigger restart...")
                     # Close gracefully if possible
                     try:
                        driver.quit()
                     except: 
                        pass
                     sys.exit(1)
                     
            await asyncio.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await client.disconnect()
        driver.quit()

if __name__ == "__main__":
    asyncio.run(main())
