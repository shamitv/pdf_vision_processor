
import sqlite3
import os

DB_PATH = "db.sqlite3"

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(pages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "status" not in columns:
            print("Adding status column to pages table...")
            # Use uppercase PENDING
            cursor.execute("ALTER TABLE pages ADD COLUMN status VARCHAR DEFAULT 'PENDING'")
        else:
            # Fix existing lowercase values
            print("Fixing lowercase status values...")
            cursor.execute("UPDATE pages SET status = 'PENDING' WHERE status = 'pending'")
            
        if "error_message" not in columns:
            print("Adding error_message column to pages table...")
            cursor.execute("ALTER TABLE pages ADD COLUMN error_message TEXT")
            
        conn.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
