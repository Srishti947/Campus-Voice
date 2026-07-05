import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

email = "santoskumar26682@gmail.com"   # Replace with your email

cursor.execute(
    "UPDATE users SET is_admin = 1 WHERE email = ?",
    (email,)
)

conn.commit()

if cursor.rowcount > 0:
    print("✅ Admin created successfully!")
else:
    print("❌ No user found with that email.")

conn.close()