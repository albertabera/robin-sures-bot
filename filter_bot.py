import logging
import asyncio
import sqlite3
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("FILTER_BOT_TOKEN")

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
DB_NAME = os.path.abspath("surebets.db")
CHECK_INTERVAL = 5 # Seconds to check for new bets

# List of known bookmakers to filter (from User request)
KNOWN_BOOKIES = [
    "888sport", "Gran Madrid", "JOKERBET", "Pastón", 
    "Bet777", "betsson", "Casino Gran Via", "eBingo", 
    "PokerStars", "betfair exchange", "bwin", "Codere", 
    "Marca Apuestas", "Casumo", "LeoVegas", "paf", 
    "SpeedyBet", "YoSports", "Aupabet", "Juegging", 
    "KIROLBET", "Marathonbet", "Sportium", "Versus", 
    "TonyBet", "Casino Barcelona", "Winamax", "bet365", 
    "betfair", "Betway", "efbet", "interwetten", 
    "Luckia", "William Hill"
]

# Sports Configuration
KNOWN_SPORTS = {
    "Soccer": ["soccer", "football", "fútbol", "laliga", "premier", "serie a", "bundesliga", "ligue 1", "uefa", "champions", "europa"],
    "Basketball": ["basketball", "baloncesto", "nba", "ncaa", "euroleague", "acb"],
    "Tennis": ["tennis", "tenis", "atp", "wta", "itf", "davis", "open"],
    "Baseball": ["baseball", "mlb"],
    "American Football": ["american football", "nfl", "super bowl"],
    "Ice Hockey": ["ice hockey", "hockey", "nhl"],
    "Rugby": ["rugby", "union", "league", "six nations"],
    "Cricket": ["cricket", "ipl", "test"],
    "MMA": ["mma", "ufc", "bellator"],
    "Boxing": ["boxing", "boxeo"],
    "Darts": ["darts", "dardos"],
    "e-Sports": ["esport", "e-sport", "lol", "dota", "cs:go", "valorant"],
    "Badminton": ["badminton"],
    "Netball": ["netball"],
    "Futsal": ["futsal"],
    "Snooker": ["snooker"],
    "Table Tennis": ["table tennis", "ping pong"],
    "Volleyball": ["volleyball", "voleibol"],
    "Handball": ["handball", "balonmano"],
    "Floorball": ["floorball"],
    "Waterpolo": ["waterpolo"]
}

SPORT_EMOJIS = {
    "Soccer": "⚽", "Basketball": "🏀", "Tennis": "🎾", "Baseball": "⚾",
    "American Football": "🏈", "Ice Hockey": "🏒", "Rugby": "🏉", "Cricket": "🏏",
    "MMA": "🤼", "Boxing": "🥊", "Darts": "🎯", "e-Sports": "🎮",
    "Badminton": "🏸", "Netball": "🏐", "Futsal": "⚽", "Snooker": "🎱",
    "Table Tennis": "🏓", "Volleyball": "🏐", "Handball": "🤾", "Floorball": "🏑", "Waterpolo": "🤽"
}

# Sports Configuration
KNOWN_SPORTS = {
    "Soccer": ["soccer", "football", "fútbol", "laliga", "premier", "serie a", "bundesliga", "ligue 1", "uefa", "champions", "europa"],
    "Basketball": ["basketball", "baloncesto", "nba", "ncaa", "euroleague", "acb"],
    "Tennis": ["tennis", "tenis", "atp", "wta", "itf", "davis", "open"],
    "Baseball": ["baseball", "mlb"],
    "American Football": ["american football", "nfl", "super bowl"],
    "Ice Hockey": ["ice hockey", "hockey", "nhl"],
    "Rugby": ["rugby", "union", "league", "six nations"],
    "Cricket": ["cricket", "ipl", "test"],
    "MMA": ["mma", "ufc", "bellator"],
    "Boxing": ["boxing", "boxeo"],
    "Darts": ["darts", "dardos"],
    "e-Sports": ["esport", "e-sport", "lol", "dota", "cs:go", "valorant"],
    "Badminton": ["badminton"],
    "Netball": ["netball"],
    "Futsal": ["futsal"],
    "Snooker": ["snooker"],
    "Table Tennis": ["table tennis", "ping pong"],
    "Volleyball": ["volleyball", "voleibol"],
    "Handball": ["handball", "balonmano"],
    "Floorball": ["floorball"],
    "Waterpolo": ["waterpolo"]
}

SPORT_EMOJIS = {
    "Soccer": "⚽", "Basketball": "🏀", "Tennis": "🎾", "Baseball": "⚾",
    "American Football": "🏈", "Ice Hockey": "🏒", "Rugby": "🏉", "Cricket": "🏏",
    "MMA": "🤼", "Boxing": "🥊", "Darts": "🎯", "e-Sports": "🎮",
    "Badminton": "🏸", "Netball": "🏐", "Futsal": "⚽", "Snooker": "🎱",
    "Table Tennis": "🏓", "Volleyball": "🏐", "Handball": "🤾", "Floorball": "🏑", "Waterpolo": "🤽"
}

SPORTS_STRUCTURE = {
    "Soccer": [
        "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", 
        "UEFA Champions League", "UEFA Europa League", "UEFA Conference League", "UEFA Nations League",
        "MLS", "Eredivisie", "Primeira Liga", "Copa del Rey", "FA Cup", "EFL Cup", 
        "DFB-Pokal", "Coppa Italia", "Coupe de France", "Copa Libertadores", "Copa Sudamericana", 
        "Liga MX", "Jupiler Pro League", "World Cup", "Friendlies", "Others"
    ],
    "Basketball": [
        "NBA", "WNBA", "NCAA", "WNCAA", "EuroLeague", "EuroBasket", "EuroCup", 
        "ACB", "CBA", "NBL", "LNB Pro B", "Others"
    ],
    "Tennis": [
        "ATP", "WTA", "ITF", "ITF Women", "US Open", "Wimbledon", "Roland Garros", 
        "Australian Open", "Six Kings Slam", "Davis Cup", "Billie Jean King Cup", "Challenger", "Others"
    ],
    "Baseball": [
        "MLB", "NPB", "KBO", "AAA", "CPBL", "LMB", "NCAA", "MiLB", "Double-A", "Triple-A", "Others"
    ],
    "American Football": ["NFL", "NCAA", "CFL", "XFL", "USFL", "Others"],
    "Ice Hockey": ["NHL", "KHL", "SHL", "AHL", "Others"],
    "Rugby": ["Top 14", "Super League", "NRL", "World Cup", "Others"],
    "Cricket": ["IPL", "BBL", "CPL", "The Hundred", "PSL", "Test Matches", "ODI", "T20I", "Others"],
    "MMA": ["UFC", "Bellator", "PFL", "ONE Championship", "KSW", "Others"]
}

# --- Database Management ---
def init_bot_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            min_profit REAL DEFAULT 1.0,
            bookies TEXT DEFAULT '[]',
            sports TEXT DEFAULT '[]',
            leagues TEXT DEFAULT '{}',
            active INTEGER DEFAULT 1,
            expiration_date TEXT DEFAULT NULL
        )
    ''')
    
    # Migrations (Ignored if column exists)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN sports TEXT DEFAULT '[]'")
        print("⚠️ Added 'sports' column to users table.")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN expiration_date TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN leagues TEXT DEFAULT '{}'")
        print("⚠️ Added 'leagues' column to users table.")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def register_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Default expiration None (Free/Inactive) unless we want a trial? 
        # Let's start with NO access until paid.
        cursor.execute("INSERT OR IGNORE INTO users (user_id, expiration_date) VALUES (?, NULL)", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"ERROR in register_user: {e}")
    finally:
        try: conn.close()
        except: pass

def update_user_field(user_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()
    
def extend_subscription(user_id, days):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check current expiration
    cursor.execute("SELECT expiration_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    current_exp = None
    if row and row[0]:
        try:
            current_exp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        except:
            current_exp = datetime.now()
            
    # If expired or new, start from NOW. If active, add to existing.
    if not current_exp or current_exp < datetime.now():
        start_date = datetime.now()
    else:
        start_date = current_exp
        
    new_exp = start_date + timedelta(days=days)
    new_exp_str = new_exp.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("UPDATE users SET expiration_date = ? WHERE user_id = ?", (new_exp_str, user_id))
    conn.commit()
    conn.close()
    return new_exp_str

def is_subscription_active(expiration_str):
    if not expiration_str: return False
    try:
        exp = datetime.strptime(expiration_str, "%Y-%m-%d %H:%M:%S")
        return exp > datetime.now()
    except:
        return False

# --- Helpers ---
def get_user_bookies(user_row):
    if not user_row: return []
    raw = user_row['bookies']
    if raw == 'ALL': return list(KNOWN_BOOKIES)
    try:
        return json.loads(raw)
    except:
        return []

def get_user_sports(user_row):
    if not user_row: return []
    try:
        val = user_row['sports']
        if not val: return []
        return json.loads(val)
    except:
        return []

def get_user_leagues(user_row):
    if not user_row: return {}
    try:
        val = user_row['leagues']
        if not val: return {}
        return json.loads(val) # Dict { "Soccer": ["La Liga", ...] }
    except:
        return {}

def classify_sport(text):
    text = text.lower()
    for sport, keywords in KNOWN_SPORTS.items():
        for kw in keywords:
            if kw in text:
                return sport
    return "Other"
    
def get_sport_emoji(league_name):
    sport = classify_sport(league_name)
    return SPORT_EMOJIS.get(sport, "🏆")

def build_sports_keyboard(selected_sports):
    keyboard = []
    # Controls
    keyboard.append([
        InlineKeyboardButton("✅ Todos", callback_data="sport_enable_all"),
        InlineKeyboardButton("❌ Ninguno", callback_data="sport_disable_all")
    ])
    
    row = []
    for sport in KNOWN_SPORTS.keys():
        emoji = SPORT_EMOJIS.get(sport, "")
        code_toggle = "sport_toggle_" + sport
        code_leagues = "open_leagues_" + sport
        
        is_selected = (not selected_sports) or (sport in selected_sports)
        if selected_sports and "__NONE__" in selected_sports:
            is_selected = False
            
        label = f"✅ {emoji} {sport}" if is_selected else f"⬜ {emoji} {sport}"
        
        # Add Toggle Button AND "Ligas" button if applicable
        if sport in SPORTS_STRUCTURE:
             keyboard.append([
                InlineKeyboardButton(label, callback_data=code_toggle),
                InlineKeyboardButton("📂 Ligas", callback_data=code_leagues)
             ])
        else:
             keyboard.append([InlineKeyboardButton(label, callback_data=code_toggle)])
    
    keyboard.append([InlineKeyboardButton("💾 Guardar y Cerrar", callback_data="close_sports_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_leagues_keyboard(sport, enabled_leagues_for_sport):
    # enabled_leagues_for_sport is a list of strings. If empty -> ALL enabled.
    keyboard = []
    
    # Structure: [Back], [Enable All], [Disable All]
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="menu_sports")])
    keyboard.append([
        InlineKeyboardButton("✅ Todas", callback_data=f"league_all_{sport}"),
        InlineKeyboardButton("❌ Ninguna", callback_data=f"league_none_{sport}")
    ])
    
    leagues = SPORTS_STRUCTURE.get(sport, [])
    row = []
    for league in leagues:
        # Check if enabled
        # Logic: If list is empty -> ALL enabled.
        # If list has "__NONE__" -> NONE enabled.
        # Else -> Only items in list enabled.
        
        is_enabled = True
        if not enabled_leagues_for_sport:
            is_enabled = True
        elif "__NONE__" in enabled_leagues_for_sport:
            is_enabled = False
        else:
            is_enabled = league in enabled_leagues_for_sport
            
        emoji = "✅" if is_enabled else "⬜"
        cb = f"league_toggle_{sport}_{league}"
        
        row.append(InlineKeyboardButton(f"{emoji} {league}", callback_data=cb))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def build_bookie_keyboard(enabled_bookies):
    keyboard = []
    row = []
    for i, bookie in enumerate(KNOWN_BOOKIES):
        is_enabled = bookie in enabled_bookies
        status = "✅" if is_enabled else "❌"
        text = f"{status} {bookie}"
        callback_data = f"toggle_{bookie}"
        
        row.append(InlineKeyboardButton(text, callback_data=callback_data))
        
        if len(row) == 2: # 2 buttons per row
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    # Add control buttons
    keyboard.append([InlineKeyboardButton("💾 Guardar y Cerrar", callback_data="close_menu")])
    keyboard.append([InlineKeyboardButton("✅ Activar Todo", callback_data="enable_all"), 
                     InlineKeyboardButton("❌ Desactivar Todo", callback_data="disable_all")])
                     
    return InlineKeyboardMarkup(keyboard)

# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id)
    
    # Inline Menu
    keyboard = [
        [InlineKeyboardButton("📊 Mi Estado", callback_data="menu_status"), InlineKeyboardButton("💰 Profit", callback_data="menu_profit_hint")],
        [InlineKeyboardButton("🏦 Mis Casas", callback_data="menu_bookies"), InlineKeyboardButton("🏆 Deportes", callback_data="menu_sports")],
        [InlineKeyboardButton("🆘 Ayuda / Contacto", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🏹 RobinSuresHood Premium 🏹\n\n"
        f"¡Bienvenido, {user.first_name}! 👋\n\n"
        "Soy tu asistente personal de arbitraje deportivo 🤖.\n\n"
        "💎 Acceso Exclusivo\n"
        "Para recibir las mejores surebets, necesitas una suscripción activa.\n\n"
        f"🆔 Tu ID: `{user.id}`\n"
        "(Comparte este ID con administración para activar tu cuenta)\n\n"
        "⚙️ Tus Herramientas:\n"
        "━━━━━━━━━━\n"
        "👤 /status » Ver estado y caducidad\n"
        "📈 /stats » Tu rendimiento personal\n"
        "💰 /profit [N] » Mínimo % de ganancia\n"
        "🏦 /casas » Elegir tus casas de apuestas\n"
        "🏆 /deportes » Filtrar tus Deportes\n"
        "🆔 /id » Copiar tu ID de cliente\n"
        "🆘 /ayuda » Soporte y contacto\n\n"
        "🚀 ¡Afinando la puntería para tu rentabilidad!"
    )



            
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Centro de Ayuda RobinSuresHood\n\n"
        "Soporte y Activación de Plan Premium 💎\n\n"
        "👤 Contacto Oficial: @taberraco\n\n"
        "📖 Guía Rápida:\n"
        "• `/start` - Iniciar el bot\n"
        "• `/id` - Ver tu ID (necesario para activar)\n"
        "• `/casas` - Seleccionar bookies\n"
        "• `/profit` - Filtrar por beneficio\n"
        "• `/stats` - Ver tu rendimiento\n"
        "• `/status` - Ver estado de tu cuenta"
    )




async def set_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(context.args[0])
        update_user_field(update.effective_user.id, "min_profit", val)
        await update.message.reply_text(f"✅ Guardado: Mínimo {val}% profit.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Ejemplo: `/profit 5`")

async def cmd_bookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id) # Ensure exists
    row = get_user(user_id)
    
    current_bookies = get_user_bookies(row)
    kb = build_bookie_keyboard(current_bookies)
    
    await update.message.reply_text("🏦 Configura tus Casas de Apuestas:\nMarca las que tengas disponibles.", reply_markup=kb)

async def cmd_sports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id)
    row = get_user(user_id)
    current = get_user_sports(row)
    kb = build_sports_keyboard(current)
    try:
        await update.message.reply_text("🏆 Filtra tus Deportes Favoritos:", reply_markup=kb)
    except:
        await update.message.reply_text("❌ Error interno al cargar deportes.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    try:
        await query.answer() # Acknowledge click
    except Exception:
        pass # Ignore "Query is too old" errors
    
    # --- Main Menu Handling ---
    if data == "menu_status":
        await status(update, context) # Reuse existing status logic
        return
        
    elif data == "menu_help":
        await cmd_help(update, context)
        return
        
    elif data == "menu_bookies":
        # ... existing ...
        # (Shortened for brevity in tool call, just ensure existing logic remains)
        row = get_user(user_id)
        current_bookies = get_user_bookies(row)
        kb = build_bookie_keyboard(current_bookies)
        try: await query.message.reply_text("🏦 Configura tus Casas de Apuestas:", reply_markup=kb)
        except: await context.bot.send_message(user_id, "🏦 Configura tus Casas de Apuestas:", reply_markup=kb)
        return
        
    elif data == "menu_sports":
        row = get_user(user_id)
        current_sports = get_user_sports(row)
        kb = build_sports_keyboard(current_sports)
        try: await query.message.reply_text("🏆 Filtra tus Deportes:", reply_markup=kb)
        except: await context.bot.send_message(user_id, "🏆 Filtra tus Deportes:", reply_markup=kb)
        return
        
    # --- Bet Tracking ---
    elif data.startswith("track_"):
        surebet_id = data.replace("track_", "")
        context.user_data["track_sb_id"] = surebet_id
        
        await context.bot.send_message(
            user_id,
            "💰 **Registro de Apuesta**\n\n¿Cuánto has invertido en total (EUR)?\nRespondeme solo con el número (ej: 50 o 100.5)",
            reply_markup=ForceReply(selective=True),
            parse_mode='Markdown'
        )
        return
    
    # --- Bookie Toggles ---
    
    row = get_user(user_id)
    current_bookies = get_user_bookies(row)
    
    new_bookies = list(current_bookies)
    
    if data == "close_menu":
        await query.delete_message()
        await context.bot.send_message(user_id, "✅ Preferencias de casas guardadas.")
        return
        
    # --- Bookie Toggles ---
    if data.startswith("toggle_") or data == "enable_all" or data == "disable_all":
        # ... logic for bookies ...
        if data == "enable_all": new_bookies = list(KNOWN_BOOKIES)
        elif data == "disable_all": new_bookies = []
        else:
            bookie = data.replace("toggle_", "")
            if bookie in new_bookies: new_bookies.remove(bookie)
            else: new_bookies.append(bookie)
        
        update_user_field(user_id, "bookies", json.dumps(new_bookies))
        kb = build_bookie_keyboard(new_bookies)
        try: await query.edit_message_reply_markup(reply_markup=kb)
        except: pass
        return

    # --- Sports Toggles ---
    # Need to handle sports logic similarly
    elif "sport_" in data or data == "close_sports_menu":
        row = get_user(user_id)
        current_sports = get_user_sports(row)
        # If empty, it means ALL. To toggle one OFF, we must first populate with ALL, then remove.
        if not current_sports: 
            current_sports = list(KNOWN_SPORTS.keys())
            
        new_sports = list(current_sports)
        
        if data == "close_sports_menu":
             await query.delete_message()
             await context.bot.send_message(user_id, "✅ Deportes guardados.")
             return
             
        elif data == "sport_enable_all":
            new_sports = [] # Empty = All
            
        elif data == "sport_disable_all":
            new_sports = ["None"] # Hack to represent None? Or just store string "None"
            # If we store [], it means ALL. 
            # We need a way to say "Truly Empty".
            # Let's use a dummy value "DISABLED" or just check logic.
            # If User wants NO sports (weird), we can store ["__NONE__"].
            new_sports = ["__NONE__"]
            
        elif data.startswith("sport_toggle_"):
            sport = data.replace("sport_toggle_", "")
            if "__NONE__" in new_sports: new_sports.remove("__NONE__")
            
            if sport in new_sports:
                new_sports.remove(sport)
                # If removed last one, should it become ALL ([]) or NONE?
                # Usually user expects it to be empty = none if they deselected all?
                # But our default is [] = All.
                # So if empty, we must put ["__NONE__"] to mean None.
                if not new_sports: new_sports = ["__NONE__"]
            else:
                new_sports.append(sport)
                
            if len(new_sports) == len(KNOWN_SPORTS):
                new_sports = []
                
        update_user_field(user_id, "sports", json.dumps(new_sports))
        kb = build_sports_keyboard(new_sports)
        try: await query.edit_message_reply_markup(reply_markup=kb)
        except: pass
        return

    # --- League Menu & Toggles ---
    elif data.startswith("open_leagues_"):
        sport = data.replace("open_leagues_", "")
        row = get_user(user_id)
        user_leagues = get_user_leagues(row) # Dict
        sport_leagues = user_leagues.get(sport, []) # List
        
        kb = build_leagues_keyboard(sport, sport_leagues)
        try: await query.edit_message_text(f"⚽ **Ligas de {sport}**\nSelecciona las que quieras:", reply_markup=kb, parse_mode='Markdown')
        except: pass
        return

    elif data.startswith("league_"):
        # league_toggle_Soccer_La Liga
        # league_all_Soccer
        # league_none_Soccer
        
        parts = data.split("_")
        action = parts[1] # toggle, all, none
        sport = parts[2]
        
        # Determine remaining parts for league name (might contain spaces)
        # e.g. league_toggle_Soccer_La Liga -> parts[0]=league, [1]=toggle, [2]=Soccer, [3:]="La Liga"
        
        row = get_user(user_id)
        all_leagues_dict = get_user_leagues(row)
        current_list = all_leagues_dict.get(sport, [])
        
        # If currently empty (ALL), and we toggle one OFF, we must populate.
        if not current_list:
             all_possible = SPORTS_STRUCTURE.get(sport, [])
             current_list = list(all_possible)
             
        if action == "all":
            current_list = [] # Alloc logic
        elif action == "none":
            current_list = ["__NONE__"]
        elif action == "toggle":
            league_name = "_".join(parts[3:]) # Rejoin splits
            if "__NONE__" in current_list: current_list.remove("__NONE__")
            
            if league_name in current_list:
                current_list.remove(league_name)
                if not current_list: current_list = ["__NONE__"] # Empty list means ALL, so if manually emptied -> None
            else:
                current_list.append(league_name)
                # Check if all selected
                all_possible = SPORTS_STRUCTURE.get(sport, [])
                if len(current_list) == len(all_possible):
                    current_list = [] # Optimize to ALL
        
        # Save
        if not current_list:
             # Remove key from dict to save space? Or just keep empty list
             all_leagues_dict[sport] = []
        else:
             all_leagues_dict[sport] = current_list
             
        update_user_field(user_id, "leagues", json.dumps(all_leagues_dict))
        
        # Refresh
        kb = build_leagues_keyboard(sport, current_list)
        try: await query.edit_message_reply_markup(reply_markup=kb)
        except: pass
        return

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Total Bets
        cursor.execute("SELECT COUNT(*), SUM(stake), SUM(real_profit) FROM user_bets WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        count = res[0] if res[0] else 0
        volume = res[1] if res[1] else 0.0
        profit = res[2] if res[2] else 0.0
        
        roi = (profit / volume * 100) if volume > 0 else 0.0
        
        emoji_p = "📈" if profit >= 0 else "📉"
        
        msg = (
            f"📊 **Tus Estadísticas**\n\n"
            f"✅ Apuestas Realizadas: `{count}`\n"
            f"💸 Inversión Total: `{volume:.2f}€`\n\n"
            f"{emoji_p} **Beneficio Real:** `{profit:.2f}€`\n"
            f"⚡ ROI: `{roi:.2f}%`"
        )
        conn.close()
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text("❌ Error al calcular estadísticas.")

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Tu ID de Telegram es: `{user_id}`", parse_mode='Markdown')

async def cmd_add_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security: Check if sender is Admin (You)
    # Ideally checking against ADMIN_ID env var, but for now we can rely on a hardcoded ID or assume you are the first user?
    # BETTER: Let's assume YOU are the admin. Since I don't know your ID yet, 
    # I will allow it for now but you should set ADMIN_ID in .env
    
    admin_id = os.getenv("ADMIN_ID")
    sender_id = str(update.effective_user.id)
    
    if admin_id and sender_id != admin_id:
        await update.message.reply_text("⛔ Comando solo para administradores.")
        return

    try:
        # /add 123456 30
        target_id = int(context.args[0])
        days = int(context.args[1])
        
        new_date = extend_subscription(target_id, days)
        
        await update.message.reply_text(f"✅ Usuario {target_id} renovado hasta: {new_date}")
        
        # Notify user potentially?
        try:
            await context.bot.send_message(target_id, f"🎉 ¡Tu suscripción ha sido activada/renovada!\n📅 Caduca el: {new_date}")
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text("❌ Uso: `/add <ID> <DIAS>`")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_user(update.effective_user.id)
    if row:
        min_p = row['min_profit']
        active = row['active']
        exp_date = row['expiration_date']
        bookies = get_user_bookies(row)
        
        is_premium = is_subscription_active(exp_date)
        status_icon = "🟢 PREMIUM" if is_premium else "🔴 CADUCADO / GRATIS"
        
        bookies_text = ", ".join(bookies) if len(bookies) < len(KNOWN_BOOKIES) else "TODAS"
        if not bookies: bookies_text = "NINGUNA"
        
        sports = get_user_sports(row)
        sports_text = ", ".join(sports) if sports else "TODOS"
        if sports and "None" in sports or "__NONE__" in sports: sports_text = "NINGUNO"
        
        await update.message.reply_text(
            f"📊 Tu Cuenta:\n"
            f"Estado: {status_icon}\n"
            f"📅 Caducidad: {exp_date if exp_date else 'Sin activar'}\n\n"
            f"💰 Profit Mínimo: {min_p}%\n"
            f"🏦 Casas: {bookies_text}\n"
            f"🏆 Deportes: {sports_text}\n",
            protect_content=True
        )
    else:
        await update.message.reply_text("No estás registrado.")

async def handle_stake_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "track_sb_id" not in context.user_data:
        return # Not waiting for input
        
    text = update.message.text
    try:
        stake = float(text.replace(',', '.'))
        sb_id = context.user_data.pop("track_sb_id")
        
        # Get Profit % from DB
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT profit FROM surebets WHERE id = ?", (sb_id,))
        res = cursor.fetchone()
        
        if not res:
            await update.message.reply_text("❌ Error: No encuentro esa apuesta (¿es muy antigua?).")
            conn.close()
            return
            
        profit_percent = res[0]
        real_profit = stake * (profit_percent / 100)
        
        # Save to user_bets
        cursor.execute("""
            INSERT INTO user_bets (user_id, surebet_id, profit_percent, stake, real_profit)
            VALUES (?, ?, ?, ?, ?)
        """, (update.effective_user.id, sb_id, profit_percent, stake, real_profit))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Apuesta registrada.\nInversión: {stake}€\nBeneficio Estimado: +{real_profit:.2f}€")
        
    except ValueError:
        await update.message.reply_text("❌ Por favor, escribe un número válido (ej: 50).")

# --- Background Worker ---
async def check_new_bets(context: ContextTypes.DEFAULT_TYPE):
    last_id = context.bot_data.get('last_processed_id', 0)
    
    # Init last_id from DB if 0 (start fresh)
    if last_id == 0:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM surebets")
            res = cursor.fetchone()
            start_id = res[0] if res[0] else 0
            conn.close()
            context.bot_data['last_processed_id'] = start_id
            return
        except: return

    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get NEW bets
        cursor.execute("SELECT * FROM surebets WHERE id > ? ORDER BY id ASC", (last_id,))
        new_bets = cursor.fetchall()
        
        # Get Active Users
        cursor.execute("SELECT * FROM users WHERE active = 1")
        users = cursor.fetchall()
        
        conn.close()
        
        if not new_bets: return

        logger.info(f"🔍 Found {len(new_bets)} NEW bets (IDs: {[b['id'] for b in new_bets]}) > Last ID {last_id}")
        
        if not users:
            logger.warning("⚠️ No active users found in DB!")
            context.bot_data['last_processed_id'] = new_bets[-1]['id'] # Skip them anyway
            return
            
        logger.info(f"Checking {len(new_bets)} bets against {len(users)} users...")
        
        
        for bet in new_bets:
            profit = bet['profit']
            bet_bookies_json = bet['bookies_json'] 
            
            # Parse bet bookies names
            try:
                bet_bookies_data = json.loads(bet_bookies_json)
                bet_bookie_names = [b['bookie'] for b in bet_bookies_data]
            except:
                bet_bookie_names = []
            
            # Format message (Standard Style)
            emoji = get_sport_emoji(bet['league'])
            
            lines = []
            lines.append("🏹 ALERTA DE SUREBETS (SIN RIESGO)")
            lines.append("")
            lines.append(f"1️⃣ 🔥 -- ROBINSURESHOOD PREMIUM -- 🔥")
            lines.append(f"📈 PROFIT: {profit}%")
            lines.append("")
            lines.append(f"{emoji} Liga: {bet['league']}")
            lines.append(f"📆 Fecha: {bet['found_at']}") # or start_time if available in DB... wait DB has found_at, start_time is inside...
            # Actually DB schema: id, found_at, event, league, profit, bookies_json
            # We don't have start_time in DB explicitly? 
            # Wait, let me check init_db in scraper.
            # Scraper init_db: event, league, profit, bookies_json. 
            # It seems start_time was NOT saved to DB! 
            # I will use found_at as a proxy or just omit date if strictly following format.
            # But the user wants "Same format".
            # Let's use found_at for now.
            lines.append(f"🏆 Partido: {bet['event']}")
            lines.append("")
            
            # Reconstruct bookies loop
            # bookies_json is list of dicts: market, bookie, odds
            try:
                b_data = json.loads(bet_bookies_json)
                for i, b in enumerate(b_data):
                    lines.append(f"🏦 Casa {i+1}: {b.get('bookie', 'Unknown')}")
                    lines.append(f"   🎯 Mercado: {b.get('market', '-')}")
                    lines.append(f"   📊 Cuota: {b.get('odds', '-')}")
                    if i < len(b_data) - 1:
                        lines.append("")
            except:
                pass
            
            msg = "\n".join(lines)
            
            for user in users:
                user_id = user['user_id']
                user_min_profit = user['min_profit']
                user_bookies = get_user_bookies(user)
                expiration = user['expiration_date']

                # Check 0: Subscription Active? (Monetization)
                # If expiration is None or in the past -> SKIP
                if not is_subscription_active(expiration):
                    continue

                # Check 0: Subscription Active?
                if not is_subscription_active(expiration):
                    continue

                # Check 1: Profit
                if profit < user_min_profit:
                    continue
                    
                # Check 2: Sports
                # Classify bet
                bet_sport = classify_sport(bet['league'] + " " + bet['event'])
                user_sports = get_user_sports(user)
                
                # If user_sports is empty -> ALL allowed
                # If user_sports has "__NONE__" -> NONE allowed (skip)
                if user_sports and "__NONE__" in user_sports:
                    continue
                
                if user_sports and bet_sport not in user_sports:
                     # Filter blocked!
                     # logger.info(f"User {user_id} filtered out sport {bet_sport}")
                     continue
                
                # Check 2.5: Leagues (Granular)
                user_leagues_dict = get_user_leagues(user)
                allowed_leagues = user_leagues_dict.get(bet_sport, [])
                
                if allowed_leagues:
                    if "__NONE__" in allowed_leagues:
                        continue
                        
                    found_league = False
                    for allowed in allowed_leagues:
                        if allowed.lower() in bet['league'].lower() or bet['league'].lower() in allowed.lower():
                            found_league = True
                            break
                    
                    if not found_league:
                        continue
                     
                # Check 3: Bookies
                has_all_bookies = True
                for required_bookie in bet_bookie_names:
                    found = False
                    for allowed in user_bookies:
                        if allowed.lower() in required_bookie.lower() or required_bookie.lower() in allowed.lower():
                            found = True
                            break
                    if not found:
                        has_all_bookies = False
                        break
                
                # Debug logging
                # logger.info(f"Checking user {user_id}: Sub={is_subscription_active(expiration)}, Profit={profit}>={user_min_profit}, Bookies={has_all_bookies}")
                
                if has_all_bookies:
                    try:
                        await context.bot.send_message(chat_id=user_id, text=msg, protect_content=True)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.warning(f"Failed to send to {user_id}: {e}")

    except Exception as e:
        logger.error(f"Worker Error: {e}")

def format_bookies(json_str):
    try:
        data = json.loads(json_str)
        # Included Market info as requested
        # Format: "Bookie (Market) @ Odd"
        return "\n".join([f"🏦 {b['bookie']} ({b['market']}) ➡️ @{b['odds']}" for b in data])
    except:
        return ""




async def post_init(application):
    from telegram import BotCommand
    commands = [
        BotCommand("start", "🏹 Iniciar / Menú"),
        BotCommand("status", "📊 Estado Cuenta"),
        BotCommand("casas", "🏦 Casas de Apuestas"),
        BotCommand("deportes", "🏆 Deportes"),
        BotCommand("profit", "💰 Mínimo Beneficio"),
        BotCommand("id", "🆔 Ver mi ID"),
        BotCommand("ayuda", "🆘 Soporte")
    ]
    await application.bot.set_my_commands(commands)

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: FILTER_BOT_TOKEN not found in .env")
        exit(1)
        
    init_bot_db()
    
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profit", set_profit))
    app.add_handler(CommandHandler("casas", cmd_bookies))
    app.add_handler(CommandHandler("deportes", cmd_sports))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("add", cmd_add_promo)) # Admin Command
    app.add_handler(CommandHandler("ayuda", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_stake_input))
    
    job_queue = app.job_queue
    job_queue.run_repeating(check_new_bets, interval=CHECK_INTERVAL, first=1)
    
    print("🤖 Bot Iniciado y Esperando...")
    app.run_polling()
    
def run_bot():
    if not TOKEN:
        print("❌ Error: FILTER_BOT_TOKEN not found in .env")
        return
        
    init_bot_db()
    
    global app # Global app required for handlers? No, it's local scope but handlers use closures?
    # Actually handlers are defined at module level, so they are fine.
    # The app variable is local to this func.
    
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profit", set_profit))
    app.add_handler(CommandHandler("casas", cmd_bookies))
    app.add_handler(CommandHandler("deportes", cmd_sports))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("add", cmd_add_promo)) # Admin Command
    app.add_handler(CommandHandler("ayuda", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_stake_input))
    
    job_queue = app.job_queue
    job_queue.run_repeating(check_new_bets, interval=CHECK_INTERVAL, first=1)
    
    print("🤖 Bot Iniciado y Esperando (Modo Combinado)...")
    app.run_polling()
