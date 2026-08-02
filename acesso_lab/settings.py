"""
Django settings para acesso_lab — Sistema de Controle de Acesso SSH/Samba
Laboratório de Desenvolvimento de Sistemas (roda no WSL2 da escola).

Credenciais (MySQL, SECRET_KEY, Google OAuth) NÃO são versionadas:
  - MySQL e SECRET_KEY são lidos de /etc/acesso_lab/config (como SIM808/RouterLog)
  - Google OAuth2 usa variáveis de ambiente (GOOGLE_OAUTH_*)

Para rodar: ver docs/deploy-wsl2.md
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Config externa (não versionada) — /etc/acesso_lab/config
# ---------------------------------------------------------------------------
def _ler_config():
    cfg = {
        'secret_key': 'CHANGE-ME-EM-PRODUCAO',
        'db_name': 'acesso_lab',
        'db_user': 'acesso_lab',
        'db_pass': 'CHANGE-ME-NO-ETC',  # real em /etc/acesso_lab/config
        'db_host': '127.0.0.1',
        'db_port': '3306',
    }
    caminho = '/etc/acesso_lab/config'
    try:
        with open(caminho) as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#') or '=' not in linha:
                    continue
                chave, _, valor = linha.partition('=')
                cfg[chave.strip()] = valor.strip()
    except FileNotFoundError:
        print(f"⚠️ {caminho} não encontrado — usando defaults de DEV sem senha válida. "
              "Crie /etc/acesso_lab/config (root:www-data 640).")
    except Exception as e:
        print(f"⚠️ Erro ao ler {caminho}: {e}")
    return cfg

_config = _ler_config()

SECRET_KEY = _config.get('secret_key', 'CHANGE-ME-EM-PRODUCAO')

DEBUG = True  # colocar False em produção

# Hosts permitidos — preencher com o IP/localhost do servidor na escola
ALLOWED_HOSTS = ['*']  # em produção: ['localhost','127.0.0.1','<ip-do-servidor-wsl>']

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # apps do projeto
    'alunos.apps.AlunosConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acesso_lab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'alunos' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'acesso_lab.wsgi.application'

# ---------------------------------------------------------------------------
# Banco de dados — MySQL (1 db por aluno é criado em runtime pelo app)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': _config.get('db_name', 'acesso_lab'),
        'USER': _config.get('db_user', 'acesso_lab'),
        'PASSWORD': _config.get('db_pass', 'CHANGE-ME-NO-ETC'),
        'HOST': _config.get('db_host', '127.0.0.1'),
        'PORT': _config.get('db_port', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Login / rotas
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ---------------------------------------------------------------------------
# Internationalization — pt-BR
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'alunos' / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Google OAuth2 (login de professores/alunos com @escola.edu.br)
# Sobrescrevido por variáveis de ambiente ou /etc/acesso_lab/config
# ---------------------------------------------------------------------------
GOOGLE_OAUTH2_CLIENT_ID = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', _config.get('google_client_id', ''))
GOOGLE_OAUTH2_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET', _config.get('google_client_secret', ''))
# Domínio permitido (somente contas @escola.edu.br)
GOOGLE_OAUTH2_ALLOWED_DOMAIN = os.environ.get('GOOGLE_OAUTH2_ALLOWED_DOMAIN', _config.get('google_allowed_domain', 'escola.edu.br'))

# ---------------------------------------------------------------------------
# Integração Linux/Samba/MySQL (executados no servidor via subprocess/sudo)
# ---------------------------------------------------------------------------
# Comandos usados pelo serviço de provimento. O usuário do Django precisa
# de permissão sudo NOPASSWD para estes comandos (ver docs/seguranca.md)
LAB_SSH_SHELL = os.environ.get('LAB_SSH_SHELL', _config.get('lab_shell', '/bin/bash'))
LAB_SAMBA_GROUP = os.environ.get('LAB_SAMBA_GROUP', _config.get('lab_samba_group', 'alunos'))
LAB_MYSQL_ADMIN = os.environ.get('LAB_MYSQL_ADMIN', _config.get('lab_mysql_admin', 'root'))
LAB_SAMBA_SHARE_ROOT = os.environ.get('LAB_SAMBA_SHARE_ROOT', _config.get('lab_samba_share_root', '/srv/samba/alunos'))
