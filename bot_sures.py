import os, io, asyncio, logging, contextlib, re
from fastapi import FastAPI, Response
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.sessions import StringSession
from telethon.utils import get_peer_id
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, level_name, logging.INFO),
                    format="%(asctime)s %(levelname)s %(message)s")

# ─────────────────────────────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────────────────────────────
API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION  = os.environ.get("TELEGRAM_STRING_SESSION", "")

# Compatibilidad con tus variables previas
ORIGIN_CHAT_1 = os.environ.get("ORIGIN_CHAT_1", "").strip()
DEST_CHAT_1   = os.environ.get("DEST_CHAT_1", "").strip()
ORIGIN_CHAT_2 = os.environ.get("ORIGIN_CHAT_2", "").strip()
DEST_CHAT_2   = os.environ.get("DEST_CHAT_2", "").strip()

# NUEVO: múltiples orígenes por destino (CSV)
# Ej: ORIGINS_DEST1="@canalA,@NombreDeBot,-1001234567890"
ORIGINS_DEST1 = os.environ.get("ORIGINS_DEST1", "").strip()
ORIGINS_DEST2 = os.environ.get("ORIGINS_DEST2", "").strip()

FORCE_DOCUMENT = os.environ.get("FORCE_DOCUMENT", "false").lower() == "true"

# NUEVO: Filtrado solo para orígenes de DEST_CHAT_1 (ORIGIN_CHAT_1 y ORIGINS_DEST1)
# Si el mensaje contiene "Valuebets", enviar a DEST_CHAT_3 en lugar del destino por defecto
FILTER_KEYWORD = "Valuebets"  # Mantengo el original
DEST_CHAT_3    = os.environ.get("DEST_CHAT_3", "").strip()

# AÑADIDO: Nuevo filtrado para "bet365" en orígenes de DEST_CHAT_1
# Si el mensaje contiene "bet365", enviar solo a DEST_CHAT_1
# Si no contiene "bet365", enviar a DEST_CHAT_1 y DEST_CHAT_4
FILTER_KEYWORD2 = "bet365"
DEST_CHAT_4     = os.environ.get("DEST_CHAT_4", "").strip()  # Nuevo canal destino

# AÑADIDO: Nuevo filtrado para "winamax" en orígenes de DEST_CHAT_1 (similar al de bet365)
# Si el mensaje contiene "winamax", enviar solo a DEST_CHAT_1
# Si no contiene "winamax", enviar a DEST_CHAT_1 y DEST_CHAT_5
FILTER_KEYWORD3 = "winamax"
DEST_CHAT_5     = os.environ.get("DEST_CHAT_5", "").strip()  # Nuevo canal destino

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _maybe_int(v):
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.lstrip("-").isdigit():
        try:
            return int(v)
        except ValueError:
            return v
    return v

def _split_csv(s: str):
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def calculate_profit_percentage(odds1, odds2):
    try:
        o1 = float(odds1)
        o2 = float(odds2)
        if o1 <= 1 or o2 <= 1:
            return None  # Odds inválidas
        surebet_pct = 1 / (1 / o1 + 1 / o2) * 100
        return surebet_pct - 100  # Profit % = surebet % - 100%
    except (ValueError, ZeroDivisionError):
        return None

def modify_text(text):
    # Cambiar "SUREBETS25" a "SURESTABERA"
    text = text.replace("SUREBETS25", "SURESTABERA")
    
    # Encabezado para split
    header = "🔥 -- SURESTABERA -- 🔥"
    parts = text.split(header)
    if len(parts) < 2:
        return text  # No hay bloques, devolver tal cual
    
    modified_parts = [parts[0]]  # Parte antes del primer header
    for part in parts[1:]:
        lines = part.strip().split('\n')
        profit_line_idx = None
        odds = []
        for i, line in enumerate(lines):
            if line.startswith("📈 PROFIT:"):
                profit_line_idx = i
            elif "🎯 @" in line:
                # Extraer odds
                match = re.search(r"🎯 @([\d.]+)", line)
                if match:
                    odds.append(match.group(1))
                # Modificar la línea: quitar "💰...€ para ..." pero dejar "🎯 @odds"
                new_line = re.sub(r" 💰.*$", "", line)
                lines[i] = new_line
        
        # Si hay exactamente 2 odds y una línea PROFIT, calcular profit y reemplazar
        if len(odds) == 2 and profit_line_idx is not None:
            profit_pct = calculate_profit_percentage(odds[0], odds[1])
            if profit_pct is not None:
                lines[profit_line_idx] = f"📈 PROFIT: {profit_pct:.2f}%"
        
        modified_parts.append('\n'.join(lines))
    
    return header.join(modified_parts)

# ─────────────────────────────────────────────────────────────────────────────
# NUEVO: Helpers para parsear líneas de casas (sure/middle)
# ─────────────────────────────────────────────────────────────────────────────
def parse_book_line(line: str):
    """
    Intenta extraer:
      - nombre de casa
      - mercado
      - cuota
      - stake (si aparece con 💰)
      - sufijo (⚡, ❓, etc.)
    Si algo falla, devuelve valores parciales sin romper.
    """
    # Normalizar: reemplazar 📕 por nada para parsear
    original = line
    line_wo_icon = line.replace("📕", "").replace("🏠", "").strip()

    book_name = ""
    market = ""
    odds = ""
    stake = ""
    suffix = ""

    # Separar casa y resto por 📍
    if "📍" in line_wo_icon:
        left, right = line_wo_icon.split("📍", 1)
        book_name = left.strip()
        right = right.strip()
    else:
        # Si no hay 📍, devolvemos casi todo como nombre
        return original, "", "", "", ""

    # Mercado: hasta 🎲
    part_before_odd = right
    part_after_odd = ""
    if "🎲" in right:
        part_before_odd, part_after_odd = right.split("🎲", 1)
        market = part_before_odd.strip()
        part_after_odd = part_after_odd.strip()
    else:
        market = right.strip()

    # Cuota: después de @
    m_odds = re.search(r"@\s*([\d.,]+)", part_after_odd)
    if m_odds:
        odds = m_odds.group(1)

    # Stake y sufijo: después de 💰
    if "💰" in part_after_odd:
        stake_part = part_after_odd.split("💰", 1)[1]
        # stake_part suele ser "14.01% ⚡️ Causa Surebet" o "85.99% ❓ ..."
        # Intentamos separar valor y resto
        m_stake = re.match(r"\s*([\d.,]+%?)\s*(.*)", stake_part)
        if m_stake:
            stake = m_stake.group(1)
            suffix = m_stake.group(2).strip()

    # Si algo está vacío, usamos el original como fallback parcial
    return book_name, market, odds, stake, suffix

# ─────────────────────────────────────────────────────────────────────────────
# NUEVO: Formateo NUEVA SUREBET (💰 New surebet found!)
# ─────────────────────────────────────────────────────────────────────────────
def format_new_surebet(text: str) -> str:
    try:
        lines = text.splitlines()
        data = {}
        bookies = []
        current_bookie = {}
        
        # Parsing header info
        for line in lines:
            line = line.strip()
            if line.startswith("Profit:"):
                data['profit'] = line.replace("Profit:", "").strip().replace("%", "")
            elif line.startswith("Sport:"):
                data['sport'] = line.replace("Sport:", "").strip()
            elif line.startswith("League:"):
                data['league'] = line.replace("League:", "").strip()
            elif line.startswith("Event:"):
                data['event'] = line.replace("Event:", "").strip()
            elif line.startswith("Start at :"):
                data['start'] = line.replace("Start at :", "").strip()
            elif line.endswith(":") and not line.startswith("Start at") and not line.startswith("Profit") and not line.startswith("Sport") and not line.startswith("League") and not line.startswith("Event"):
                # New bookie
                if current_bookie:
                    bookies.append(current_bookie)
                current_bookie = {'name': line.rstrip(":")}
            elif "→" in line:
                parts = line.split("→")
                if len(parts) == 2:
                    current_bookie['market'] = parts[0].replace("▫️", "").strip()
                    current_bookie['odds'] = parts[1].strip()
            elif "Stake:" in line:
                # ▫️Stake: 35.62 $ Place Bet (url)
                # Remove ▫️
                s = line.replace("▫️", "").strip()
                # Extract Stake - relaxed regex for any currency or formatting
                m_stake = re.search(r"Stake:\s*([\d.,]+)", s)
                if m_stake:
                    current_bookie['stake'] = m_stake.group(1)
                
                # Url
                m_url = re.search(r"\((http.*?)\)", s)
                if m_url:
                    current_bookie['url'] = m_url.group(1)

        if current_bookie:
            bookies.append(current_bookie)

        # Formatting
        out = []
        out.append("📢 ALERTA DE SUREBETS (SIN RIESGO)")
        out.append("")
        out.append("1️⃣ 🔥 -- SURESTABERA -- 🔥")
        out.append(f"📈 PROFIT: {data.get('profit', '0')}%")
        out.append("")
        
        # Sport mapping (only emojis, no naming translation as requested)
        sport_raw = data.get('sport', 'Unknown')
        emoji = "🏆"
        # Determine emoji based on raw string content
        if "Basketball" in sport_raw or "Baloncesto" in sport_raw: 
            emoji = "🏀"
        elif "Football" in sport_raw or "Soccer" in sport_raw or "Fútbol" in sport_raw: 
            emoji = "⚽️"
        elif "Tennis" in sport_raw or "Tenis" in sport_raw: 
            emoji = "🎾"
        
        out.append(f"{emoji} Deporte: {sport_raw}")
        
        # Date (raw as requested)
        out.append(f"📆 Fecha: {data.get('start', '')}")
             
        out.append(f"🏆 Partido: {data.get('event', '')} ({data.get('league', '')})")
        out.append("")
        
        for i, b in enumerate(bookies):
            b_url = b.get("url", "")
            b_link_str = f" ({b_url})" if b_url else ""
            out.append(f"🏦 Casa {i+1}: {b.get('name', '')}{b_link_str}")
            out.append(f"   🎯 Mercado: {b.get('market', '')}")
            out.append(f"   📊 Cuota: {b.get('odds', '')}")
            st = b.get('stake', '')
            out.append(f"   💰 % Stake: {st}%")
            if i < len(bookies) - 1:
                out.append("")
            
        return "\n".join(out).strip()
        
    except Exception as e:
        logging.exception("Error formatting new surebet")
        return text

# ─────────────────────────────────────────────────────────────────────────────
# NUEVO: Formateo SUREBETS (Plantilla 1, múltiples)
# ─────────────────────────────────────────────────────────────────────────────
def format_surebets(text: str) -> str:
    lines = text.splitlines()
    blocks = []
    current_lines = None

    for line in lines:
        stripped = line.strip()

        # Saltar cabeceras globales que vienen del canal original
        if stripped.startswith("💵 Rango Beneficio:"):
            continue
        if "📢 Alerta de Surebets" in stripped:
            continue

        # Inicio de una nueva sure
        if stripped.startswith("💎 Profit"):
            if current_lines is not None:
                blocks.append(current_lines)
            current_lines = [line]
        else:
            if current_lines is not None:
                current_lines.append(line)
            else:
                # Antes de la primera sure, ignoramos
                continue

    if current_lines is not None:
        blocks.append(current_lines)

    if not blocks:
        return text

    out_lines = []
    out_lines.append("📢 ALERTA DE SUREBETS (SIN RIESGO)")
    out_lines.append("")

    for idx, block in enumerate(blocks, start=1):
        # Vars por defecto
        profit_val = ""
        sport_emoji = ""
        sport_name = ""
        date_val = ""
        match_full = ""
        comp_full = ""
        book1 = None
        book2 = None

        try:
            # Parseamos líneas del bloque
            for bline in block:
                s = bline.strip()
                if s.startswith("💎 Profit"):
                    # Ej: "💎 Profit: 5.08%"
                    m = re.search(r"([\d.,]+)%", s)
                    if m:
                        profit_val = m.group(1)
                elif s.startswith("⚽") or s.startswith("🏀") or s.startswith("🎾") or s.startswith("🏈") or s.startswith("🏀"):
                    # Ej: "⚽️ Fútbol"
                    parts = s.split(maxsplit=1)
                    sport_emoji = parts[0]
                    sport_name = parts[1] if len(parts) > 1 else ""
                elif s.startswith("🗓") or s.startswith("📆"):
                    # Ej: "🗓️ 06/12 21:00"
                    parts = s.split(maxsplit=1)
                    date_val = parts[1] if len(parts) > 1 else ""
                elif s.startswith("🏆"):
                    # Ej: "🏆 Athletic Bilbao – Atletico Madrid (To Spanish La Liga Primera)"
                    raw = s[1:].strip()  # quitamos el emoji
                    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", raw)
                    if m:
                        match_full = m.group(1).strip()
                        comp_full = m.group(2).strip()
                    else:
                        match_full = raw
                        comp_full = ""
                elif "📕" in s or "🏠" in s:
                    # Líneas de casas
                    if book1 is None:
                        book1 = bline
                    elif book2 is None:
                        book2 = bline

            out_lines.append(f"{idx}️⃣ 🔥 -- SURESTABERA -- 🔥")
            if profit_val:
                out_lines.append(f"📈 PROFIT: {profit_val}%")
            else:
                out_lines.append("📈 PROFIT:")

            out_lines.append("")

            # Deporte
            if sport_emoji or sport_name:
                out_lines.append(f"{sport_emoji} Deporte: {sport_name}".strip())
            # Fecha
            if date_val:
                out_lines.append(f"📆 Fecha: {date_val}")
            # Partido
            if match_full:
                if comp_full:
                    out_lines.append(f"🏆 Partido: {match_full} ({comp_full})")
                else:
                    out_lines.append(f"🏆 Partido: {match_full}")

            out_lines.append("")

            # Casas
            # Casa 1
            if book1:
                b1_name, b1_mkt, b1_odds, b1_stake, b1_suf = parse_book_line(book1)
                out_lines.append(f"🏦 Casa 1: {b1_name}")
                if b1_mkt:
                    out_lines.append(f"   🎯 Mercado: {b1_mkt}")
                if b1_odds:
                    out_lines.append(f"   📊 Cuota: {b1_odds}")
                if b1_stake or b1_suf:
                    suf = f"  {b1_suf}" if b1_suf else ""
                    out_lines.append(f"   💰 % Stake: {b1_stake}{suf}")
            # Casa 2
            if book2:
                out_lines.append("")
                b2_name, b2_mkt, b2_odds, b2_stake, b2_suf = parse_book_line(book2)
                out_lines.append(f"🏦 Casa 2: {b2_name}")
                if b2_mkt:
                    out_lines.append(f"   🎯 Mercado: {b2_mkt}")
                if b2_odds:
                    out_lines.append(f"   📊 Cuota: {b2_odds}")
                if b2_stake or b2_suf:
                    suf = f"  {b2_suf}" if b2_suf else ""
                    out_lines.append(f"   💰 % Stake: {b2_stake}{suf}")

            if idx != len(blocks):
                out_lines.append("")
                out_lines.append("")

        except Exception as e:
            logging.exception("Error formateando surebet, devolviendo bloque original")
            # Si algo falla, metemos el bloque original tal cual
            out_lines.append("\n".join(block))
            if idx != len(blocks):
                out_lines.append("")
                out_lines.append("")

    return "\n".join(out_lines).strip()

# ─────────────────────────────────────────────────────────────────────────────
# NUEVO: Formateo MIDDLEBETS (Plantilla 1, múltiples)
# ─────────────────────────────────────────────────────────────────────────────
def format_middlebets(text: str) -> str:
    lines = text.splitlines()
    blocks = []
    current_lines = None

    for line in lines:
        s = line.strip()

        # Cabeceras originales fuera
        if s.startswith("👑 Rango Valor Esperado"):
            continue
        if "📢 Alerta de Middlebets" in s:
            continue

        if s.startswith("💎 Valor esperado"):
            if current_lines is not None:
                blocks.append(current_lines)
            current_lines = [line]
        else:
            if current_lines is not None:
                current_lines.append(line)
            else:
                continue

    if current_lines is not None:
        blocks.append(current_lines)

    if not blocks:
        return text

    out_lines = []
    out_lines.append("📢 ALERTA DE MIDDLEBETS")
    out_lines.append("")

    for idx, block in enumerate(blocks, start=1):
        min_ev = ""
        max_ev = ""
        prob_middle = ""
        sport_emoji = ""
        sport_name = ""
        date_val = ""
        match_full = ""
        comp_full = ""
        book1 = None
        book2 = None

        try:
            for bline in block:
                s = bline.strip()
                # Rango EV
                if "📉 Mín." in s and "📈 Máx." in s:
                    # Ej: "📉 Mín. 9.99% | 📈 Máx. 119.98%"
                    m = re.search(r"Mín\.\s*([\d.,]+%)\s*\|\s*📈 Máx\.\s*([\d.,]+%)", s)
                    if m:
                        min_ev = m.group(1)
                        max_ev = m.group(2)
                # Prob middle
                elif s.startswith("🍀"):
                    # "🍀 Probabilidad de middle: 2.33%"
                    m = re.search(r"([\d.,]+%)", s)
                    if m:
                        prob_middle = m.group(1)
                # Deporte
                elif s.startswith("⚽") or s.startswith("🏀") or s.startswith("🎾") or s.startswith("🏈"):
                    parts = s.split(maxsplit=1)
                    sport_emoji = parts[0]
                    sport_name = parts[1] if len(parts) > 1 else ""
                # Fecha
                elif s.startswith("🗓") or s.startswith("📆"):
                    parts = s.split(maxsplit=1)
                    date_val = parts[1] if len(parts) > 1 else ""
                # Partido
                elif s.startswith("🏆"):
                    raw = s[1:].strip()
                    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", raw)
                    if m:
                        match_full = m.group(1).strip()
                        comp_full = m.group(2).strip()
                    else:
                        match_full = raw
                        comp_full = ""
                # Casas
                elif "📕" in s or "🏠" in s:
                    if book1 is None:
                        book1 = bline
                    elif book2 is None:
                        book2 = bline

            out_lines.append(f"{idx}️⃣ 🔥 -- SURESTABERA -- 🔥")

            # Rango EV
            if min_ev and max_ev:
                out_lines.append(f"📉 Rango EV: {min_ev}  →  {max_ev}")
            # Prob middle
            if prob_middle:
                out_lines.append(f"🍀 Probabilidad de middle: {prob_middle}")

            out_lines.append("")

            # Deporte
            if sport_emoji or sport_name:
                out_lines.append(f"{sport_emoji} Deporte: {sport_name}".strip())
            # Fecha
            if date_val:
                out_lines.append(f"📆 Fecha: {date_val}")
            # Partido
            if match_full:
                if comp_full:
                    out_lines.append(f"🏆 Partido: {match_full} ({comp_full})")
                else:
                    out_lines.append(f"🏆 Partido: {match_full}")

            out_lines.append("")
            out_lines.append("🧩 Estructura del middle:")

            # Casas
            if book1:
                out_lines.append("")
                b1_name, b1_mkt, b1_odds, b1_stake, b1_suf = parse_book_line(book1)
                out_lines.append(f"🏦 Casa 1: {b1_name}")
                if b1_mkt:
                    out_lines.append(f"   🎯 Mercado: {b1_mkt}")
                if b1_odds:
                    out_lines.append(f"   📊 Cuota: {b1_odds}")
                if b1_stake or b1_suf:
                    suf = f"  {b1_suf}" if b1_suf else ""
                    out_lines.append(f"   💰 % Stake: {b1_stake}{suf}")

            if book2:
                out_lines.append("")
                b2_name, b2_mkt, b2_odds, b2_stake, b2_suf = parse_book_line(book2)
                out_lines.append(f"🏦 Casa 2: {b2_name}")
                if b2_mkt:
                    out_lines.append(f"   🎯 Mercado: {b2_mkt}")
                if b2_odds:
                    out_lines.append(f"   📊 Cuota: {b2_odds}")
                if b2_stake or b2_suf:
                    suf = f"  {b2_suf}" if b2_suf else ""
                    out_lines.append(f"   💰 % Stake: {b2_stake}{suf}")

            if idx != len(blocks):
                out_lines.append("")
                out_lines.append("")

        except Exception:
            logging.exception("Error formateando middlebet, devolviendo bloque original")
            out_lines.append("\n".join(block))
            if idx != len(blocks):
                out_lines.append("")
                out_lines.append("")

    return "\n".join(out_lines).strip()

# ─────────────────────────────────────────────────────────────────────────────
# NUEVO: selector general Sure/Middle
# ─────────────────────────────────────────────────────────────────────────────
def modify_sure_middle_text(text: str) -> str:
    t = text
    # Nueva lógica para surebets formato "💰 New surebet found!"
    if "💰 New surebet found!" in t:
        return format_new_surebet(t)
    
    if "Alerta de Surebets" in t or "💵 Rango Beneficio" in t:
        return format_surebets(t)
    if "Alerta de Middlebets" in t or "👑 Rango Valor Esperado" in t:
        return format_middlebets(t)
    return text

# ─────────────────────────────────────────────────────────────────────────────
# TELETHON + FASTAPI
# ─────────────────────────────────────────────────────────────────────────────
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
app = FastAPI(title="Multi-Forwarder: canales, grupos y bots (privado) con filtrado específico")

# Mapa: {origin_peer_id(int): dest_target(str|int)}
PAIRS = {}
# Para status/diagnóstico
LISTEN_IDS   = []  # peer ids
LISTEN_PEERS = []  # entidades (Channel/Chat/User)
# Orígenes que aplican filtrado (los de DEST_CHAT_1)
FILTER_ORIGINS = []
# Resuelto para comparación
DEST_CHAT_2_RESOLVED = None

@app.on_event("startup")
async def startup_event():
    await client.start()

    # Construcción de especificaciones (lista de (origenes[], destino))
    origin_dest_specs = []

    # Bloque destino 1
    if DEST_CHAT_1:
        csv1 = _split_csv(ORIGINS_DEST1)
        if csv1:
            origin_dest_specs.append((csv1, DEST_CHAT_1))
        if ORIGIN_CHAT_1:  # compatibilidad
            origin_dest_specs.append(([ORIGIN_CHAT_1], DEST_CHAT_1))

    # Bloque destino 2
    if DEST_CHAT_2:
        csv2 = _split_csv(ORIGINS_DEST2)
        if csv2:
            origin_dest_specs.append((csv2, DEST_CHAT_2))
        if ORIGIN_CHAT_2:  # compatibilidad
            origin_dest_specs.append(([ORIGIN_CHAT_2], DEST_CHAT_2))

    if not origin_dest_specs:
        logging.warning("No hay pares configurados. Define ORIGINS_DEST1/2 y/o ORIGIN_CHAT_1/2 con sus DEST_CHAT_1/2.")

    # Resolver entidades y construir PAIRS / LISTEN_PEERS
    pairs_local = {}
    peers_local = []
    ids_local   = []
    filter_origins_local = []

    dest_chat_1_resolved = _maybe_int(DEST_CHAT_1) if DEST_CHAT_1 else None
    global DEST_CHAT_2_RESOLVED
    DEST_CHAT_2_RESOLVED = _maybe_int(DEST_CHAT_2) if DEST_CHAT_2 else None

    for origins_list, dest_val in origin_dest_specs:
        dest_target = _maybe_int(dest_val)  # se usa tal cual en send_*
        # No hace falta resolver el destino (Telethon acepta @/id), resolvemos solo orígenes
        for origin in origins_list:
            try:
                origin_resolved = _maybe_int(origin)
                ent_o = await client.get_entity(origin_resolved)  # User/Channel/Chat
                o_peer = get_peer_id(ent_o)                      # int (p.ej. -100..., o id positivo en privados)

                pairs_local[o_peer] = dest_target
                peers_local.append(ent_o)  # importante: ENTIDADES para que Telethon detecte privados/bots
                ids_local.append(o_peer)

                # Si este origen va a DEST_CHAT_1, agregarlo a filter_origins
                if dest_target == dest_chat_1_resolved:
                    filter_origins_local.append(o_peer)
            except Exception as e:
                logging.error(f"Error resolviendo origen {origin}: {e}")

    global PAIRS, LISTEN_PEERS, LISTEN_IDS, FILTER_ORIGINS
    PAIRS = pairs_local
    LISTEN_PEERS = peers_local
    LISTEN_IDS = ids_local
    FILTER_ORIGINS = filter_origins_local

    logging.info(f"Pares configurados (peer ids): { {str(k): str(v) for k,v in PAIRS.items()} }")
    logging.info(f"Escuchando orígenes (peer ids): {LISTEN_IDS}")
    
    # Handler: acepta mensajes entrantes (incoming=True) de las ENTIDADES configuradas
    @client.on(events.NewMessage(chats=LISTEN_PEERS, incoming=True))
    async def handler(event):
        # Aceptamos canales, grupos y privados (incluye bots en privado)
        src_id = event.chat_id  # peer id numérico
        dest_default = PAIRS.get(src_id)

        logging.debug(
            f"NewMessage | chat_id={src_id} sender_id={event.sender_id} "
            f"is_channel={event.is_channel} is_group={event.is_group} is_private={event.is_private}"
        )

        if not dest_default:
            logging.warning(f"Origen no emparejado: {src_id} | known={LISTEN_IDS}")
            return

        # Evitar eco de mensajes salientes propios (por si el user escribe en origen)
        if event.out:
            return

        msg = event.message
        text = (msg.text or "").strip()

        # Determinar destinos basado en filtrado (solo para orígenes en FILTER_ORIGINS)
        dests = [dest_default]
        if src_id in FILTER_ORIGINS:
            if FILTER_KEYWORD in text and DEST_CHAT_3:
                dests = [_maybe_int(DEST_CHAT_3)]
                logging.debug(f"Filtrado 1 aplicado: {src_id} → {dests}")
            else:
                # Filtrado 2: bet365
                if FILTER_KEYWORD2.lower() in text.lower():
                    dests = [dest_default]
                else:
                    if DEST_CHAT_4:
                        dests.append(_maybe_int(DEST_CHAT_4))
                
                # Filtrado 3: winamax (similar al 2)
                if FILTER_KEYWORD3.lower() in text.lower():
                    dests = [dest_default]
                else:
                    if DEST_CHAT_5:
                        dests.append(_maybe_int(DEST_CHAT_5))

        # Modificar si alguno de los destinos es DEST_CHAT_2
        modified_text = text
        if any(dest == DEST_CHAT_2_RESOLVED for dest in dests) and text:
            modified_text = modify_text(text)

        # NUEVO SURE/MIDDLE: solo para orígenes de ORIGIN1 (FILTER_ORIGINS)
        if src_id in FILTER_ORIGINS and modified_text:
            new_text = modify_sure_middle_text(modified_text)
            if new_text != modified_text:
                modified_text = new_text

        try:
            for dest in dests:
                if msg.media:
                    buf = io.BytesIO()
                    # Nombre descriptivo si existe
                    buf.name = getattr(getattr(msg, "file", None), "name", None) or "file"
                    # Puede fallar si el origen tiene contenido protegido
                    await client.download_media(msg, file=buf)
                    buf.seek(0)
                    caption = modified_text if modified_text else ""
                    await client.send_file(dest, buf, caption=caption, force_document=FORCE_DOCUMENT)
                    logging.info(f"Media {src_id} → {dest} | msg_id={msg.id}")
                else:
                    if modified_text:
                        await client.send_message(dest, modified_text)
                        logging.info(f"Texto {src_id} → {dest} | msg_id={msg.id}")
                    else:
                        logging.info(f"Skip empty text | msg_id={msg.id}")
        except RPCError as e:
            logging.error(f"Fallo reenviando {src_id}→{dests} | msg_id={msg.id} | {type(e).__name__}: {e}")

    # Mantener el cliente vivo
    app.state.client_task = asyncio.create_task(client.run_until_disconnected())

@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "client_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await client.disconnect()

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"ok": True}

@app.head("/")
def root_head():
    return Response(status_code=200)

@app.get("/status")
def status():
    return {
        "connected": client.is_connected(),
        "pairs": {str(k): str(v) for k, v in PAIRS.items()},
        "listening_ids": [str(x) for x in LISTEN_IDS],
    }
