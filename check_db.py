import sqlite3

connection = sqlite3.connect("instance/assigneval.db")
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(submission)")

columns = [column[1] for column in cursor.fetchall()]

if "marks" not in columns:
    cursor.execute(
        "ALTER TABLE submission ADD COLUMN marks INTEGER"
    )
    print("Marks column added.")

if "feedback" not in columns:
    cursor.execute(
        "ALTER TABLE submission ADD COLUMN feedback TEXT"
    )
    print("Feedback column added.")

connection.commit()

print("Database updated successfully!")

connection.close()