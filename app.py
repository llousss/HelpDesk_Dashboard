import os
import sqlite3
import smtplib
import math  # Importação para cálculos matemáticos (arredondar páginas)
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename
from threading import Thread 
from dotenv import load_dotenv

load_dotenv()

# Inicializa o framework Flask
app = Flask(__name__)

# --- CONFIGURAÇÕES GERAIS ---
# Chave de segurança para proteger cookies e dados de sessão
app.secret_key = os.getenv('YOUR_SECRET_KEY')

# Define a pasta onde fotos e vídeos serão salvos
UPLOAD_FOLDER = 'uploads'

# Extensões permitidas para segurança (evita vírus .exe, scripts .py, etc.)
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'mkv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Caractere separador para salvar múltiplos arquivos numa única coluna de texto no BD
DB_FILE_SEPARATOR = ';' 

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_HOST = 'smtp.gmail.com'      # Servidor SMTP do Google
EMAIL_PORT = 587                   # Porta padrão para TLS
EMAIL_USER = 'YOUR_EMAIL_USER' 
EMAIL_PASS = os.getenv('EMAIL_SENHA') # Senha de aplicativo (App Password)

# Aplica configurações no app Flask e cria a pasta de uploads se não existir
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Credenciais de acesso ao Painel Admin (Login Hardcoded)
ADMIN_USER = 'your_user_admin'
ADMIN_PASS = 'your_password'

# --- BANCO DE DADOS (SQLite) ---

def get_db_connection():
    """Cria conexão com o arquivo do banco de dados."""
    conn = sqlite3.connect('helpdesk.db') 
    # Row Factory permite acessar colunas pelo nome (ex: item['email'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Cria a tabela 'chamados' se ela ainda não existir."""
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

# --- FUNÇÕES UTILITÁRIAS ---

def allowed_file(filename, extensions):
    """Verifica se a extensão do arquivo é válida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

def processar_uploads(lista_arquivos, extensoes_permitidas, prefixo):
    """
    Salva múltiplos arquivos na pasta uploads e retorna uma string
    com os nomes separados por ponto e vírgula para o banco.
    """
    filenames_salvos = []
    
    for file in lista_arquivos:
        # Se o arquivo existe e a extensão é permitida
        if file and allowed_file(file.filename, extensoes_permitidas):
            # Limpa o nome (remove caracteres especiais perigosos)
            safe_name = secure_filename(file.filename)
            # Cria timestamp para evitar arquivos com mesmo nome
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
            filename = f"{prefixo}_{timestamp}_{safe_name}"
            
            # Salva fisicamente
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filenames_salvos.append(filename)
            
    # Retorna string formatada ou None
    return DB_FILE_SEPARATOR.join(filenames_salvos) if filenames_salvos else None

# --- FUNÇÕES DE DISPARO DE E-MAIL (ASSÍNCRONAS) ---

def enviar_email_confirmacao(destinatario, nome_usuario, id_chamado, descricao_texto):
    """Envia e-mail de confirmação de abertura."""
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
    """Notifica que o chamado está 'Em Andamento'."""
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
    """Notifica que o chamado foi 'Concluído'."""
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

# --- ROTAS PÚBLICAS ---

@app.route('/favicon.ico')
def favicon():
    """Rota para servir o ícone do site e evitar erro 404 no console."""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    """Página inicial (Menu)."""
    return render_template('index.html')

@app.route('/abrir-chamado', methods=('GET', 'POST'))
def abrir_chamado():
    """Formulário de abertura de chamados."""
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

        # Envio Assíncrono com Thread
        Thread(target=enviar_email_confirmacao, args=(email, nome, novo_id, descricao)).start()

        return redirect(url_for('success'))

    return render_template('report.html')

@app.route('/sucesso')
def success():
    """Página de agradecimento."""
    return render_template('success.html')

# --- ROTAS ADMINISTRATIVAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de login do administrador."""
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
    """Desloga o administrador."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    """Painel principal do administrador com BUSCA e PAGINAÇÃO."""
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # 1. Configurações de Paginação
    PER_PAGE = 10 # Quantidade de chamados por página
    page = request.args.get('page', 1, type=int) # Pega página atual da URL (padrão 1)
    offset = (page - 1) * PER_PAGE
    
    # 2. Busca e Filtro
    busca = request.args.get('q')
    
    if busca:
        # Se tem busca, filtramos
        termo = f'%{busca}%'
        where_clause = "WHERE nome LIKE ? OR email LIKE ? OR descricao LIKE ? OR id LIKE ?"
        params = (termo, termo, termo, termo)
        
        # Conta total de resultados para essa busca (para saber quantas páginas teremos)
        total_registros = conn.execute(f'SELECT COUNT(*) FROM chamados {where_clause}', params).fetchone()[0]
        
        # Busca os dados paginados filtrados
        query = f'''
            SELECT * FROM chamados 
            {where_clause}
            ORDER BY CASE WHEN status="Pendente" THEN 1 WHEN status="Em Andamento" THEN 2 ELSE 3 END, data_hora DESC
            LIMIT ? OFFSET ?
        '''
        params_paginado = params + (PER_PAGE, offset)
        chamados = conn.execute(query, params_paginado).fetchall()
        
    else:
        # Sem busca (Padrão) - Conta tudo
        total_registros = conn.execute('SELECT COUNT(*) FROM chamados').fetchone()[0]
        
        # Busca tudo paginado
        query = '''
            SELECT * FROM chamados 
            ORDER BY CASE WHEN status="Pendente" THEN 1 WHEN status="Em Andamento" THEN 2 ELSE 3 END, data_hora DESC
            LIMIT ? OFFSET ?
        '''
        chamados = conn.execute(query, (PER_PAGE, offset)).fetchall()

    # Calcula número total de páginas (arredonda para cima com math.ceil)
    total_pages = math.ceil(total_registros / PER_PAGE)

    # 3. Contadores do Cabeçalho (Contagem Global Independente da Paginação)
    # Fazemos queries específicas para contar o total de cada status no banco todo
    pendentes = conn.execute("SELECT COUNT(*) FROM chamados WHERE status='Pendente'").fetchone()[0]
    andamento = conn.execute("SELECT COUNT(*) FROM chamados WHERE status='Em Andamento'").fetchone()[0]
    concluidos = conn.execute("SELECT COUNT(*) FROM chamados WHERE status='Concluído'").fetchone()[0]
    
    conn.close()
    
    # Passa TODAS as variáveis para o HTML
    return render_template('admin.html', 
                           chamados=chamados, 
                           separator=DB_FILE_SEPARATOR,
                           pendentes=pendentes,
                           andamento=andamento,
                           concluidos=concluidos,
                           page=page,           
                           total_pages=total_pages, 
                           busca=busca)

@app.route('/status/<int:id>/<novo_status>')
def mudar_status(id, novo_status):
    """Muda o status do chamado e dispara emails de notificação."""
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Busca dados do usuário antes de atualizar
    chamado = conn.execute('SELECT nome, email, descricao FROM chamados WHERE id = ?', (id,)).fetchone()
    
    # Atualiza Status
    conn.execute('UPDATE chamados SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()
    
    # Envio Assíncrono de notificações
    if novo_status == 'Em Andamento' and chamado:
        Thread(target=enviar_email_em_analise, 
               args=(chamado['email'], chamado['nome'], id, chamado['descricao'])).start()
    
    if novo_status == 'Concluído' and chamado:
        Thread(target=enviar_email_conclusao, 
               args=(chamado['email'], chamado['nome'], id, chamado['descricao'])).start()
        
    return redirect(url_for('admin'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_chamado(id):
    """Deleta chamado e seus arquivos físicos."""
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    
    # Recupera nomes dos arquivos
    chamado = conn.execute('SELECT imagem_filename, video_filename FROM chamados WHERE id = ?', (id,)).fetchone()
    
    if chamado:
        # Função interna para limpar arquivos do disco
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
    """Rota segura para servir os arquivos de upload."""
    if not session.get('logged_in'): return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db() # Garante que o banco existe ao iniciar
    app.run(debug=True, host='0.0.0.0', port=5000)
