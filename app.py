import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
app.secret_key = 'chave_super_secreta_ti_v2' # Mudei a chave
UPLOAD_FOLDER = 'uploads'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'mkv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Separador usado para guardar múltiplos arquivos no banco
DB_FILE_SEPARATOR = ';' 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Credenciais Admin
ADMIN_USER = 'admin'
ADMIN_PASS = '123456'

def get_db_connection():
    conn = sqlite3.connect('helpdesk_v2.db') # Mudei o nome do banco para v2
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # A estrutura é a mesma, mas agora os campos _filename guardarão strings longas
    # separadas por ponto e vírgula. Ex: "img1.jpg;img2.png"
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            prioridade TEXT NOT NULL,
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

# --- FUNÇÃO AUXILIAR PARA PROCESSAR MÚLTIPLOS UPLOADS ---
def processar_uploads(lista_arquivos, extensoes_permitidas, prefixo):
    filenames_salvos = []
    
    for file in lista_arquivos:
        if file and allowed_file(file.filename, extensoes_permitidas):
            safe_name = secure_filename(file.filename)
            # Gera nome único para cada arquivo
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
            filename = f"{prefixo}_{timestamp}_{safe_name}"
            
            # Salva o arquivo
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filenames_salvos.append(filename)
            
    # Retorna uma string única separada por ';' ou None se não salvou nada
    return DB_FILE_SEPARATOR.join(filenames_salvos) if filenames_salvos else None


# --- ROTAS PÚBLICAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/abrir-chamado', methods=('GET', 'POST'))
def abrir_chamado():
    if request.method == 'POST':
        nome = request.form['nome']
        prioridade = request.form['prioridade']
        descricao = request.form['descricao']
        
        # Pega todos os arquivos do campo único "anexos[]"
        arquivos_mistos = request.files.getlist('anexos[]')
        
        lista_imagens = []
        lista_videos = []

        # Separa o que é imagem do que é vídeo automaticamente
        for file in arquivos_mistos:
            if file.filename == '': continue # Pula arquivos vazios
            
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if ext in ALLOWED_IMAGE_EXTENSIONS:
                lista_imagens.append(file)
            elif ext in ALLOWED_VIDEO_EXTENSIONS:
                lista_videos.append(file)

        # Processa e salva as listas separadas
        imgs_string_db = processar_uploads(lista_imagens, ALLOWED_IMAGE_EXTENSIONS, 'IMG')
        vids_string_db = processar_uploads(lista_videos, ALLOWED_VIDEO_EXTENSIONS, 'VID')

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO chamados (nome, prioridade, descricao, imagem_filename, video_filename) VALUES (?, ?, ?, ?, ?)',
            (nome, prioridade, descricao, imgs_string_db, vids_string_db)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('success'))

    return render_template('report.html')

@app.route('/sucesso')
def success():
    return render_template('success.html')

# --- ROTAS ADMIN E UTILITÁRIAS ---

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
    conn.close()
    # Precisamos passar o separador para o template usar no 'split'
    return render_template('admin.html', chamados=chamados, separator=DB_FILE_SEPARATOR)

@app.route('/status/<int:id>/<novo_status>')
def mudar_status(id, novo_status):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('UPDATE chamados SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_chamado(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    
    # Busca os dados antes de apagar
    chamado = conn.execute('SELECT imagem_filename, video_filename FROM chamados WHERE id = ?', (id,)).fetchone()
    
    if chamado:
        # Função interna para apagar múltiplos arquivos de uma string "file1;file2"
        def apagar_arquivos_fisicos(string_filenames):
            if string_filenames:
                for filename in string_filenames.split(DB_FILE_SEPARATOR):
                    p = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(p):
                        os.remove(p)

        # Apaga imagens e vídeos físicos
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