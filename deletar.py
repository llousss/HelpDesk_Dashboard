import sqlite3

# Conecta no banco (verifique se o nome é 'database.db' ou 'dados.sql')
conn = sqlite3.connect('dados.sql') 
cursor = conn.cursor()

# --- CONFIGURAÇÃO ---
id_para_deletar = 1  # <--- Coloque o ID aqui
# --------------------

try:
    cursor.execute("DELETE FROM reports WHERE id = ?", (id_para_deletar,))
    conn.commit()
    if cursor.rowcount > 0:
        print(f"Sucesso! O reporte ID {id_para_deletar} foi deletado.")
    else:
        print(f"Nenhum reporte encontrado com o ID {id_para_deletar}.")
except Exception as e:
    print(f"Erro: {e}")
finally:
    conn.close()