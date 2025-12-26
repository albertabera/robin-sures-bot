import asyncio
import threading
import logging
import sys
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure Logging for Unified Output
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CombinedBot")

# Import Modules
try:
    import bethero_scraper
    import filter_bot
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)

# --- Dummy Web Server for Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        return  # Silence server logs

def run_web_server():
    """
    Starts a dummy web server to satisfy Render's requirement of binding to $PORT.
    Without this, Render detects the app as 'failed' and kills it.
    """
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🌍 Web server started on port {port} (satisfying Render requirements)")
    server.serve_forever()
# -----------------------------------

def run_scraper_thread():
    """
    Runs the scraper in a loop. If it crashes (e.g., Selenium timeout),
    it waits 10s and restarts completely.
    """
    while True:
        try:
            logger.info("🚀 Starting Scraper Logic...")
            # Run the scraper's main function
            asyncio.run(bethero_scraper.main())
        except Exception as e:
            logger.error(f"❌ Scraper Thread Crashed: {e}")
            logger.info("🔄 Restarting Scraper in 10 seconds...")
            time.sleep(10)

def run_bot_main():
    logger.info("🤖 Starting Telegram Bot (Main Thread)...")
    try:
        filter_bot.run_bot()
    except Exception as e:
        logger.error(f"❌ Bot Crashed: {e}")

if __name__ == "__main__":
    print("-" * 50)
    print("   ROBINSURESHOOD DISTRIBUTION SYSTEM   ")
    print("          Cloud Deployment Mode         ")
    print("-" * 50)
    
    # 1. Start Web Server (Thread) - CRITICAL for Render
    web_thread = threading.Thread(target=run_web_server, daemon=True, name="WebServer")
    web_thread.start()

    # 2. Start Scraper (Thread) with Auto-Restart logic
    scraper_t = threading.Thread(target=run_scraper_thread, daemon=True, name="ScraperWorker")
    scraper_t.start()
    
    # Give it a second to initialize DB
    time.sleep(2)
    
    # 3. Start Bot in Main Thread (Blocking)
    run_bot_main()
