import sqlite3

conn = sqlite3.connect('activity_log.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
conn.close()

print("Tables in database:", tables)
