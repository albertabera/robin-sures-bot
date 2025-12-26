import os
import json
import time
import undetected_chromedriver as uc

def main():
    print("🍪 Cookie Extractor for BetHero")
    print("-------------------------------")
    print("This script will open a browser.")
    print("1. Log in to BetHero.")
    print("2. Navigate to the Surebets page.")
    print("3. Return here and press ENTER.")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    try:
        driver.get("https://app.betherosports.com/surebets")
        
        input("\n👉 Press ENTER after you have successfully logged in...")
        
        print("Extracting cookies...")
        cookies = driver.get_cookies()
        
        # Save to file
        with open("bethero_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)
            
        # Also print minified for Env Var
        minified = json.dumps(cookies)
        print("\n" + "="*50)
        print("SUCCESS! Cookies saved to 'bethero_cookies.json'.")
        print("For Render, create an environment variable called 'BETHERO_COOKIES' and paste this content:")
        print("-" * 20)
        print(minified)
        print("-" * 20)
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
