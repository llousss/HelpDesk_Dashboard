import os
import sqlite3
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURAÇÕES DO SITE ---
app.secret_key = 'chave_super_secreta_ti_v3'
UPLOAD_FOLDER = 'uploads'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'mkv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
DB_FILE_SEPARATOR = ';' 

# --- CONFIGURAÇÕES DE EMAIL (PREENCHA AQUI) ---
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'EMAIL_USER' 
EMAIL_PASS = 'SENHA_GOOGLE_SENHAS' # <--- VERIFIQUE SE SUA SENHA ESTÁ AQUI

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Credenciais Admin
ADMIN_USER = 'admin'
ADMIN_PASS = 'password'

def get_db_connection():
    conn = sqlite3.connect('helpdesk_v3.db') 
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            descricao TEXT NOT NULL,
            imagem_filename TEXT, 
            video_filename TEXT,
            status TEXT DEFAULT 'Pendente',
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

def processar_uploads(lista_arquivos, extensoes_permitidas, prefixo):
    filenames_salvos = []
    for file in lista_arquivos:
        if file and allowed_file(file.filename, extensoes_permitidas):
            safe_name = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
            filename = f"{prefixo}_{timestamp}_{safe_name}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filenames_salvos.append(filename)
    return DB_FILE_SEPARATOR.join(filenames_salvos) if filenames_salvos else None

# --- FUNÇÕES DE EMAIL ---

def enviar_email_confirmacao(destinatario, nome_usuario, id_chamado, descricao_texto):
    try:
        msg = EmailMessage()
        msg.set_content(f"""
Olá, {nome_usuario}!

Recebemos seu chamado de suporte (ID: #{id_chamado}).
Nossa equipe de TI já foi notificada e em breve iniciará o atendimento.

Descrição do problema reportado:
"{descricao_texto}"

Atenciosamente,
Equipe de TI
        """)

        msg['Subject'] = f'Confirmacao de Chamado #{id_chamado}'
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Email de confirmação enviado para {destinatario}")
        
    except Exception as e:
        print(f"ERRO AO ENVIAR EMAIL: {e}")

def enviar_email_em_analise(destinatario, nome_usuario, id_chamado, descricao_texto):
    try:
        msg = EmailMessage()
        msg.set_content(f"""
Olá, {nome_usuario}!

Seu chamado de suporte (ID: #{id_chamado}) entrou em análise.
Um técnico da equipe de TI já está trabalhando na solução do seu problema neste momento.

Você será notificado assim que o chamado for concluído.

Descrição do problema reportado:
"{descricao_texto}"

Atenciosamente,
Equipe de TI
        """)

        msg['Subject'] = f'Chamado #{id_chamado} em Analise'
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Email de análise enviado para {destinatario}")
        
    except Exception as e:
        print(f"ERRO AO ENVIAR EMAIL DE ANALISE: {e}")

def enviar_email_conclusao(destinatario, nome_usuario, id_chamado, descricao_texto):
    try:
        msg = EmailMessage()
        msg.set_content(f"""
Olá, {nome_usuario}!

Seu chamado de suporte (ID: #{id_chamado}) foi concluído pela nossa equipe de TI.

Caso o problema persista ou tenha alguma dúvida, por favor, abra um novo chamado.

Descrição do problema reportado:
"{descricao_texto}"

Atenciosamente,
Equipe de TI
        """)

        msg['Subject'] = f'Chamado #{id_chamado} Concluído'
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Email de conclusão enviado para {destinatario}")
        
    except Exception as e:
        print(f"ERRO AO ENVIAR EMAIL DE CONCLUSÃO: {e}")

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/abrir-chamado', methods=('GET', 'POST'))
def abrir_chamado():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        descricao = request.form['descricao']
        
        arquivos_mistos = request.files.getlist('anexos[]')
        lista_imagens = []
        lista_videos = []

        for file in arquivos_mistos:
            if file.filename == '': continue
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext in ALLOWED_IMAGE_EXTENSIONS:
                lista_imagens.append(file)
            elif ext in ALLOWED_VIDEO_EXTENSIONS:
                lista_videos.append(file)

        imgs_string_db = processar_uploads(lista_imagens, ALLOWED_IMAGE_EXTENSIONS, 'IMG')
        vids_string_db = processar_uploads(lista_videos, ALLOWED_VIDEO_EXTENSIONS, 'VID')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO chamados (nome, email, descricao, imagem_filename, video_filename) VALUES (?, ?, ?, ?, ?)',
            (nome, email, descricao, imgs_string_db, vids_string_db)
        )
        conn.commit()
        
        novo_id = cursor.lastrowid
        conn.close()

        enviar_email_confirmacao(email, nome, novo_id, descricao)

        return redirect(url_for('success'))

    return render_template('report.html')

@app.route('/sucesso')
def success():
    return render_template('success.html')

# --- ROTAS ADMIN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            erro = 'Credenciais inválidas'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db_connection()
    chamados = conn.execute('SELECT * FROM chamados ORDER BY CASE WHEN status="Pendente" THEN 1 WHEN status="Em Andamento" THEN 2 ELSE 3 END, data_hora DESC').fetchall()
    
    # --- CÁLCULO DOS TOTAIS ---
    pendentes = sum(1 for c in chamados if c['status'] == 'Pendente')
    andamento = sum(1 for c in chamados if c['status'] == 'Em Andamento')
    concluidos = sum(1 for c in chamados if c['status'] == 'Concluído')
    
    conn.close()
    
    return render_template('admin.html', 
                           chamados=chamados, 
                           separator=DB_FILE_SEPARATOR,
                           pendentes=pendentes,
                           andamento=andamento,
                           concluidos=concluidos)

@app.route('/status/<int:id>/<novo_status>')
def mudar_status(id, novo_status):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Recupera os dados
    chamado = conn.execute('SELECT nome, email, descricao FROM chamados WHERE id = ?', (id,)).fetchone()
    
    conn.execute('UPDATE chamados SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()
    
    if novo_status == 'Em Andamento' and chamado:
        enviar_email_em_analise(chamado['email'], chamado['nome'], id, chamado['descricao'])
    
    if novo_status == 'Concluído' and chamado:
        enviar_email_conclusao(chamado['email'], chamado['nome'], id, chamado['descricao'])
        
    return redirect(url_for('admin'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_chamado(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    
    chamado = conn.execute('SELECT imagem_filename, video_filename FROM chamados WHERE id = ?', (id,)).fetchone()
    
    if chamado:
        def apagar_arquivos_fisicos(string_filenames):
            if string_filenames:
                for filename in string_filenames.split(DB_FILE_SEPARATOR):
                    p = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(p): os.remove(p)

        apagar_arquivos_fisicos(chamado['imagem_filename'])
        apagar_arquivos_fisicos(chamado['video_filename'])

    conn.execute('DELETE FROM chamados WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('logged_in'): return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
