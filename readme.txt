################### DEPLOY PROD ########################################################################################################################
- CRIAR SERVIDOR 
- CRIAR BANCO DE DADOS COM USER, NAME, SENHA E HOST 
- PROJETO LOCAL LIMPAR CACHE, MIGRACOES (FAZER COM E SEM O VENV)
- EXCLUIR DBSQLITE

-limpar cache
Get-ChildItem -Recurse __pycache__ | Remove-Item -Force -Recurse

-limpar migracoes (sem venv)
Get-ChildItem -Include 0*.py -Recurse -File | ForEach-Object { Remove-Item $_.FullName }


-limpar arquivos pdf, jpeg, png do ambiente
Get-ChildItem -Path . -Recurse -Include *.pdf,*.png,*.jpeg | Remove-Item -Force




- CONFIGURAR DB NO SETTINGS, ALOWED HOST, COMENTAR ONDE INSTALL APS DE DESENVOLVIEMTNO

- CONFIGURAR NO GITIGNORE E DOCKERIGNORE OS ARQUIVOS DE IMAGEM  (SE EXCLUIR TIRE AS PASTAS COM DATAS)



ATIVAR - local windows 
 .\venv\Scripts\activate
 linux 
 source venv/bin/activate

- COM VENV INSTALAR
pip install -r requirements.txt

- INSTALAR MYSQLCLIENT 
pip install mysqlclient



# Ativar o ambiente virtual
source /home/application/app/venv/bin/activate

# Verificar se o Gunicorn está instalado
pip freeze | grep gunicorn

# Se o Gunicorn não estiver listado, instale-o
pip install gunicorn

# Executar o Gunicorn
gunicorn app.wsgi:applications --bind 0.0.0.0:8000




- SE O SERVER NAO TIVER GUNICOR, INSTALAR ELE E ENGINX E CONFIGURAR AMBOS  
(fora do venv)
pip install gunicorn

- criar arquivo gunicorn_config.py na raiz
# gunicorn_config.py
# Caminho absoluto para o arquivo .sock
bind = "unix:/home/application/app/app.sock"
workers = 3



- SE O SERVER NAO TIVER ATIVAR O GUNICONR
gunicorn -c /home/application/app/gunicorn_config.py app.wsgi:application
ou
gunicorn --bind unix:/home/application/app/app.sock app.wsgi:application
ou 
gunicorn app.wsgi --log-file - 


4. GERAR CHAVE DJANGO NO PUTTY E POR NO SETTINGS 
comando secretkey
python -c "import string as s; from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"


5. GERAR KEY DO FERNET CRYPTOGRAPHY
pip instal cryptography(Se já instalou via REQUIREMENTS não é necessário)
shel interativo digitando python para acessar
from cryptography.fernet import Fernet 
key = Fernet.generate_key()
print(key)


# KEY DJANGO
"""
python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"
"""
# FIM KEY DJANGO

# KEY FERNET
"""
from cryptography.fernet import Fernet 
key = Fernet.generate_key()
print(key)
"""
# FIM KEY FERNET

6. COPIAR E COLAR KEY NO SETTINGS OU VAR DE AMBIENTE
 FERNET_KEY = b'***************************='


# KEY DJANGO
"""
python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"
"""
# FIM KEY DJANGO

# KEY FERNET
"""
from cryptography.fernet import Fernet 
key = Fernet.generate_key()
print(key)
"""
# FIM KEY FERNET

OBSERVACOES 
ALLOWED_HOSTS = ['teste.managerontecsolutions.com.br', 'owcncf.hospedagemelastica.com.br', 'mysql-ag-br1-15.hospedagemelastica.com.br']

HOST DB SETTINGS 
'HOST': 'mysql-ag-br1-15.hospedagemelastica.com.br'



7. GERAR MAKEMIGRATIONS 
8.MIGRATE 
9.COLLECTSTATIC 
arquivos estaticos locais devem estar em uma pasta com nome diferente de static, e listado em staticfiledirs, para quando der o collectstatic o django vai criar a pasta static com os estativos das aplicacoes e os locais, com isso funcionando em produção.
python manage.py makemigrations 
python manage.py migrate  
python manage.py collectstatic 
##################### FIM DO DEPLOY ################################################################################################################






#################### FALTA TESTAR EM PROD ##########################################################################################################
# TESTAR EM PRODUÇÃO
###midleware de qtd de acessos, contido na pasta projetos e admin automacoes (model)
###OBS: SQLITE3 NAO SUPORTA TIMEZONE, ENTAO VAI APARECER MAIS 3H, DEVEMOS TESTAR COMO FICA NO MYSQL COMUNITY EDITION
####################################################################################################################################################



#################
DEPLOY NO HEROKU

```powershell
# 1. Instale a CLI do Heroku (Windows):
#    https://devcenter.heroku.com/articles/heroku-cli
#    Após instalar, reinicie o terminal ou o VS Code

# 2. Instale a extensão Heroku no VS Code:
#    Abra a aba de extensões e procure por "Heroku"
#    Instale a extensão oficial para facilitar o deploy

# 3. Ative seu ambiente virtual (Windows PowerShell):
. .\venv\Scripts\Activate.ps1

# 4. Faça login no Heroku (irá abrir no navegador):
heroku login

# 5. Verifique se já há algum plano Postgres existente:
heroku addons -a managerontec

# 6. Liste os planos de serviços disponíveis para o PostgreSQL:
heroku addons:plans heroku-postgresql

# 7. Crie o app com nome específico (ex: managerontec):
heroku create managerontec
#    Será exibida a URL do app (ex: https://managerontec-xxxxxx.herokuapp.com)
#    e o remote git configurado automaticamente

# 8. Abra o arquivo settings.py e ajuste o ALLOWED_HOSTS:
#    ALLOWED_HOSTS = ['managerontec-xxxxxx.herokuapp.com']

# 9. Limpe arquivos de configuração local antigos:
Remove-Item .\runtime.txt -Force -ErrorAction SilentlyContinue
Remove-Item .\.python-version -Force -ErrorAction SilentlyContinue
Remove-Item .\Aptfile -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter "*ssl*" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 10. Defina a versão do Python para o Heroku (arquivo .python-version):
"3.11" | Out-File -FilePath .\.python-version -Encoding ascii

# 11. Desative a coleta automática de arquivos estáticos:
heroku config:set DISABLE_COLLECTSTATIC=1 -a managerontec

# gerar chaves secretas django e criptografia, deve gerar localmente e no heroku como var de amiente de prod. 
# SECRETKEY
python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)))"
# Cole a chave que você copiou entre as aspas simples
heroku config:set SECRET_KEY='SUA_SECRET_KEY_GERADA_AQUI' -a managerontec
# FERNETKEY
bash
heroku run python -a managerontec
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode('utf-8')) # Imprime a chave como string para facilitar copiar
exit()
# Cole a chave que você copiou entre as aspas simples
heroku config:set FERNET_KEY='SUA_CHAVE_GERADA_AQUI' -a managerontec


# KEY DJANGO
"""
python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"
"""
# FIM KEY DJANGO

# KEY FERNET
"""
from cryptography.fernet import Fernet 
key = Fernet.generate_key()
print(key)
"""
# FIM KEY FERNET


# 12. Certifique-se de que o requirements.txt está correto e atualizado
#     NÃO execute pip freeze se seu ambiente está limpo, ou perderá dependências

# 13. Crie ou ajuste o Procfile com o comando de inicialização do gunicorn:
"web: gunicorn managerontec.wsgi" | Out-File -FilePath .\Procfile -Encoding ascii

# 14. Commit das mudanças de configuração:
git add -f .python-version
git add app/settings.py Procfile
git commit -m "Configura ALLOWED_HOSTS, Python 3.11 e disable collectstatic"

# 15. Configure o buildpack Python corretamente:
heroku buildpacks:clear -a managerontec
heroku buildpacks:add heroku/python -a managerontec

# 16. Faça o push do projeto para o Heroku:
git push heroku main

# 17. Crie o banco de dados Postgres com o plano desejado (exemplo: essential-0):
heroku addons:create heroku-postgresql:essential-0 --as DATABASE -a managerontec

# 18. Verifique variáveis de ambiente do banco:
heroku config:get DATABASE_URL -a managerontec

# 19. Instale a dependência de leitura de URL do banco:
pip install dj-database-url

# 20. Adicione no settings.py para usar a DATABASE_URL do Heroku:
#     import dj_database_url
#     DATABASES = {
#         'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
#     }

# 21. Rode as migrações do banco no ambiente Heroku:
heroku run python manage.py migrate -a managerontec

# 22. (Opcional) Acesse a aplicação no navegador:
heroku open -a managerontec


# 23. setar variaveis de ambiente
LISTAR variaveis
heroku config --app managerontec
# vai listar todas as variaveis e valores

heroku config:set SESSION_COOKIE_AGE_SECONDS=3600 -a managerontec
# tempo de sessao

# PARA SETAR VAR DO AMBIENTE
heroku config:set NOME_VAR=VALOR -a managerontec

# Exemplo:
ALLOWED_HOSTS:              managerontec-cd034aa7f2cd.herokuapp.com
DATABASE_URL:               postgres://u5at0f7mc4ok6c:p883************naws.com:5432/d9jmbgcaefge7r
DEBUG:                      False
DISABLE_COLLECTSTATIC:      0
DJANGO_SETTINGS_MODULE:     managerontec.settings
SECRET_KEY:                 django-insecure-kk@8ljis4**********1*n38_u874h=
FERNET_KEY:                 kByG-q7Cpw******************************D8EYKVg=
GUNICORN_CMD_ARGS:          --timeout 300
PYTHONUNBUFFERED:           1
REDIS_URL:                  rediss://:p2b26***********1e-1.amazonaws.com:15440
SESSION_COOKIE_AGE_SECONDS: 3600


# lembrar das PASTAS para heroku
-------------------------------
Aptfile 
libssl-dev
-------------------------------
.env
DEBUG=True
SECRET_KEY = 'django-insecure-kk@8ljis4xung2k6ld8!d=^80+35j5o7*n1*n38_u874h=^'
FERNET_KEY = b'kByG-q7CpwWP5WeCuVfNXsQHhcNhi-r1SnmYD8EYKVg='
REDIS_URL=redis://localhost:6379
SESSION_COOKIE_AGE_SECONDS = 3600
-------------------------------
.python-version
3.11
-------------------------------
Procfile 
web: gunicorn managerontec.wsgi:application --workers 3 --timeout 120
release: python manage.py migrate
-------------------------------



CRIAR CONTA DE STORAGE PARA ARQUIVOS MEDIA 
GERAR CHAVE JSON
CRIAR NA PASTA DO PROJETO NA MESMA DIRECAO DE SETTINGS UMA PASTA CREDENCIAIS COM A JSON, 
CONVERTER O JSON EM BASE 64, CONFIGURAR O SETTINGS E AVARIAVEL DE AMBIENTE DO HEROKU


################### FALTA DEV ######################################################################################################################
# MODULOS 
COMPRAS   
NOTAS 
ESTOQUE








