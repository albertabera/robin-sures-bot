import sqlite3
import pandas as pd
import os

DB_NAME = "surebets.db"

def main():
    if not os.path.exists(DB_NAME):
        print(f"❌ Database '{DB_NAME}' not found.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        
        # 1. Show summary count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM surebets")
        count = cursor.fetchone()[0]
        print(f"📊 Total Surebets found: {count}")
        
        if count == 0:
            print("Database is empty yet. Waiting for the scraper to find bets...")
            conn.close()
            return

        # 2. Show last 5 bets
        print("\n🕒 Last 5 Bets:")
        df = pd.read_sql_query("SELECT found_at, event, profit, league FROM surebets ORDER BY id DESC LIMIT 5", conn)
        print(df.to_string(index=False))
        
        # 3. Export to CSV option
        export = input("\n💾 Do you want to export ALL to 'surebets_export.csv'? (y/n): ")
        if export.lower() == 'y':
            df_all = pd.read_sql_query("SELECT * FROM surebets ORDER BY id DESC", conn)
            df_all.to_csv("surebets_export.csv", index=False)
            print(f"✅ Exported {len(df_all)} rows to 'surebets_export.csv'.")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error reading DB: {e}")

if __name__ == "__main__":
    main()
