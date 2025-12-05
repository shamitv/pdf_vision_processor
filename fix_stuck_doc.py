
import sqlite3
import os

DB_PATH = "db.sqlite3"

def unblock_document(doc_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for stuck versions
    cursor.execute("SELECT id, version_number, status FROM document_versions WHERE document_id = ? AND status = 'PROCESSING'", (doc_id,))
    stuck = cursor.fetchall()
    
    if stuck:
        print(f"Found stuck versions: {stuck}")
        # Update to FAILED
        cursor.execute("UPDATE document_versions SET status = 'FAILED' WHERE document_id = ? AND status = 'PROCESSING'", (doc_id,))
        conn.commit()
        print("Updated status to FAILED.")
    else:
        print("No stuck versions found.")
        
    conn.close()

if __name__ == "__main__":
    unblock_document(5)
