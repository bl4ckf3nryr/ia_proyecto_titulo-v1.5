"""Añade la columna usuario_id a la tabla camaras sin perder datos."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "login.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("PRAGMA table_info(camaras)")
cols = [c[1] for c in cur.fetchall()]
print("Columnas actuales:", cols)

if "usuario_id" not in cols:
    cur.execute("ALTER TABLE camaras ADD COLUMN usuario_id INTEGER")
    print("✓ Columna usuario_id añadida.")
else:
    print("✓ La columna ya existía.")

# Asignar todas las cámaras viejas al primer supervisor de la BD
cur.execute("SELECT id FROM usuarios WHERE rol='supervisor' ORDER BY id LIMIT 1")
row = cur.fetchone()
if row:
    cur.execute("UPDATE camaras SET usuario_id = ? WHERE usuario_id IS NULL", (row[0],))
    print(f"✓ Cámaras sin dueño asignadas al supervisor id={row[0]}")

conn.commit()
conn.close()
print("Migración completa.")