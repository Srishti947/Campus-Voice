import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN is_admin INTEGER DEFAULT 0
    """)
    print("✅ is_admin column added successfully!")

except sqlite3.OperationalError:
    print("ℹ️ is_admin column already exists.")

conn.commit()
conn.close()