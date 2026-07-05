import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        CREATE TABLE supports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            user_email TEXT
        )
    """)
    print("✅ Supports table created.")

except sqlite3.OperationalError:
    print("ℹ️ Supports table already exists.")

conn.commit()
conn.close()