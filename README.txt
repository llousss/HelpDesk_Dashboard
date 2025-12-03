Como rodar o sistema
Instale o Python se não tiver.

Abra o terminal (CMD ou PowerShell) na pasta do projeto.

Instale o Flask (o framework web):"pip install flask"

Rode o aplicativo:"python app.py"

Acesse no seu navegador: http://localhost:5000 (ou http://SEU_IP:5000 para que outros computadores da rede possam acessar).

Acesso na Rede: Para que outros funcionários acessem, você deve passar o IP da sua máquina. Exemplo: http://192.168.1.50:5000. O código já está configurado (host='0.0.0.0') para permitir isso.

Banco de Dados: O arquivo helpdesk_v3.db será criado automaticamente na primeira execução e guardará todos os votos.

Vídeos: Os vídeos pesados podem encher o disco rápido. Monitore a pasta uploads.


Acesse http://localhost:5000/admin (ou clique no link se criar um botão na home).

Usuário: admin

Senha: 123456
