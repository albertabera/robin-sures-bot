
import os
import time
import undetected_chromedriver as uc

def main():
    print("🚀 Launching Undetected Browser for BetHero...")
    
    options = uc.ChromeOptions()
    # Adding arguments to further reduce bot detection footprint if needed
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    
    # Initialize the driver
    # use_subprocess=True is often recommended for stability
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    try:
        driver.get("https://app.betherosports.com/")
        print("\n" + "="*50)
        print("ACTION REQUIRED: Please log in to BetHero in the browser window.")
        print("Navigate to the 'Surebets' or 'Arb' page where the bets are listed.")
        print("IMPORTANT: Ensure some surebets are visible on the screen.")
        print("="*50 + "\n")
        
        input("👉 Press Enter here in the terminal once you are ready to capture the HTML...")
        
        print("📸 Capturing page source...")
        html = driver.page_source
        
        filename = "bethero_dump.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
            
        print(f"✅ HTML saved to {os.path.abspath(filename)}")
        print("The agent will now analyze this file to find the correct selectors.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("Closing browser in 5 seconds...")
        time.sleep(5)
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
