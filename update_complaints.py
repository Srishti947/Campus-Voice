import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE complaints
        ADD COLUMN user_email TEXT
    """)

    print("✅ user_email column added.")

except sqlite3.OperationalError:
    print("ℹ️ Column already exists.")

conn.commit()
conn.close()