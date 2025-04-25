import sqlite3
from passlib.context import CryptContext
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
admin_email = 'bert@example.com'
hashed_password = pwd_context.hash('bert123')  # Replace 'your_password'

conn = sqlite3.connect("../sql_app.db")  # Replace with your desired database file name (or :memory:)
cur = conn.cursor()
cur.execute(
    "CREATE TABLE IF NOT EXISTS admins (admin_id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, hashed_password TEXT, role TEXT, organization_id INTEGER)"  # Create table if it doesn't exist
)
#   cur.execute(
#       "INSERT INTO admins (name, email, hashed_password, role, organization_id) VALUES (?, ?, ?, ?, ?)",
#       ('Test Admin', 'admin@example.com', hashed_password, 'superadmin', 1)  # Example data
#   )
# conn.commit()
# conn.close()

# Check if the email already exists.
cur.execute("SELECT email FROM admins WHERE email = ?", (admin_email,))  # Use the email you are trying to insert
existing_email = cur.fetchone()

if existing_email:
    print(f"Error: Email address '{admin_email}' already exists in the database.") #change email
else:
    # Only insert if the email doesn't exist
    cur.execute(
        "INSERT INTO admins (name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Test bert', admin_email, hashed_password, 'superadmin')  # Example data
    )
    conn.commit()
    print("Admin user created successfully.")
conn.close()
