import sqlite3
import os

DB_NAME = "surebets.db"

def check_schema():
    if not os.path.exists(DB_NAME):
        print(f"❌ DB {DB_NAME} not found!")
        return

    print(f"📂 checking {DB_NAME}...")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check columns in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("\n📋 'users' Table Columns:")
        found_sports = False
        for col in columns:
            cid, name, type, notnull, dflt_value, pk = col
            print(f"  - {name} ({type})")
            if name == 'sports':
                found_sports = True
                
        if found_sports:
            print("\n✅ 'sports' column FOUND.")
        else:
            print("\n❌ 'sports' column MISSING!")
            
        conn.close()
    except Exception as e:
        print(f"\n❌ Error inspecting DB: {e}")

if __name__ == "__main__":
    check_schema()
