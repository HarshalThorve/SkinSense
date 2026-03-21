import sqlite3
import os

db_path = r'c:\Users\kunal\OneDrive\Desktop\College\MiniProject\miniproject\instance\database.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add missing columns if they don't exist
    columns_to_add = [
        ('ai_pimples', 'BOOLEAN'),
        ('ai_oily', 'BOOLEAN'),
        ('ai_spots', 'BOOLEAN'),
        ('timestamp', 'DATETIME'),
        ('skin_health_score', 'INTEGER')
    ]
    
    cursor.execute('PRAGMA table_info(skin_report)')
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to skin_report table...")
            cursor.execute(f'ALTER TABLE skin_report ADD COLUMN {col_name} {col_type}')
    
    conn.commit()
    conn.close()
    print("Database migration completed successfully.")
else:
    print("Database file not found. It will be created on next run.")
