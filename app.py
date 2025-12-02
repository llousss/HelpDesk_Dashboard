from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from datetime import datetime, date, timedelta  # <--- Adicione timedelta aqui
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
app.secret_key = 'chave_super_secreta_da_empresa'  # Necessário para o login funcionar
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm'}

# Credenciais de Admin (Pode alterar aqui)
ADMIN_USER = 'admin'
ADMIN_PASS = '123456'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- BANCO DE DADOS ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            setor TEXT NOT NULL,
            outros_afetados TEXT NOT NULL,
            modulo TEXT NOT NULL,
            video_filename TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROTAS PÚBLICAS ---

@app.route('/')
def index():
    # 1. Descobrir a hora atual
    agora = datetime.now()
    hora_atual = agora.hour
    
    # 2. Definir os horários de reset (turnos de 4 horas)
    # Incluí 2h e 22h para cobrir a madrugada
    checkpoints = [2, 6, 10, 14, 18, 22]
    
    # 3. Encontrar o checkpoint mais recente
    # Começamos assumindo que é o último do dia anterior (22h) caso seja 1 da manhã
    horario_corte = 22 
    dia_referencia = agora.date()

    # Procura qual o maior checkpoint que é menor ou igual a hora atual
    # Ex: Se são 11:30, o checkpoint é 10. Se são 17:00, é 14.
    checkpoint_atual = [h for h in checkpoints if h <= hora_atual]
    
    if checkpoint_atual:
        horario_corte = max(checkpoint_atual)
    else:
        # Se a lista estiver vazia (ex: são 01:00 da manhã),
        # o corte foi às 22h do dia anterior
        horario_corte = 22
        dia_referencia = agora.date() - timedelta(days=1)

    # 4. Criar a data/hora completa de início do filtro
    data_inicio_filtro = datetime(
        dia_referencia.year, 
        dia_referencia.month, 
        dia_referencia.day, 
        horario_corte, 0, 0
    )

    conn = get_db_connection()
    
    # 5. A Query agora conta apenas registros MAIORES (depois) que o horário de corte
    reports_turno = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE data_hora >= ?", 
        (data_inicio_filtro,)
    ).fetchone()[0]
    
    conn.close()
    
    # Passamos também o horário de início para mostrar na tela (opcional)
    msg_turno = f"Desde às {horario_corte}h"
    
    return render_template('index.html', count=reports_turno, msg_turno=msg_turno)

@app.route('/reportar', methods=('GET', 'POST'))
def report():
    if request.method == 'POST':
        nome = request.form['nome']
        setor = request.form['setor']
        outros = request.form['outros']
        modulo = request.form['modulo']
        video = request.files.get('video')
        
        filename = None
        if video and allowed_file(video.filename):
            filename = secure_filename(video.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO reports (nome, setor, outros_afetados, modulo, video_filename) VALUES (?, ?, ?, ?, ?)',
            (nome, setor, outros, modulo, filename)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('success'))

    return render_template('report.html')

@app.route('/sucesso')
def success():
    return render_template('success.html')

# --- ÁREA ADMINISTRATIVA ---

# Página de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        usuario = request.form['username']
        senha = request.form['password']
        
        if usuario == ADMIN_USER and senha == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            erro = 'Usuário ou senha incorretos.'
            
    return render_template('login.html', erro=erro)

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Painel Admin (Protegido)
@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # Pega todos os reportes, do mais recente para o mais antigo
    reports = conn.execute('SELECT * FROM reports ORDER BY data_hora DESC').fetchall()
    conn.close()
    return render_template('admin.html', reports=reports)

# Rota para baixar/ver os vídeos (Protegida)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Função deletar
@app.route('/delete/<int:id>', methods=['POST'])
def delete_report(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # 1. Primeiro, descobrimos se tem vídeo associado para apagar o arquivo
    report = conn.execute('SELECT video_filename FROM reports WHERE id = ?', (id,)).fetchone()
    
    if report and report['video_filename']:
        caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], report['video_filename'])
        # Tenta apagar o arquivo físico
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

    # 2. Agora apagamos o registro do banco
    conn.execute('DELETE FROM reports WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)