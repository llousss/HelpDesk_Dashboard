Como rodar o sistema
Instale o Python se não tiver.

Abra o terminal (CMD ou PowerShell) na pasta do projeto.

Instale o Flask (o framework web):"pip install flask"

Crie um arquivo .env na raiz do projeto seguindo o modelo:

SECRET_KEY=sua_chave_secreta_aqui
EMAIL_SENHA=senha_de_app_do_google
# Informações para acessar a página ADMIN
ADMIN_USER=your_user
ADMIN_SENHA=your_password

Entre na pasta do arquivo pelo CMD e execute:"python app.py" ou "py app.py"

Acesse no seu navegador: http://localhost (ou http://SEU_IP para que outros computadores da rede possam acessar).

Acesso na Rede: Para que outros funcionários acessem, você deve passar o IP da sua máquina. Exemplo: http://192.168.1.50. O código já está configurado (host='0.0.0.0') para permitir isso.

Banco de Dados: O arquivo helpdesk.db será criado automaticamente na primeira execução e guardará todos os chamados.

Vídeos: Os vídeos pesados podem encher o disco rápido. Monitore a pasta uploads.


Acesse http://localhost/admin ou(ou clique no link se criar um botão na home).

Usuário: your_user

Senha: your_password

IMPORTANTE:
Para validar o recebimento e envio de e-mail automático pelo código você deverá criar um acesso de senha de app do google. Apoio: "https://support.google.com/accounts/answer/185833?hl=pt-BR"
