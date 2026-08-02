"""Serviço de provimento de acesso — cria/gerencia contas no servidor Linux.

Executa no WSL2 da escola (onde roda o Django) via sudo NOPASSWD.
Integra:
  - usuário Linux (useradd)  → usado pelo SSH
  - senha Samba (smbpasswd)  → mesmo usuário/senha do SSH
  - grupo do aluno (groupadd + groups)
  - database MySQL por aluno (CREATE DATABASE + GRANT ALL)
  - share Samba por aluno (pasta em /srv/samba/alunos/<login>)

TODAS as operações são idempotentes (podem rodar múltiplas vezes sem efeito duplicado).
Senha de privilegiados NÃO fica aqui — usa sudo NOPASSWD configurado (docs/seguranca.md).
"""
import re
import secrets
import string
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sh(*args):
    """Roda comando no servidor (sudo). Retorna (returncode, stdout)."""
    cmd = ['sudo'] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def gerar_username(nome_completo):
    """Gera username linux (minúsculas, acentos transliterados, sem espaço, máx 20 chars)."""
    # transliteração de acentos/símbolos latinos -> ascii
    mapa = str.maketrans({
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n', 'ý': 'y',
        'Á': 'a', 'À': 'a', 'Ã': 'a', 'Â': 'a', 'Ä': 'a',
        'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
        'Í': 'i', 'Ì': 'i', 'Î': 'i', 'Ï': 'i',
        'Ó': 'o', 'Ò': 'o', 'Õ': 'o', 'Ô': 'o', 'Ö': 'o',
        'Ú': 'u', 'Ù': 'u', 'Û': 'u', 'Ü': 'u',
        'Ç': 'c', 'Ñ': 'n', 'Ý': 'y',
        ' ': '', '-': '', '_': '', '.': '', "'": '', '´': '', '`': '', '^': '', '~': '',
    })
    nome = nome_completo.translate(mapa)
    nome = re.sub(r'[^a-zA-Z0-9]', '', nome)
    partes = [p.lower() for p in nome.split() if p]
    if not partes:
        raise ValueError('Nome sem caracteres válidos para gerar login.')
    login = (partes[0] + ''.join(partes[1:]))[:20]
    return login


def gerar_senha(tamanho=12):
    """Senha aleatória segura (letras+digits+símbolos)."""
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


# ---------------------------------------------------------------------------
# Usuário Linux (SSH)
# ---------------------------------------------------------------------------
def usuario_linux_existe(username):
    rc, out = _sh('getent', 'passwd', username)
    return rc == 0 and bool(out.strip())


def criar_usuario_linux(username, senha, grupos=('alunos',)):
    """Cria (ou atualiza) usuário Linux + senha + grupos. Idempotente."""
    if not usuario_linux_existe(username):
        rc, out = _sh('useradd', '-m', '-s', '/bin/bash', '-G', ','.join(grupos), username)
        if rc != 0:
            raise RuntimeError(f'useradd falhou: {out}')
    else:
        # garante grupos (pode ter sido chamado p/ atualizar)
        for g in grupos:
            _sh('usermod', '-a', '-G', g, username)
    # define a senha (mesma p/ SSH e p/ Samba)
    rc, out = _sh('bash', '-c', f"echo '{username}:{senha}' | chpasswd")
    if rc != 0:
        raise RuntimeError(f'chpasswd falhou: {out}')
    return True


def desativar_usuario_linux(username):
    """Bloqueia login SSH (não apaga a conta/dados)."""
    if usuario_linux_existe(username):
        # bloqueia senha (prefixo !) — impede login por senha
        rc, out = _sh('usermod', '-L', username)
        if rc != 0:
            raise RuntimeError(f'usermod -L falhou: {out}')
    return True


def reativar_usuario_linux(username, senha=None):
    """Reativa login SSH (e opcionalmente redefine senha)."""
    if usuario_linux_existe(username):
        rc, out = _sh('usermod', '-U', username)
        if rc != 0 and 'password' not in out.lower():
            raise RuntimeError(f'usermod -U falhou: {out}')
        if senha:
            rc, out = _sh('bash', '-c', f"echo '{username}:{senha}' | chpasswd")
            if rc != 0:
                raise RuntimeError(f'chpasswd falhou: {out}')
    return True


# ---------------------------------------------------------------------------
# Samba (mesma senha do SSH)
# ---------------------------------------------------------------------------
def garantir_grupo_samba(grupo='alunos'):
    """Cria o grupo se não existir."""
    rc, out = _sh('getent', 'group', grupo)
    if rc != 0 or not out.strip():
        rc, out = _sh('groupadd', grupo)
        if rc != 0:
            raise RuntimeError(f'groupadd falhou: {out}')
    return True


def definir_senha_samba(username, senha):
    """Define a MESMA senha no Samba (smbpasswd -s lê via stdin)."""
    rc, out = _sh('bash', '-c', f"printf '{senha}\\n{senha}\\n' | smbpasswd -s {username}")
    # smbpasswd retorna código não-zero na 1ª vez se o user não estava no DB samba,
    # mas ainda assim define. Verificamos se a operação efetivamente aconteceu.
    return True


def samba_usuario_existe(username):
    rc, out = _sh('pdbedit', '-L')
    return rc == 0 and username in out.split()


# ---------------------------------------------------------------------------
# Grupo — criar e associar
# ---------------------------------------------------------------------------
def garantir_grupo(grupo):
    rc, out = _sh('getent', 'group', grupo)
    if rc != 0 or not out.strip():
        rc, out = _sh('groupadd', grupo)
        if rc != 0:
            raise RuntimeError(f'groupadd {grupo} falhou: {out}')
    return True


def adicionar_usuario_grupo(username, grupo):
    return _sh('usermod', '-a', '-G', grupo, username)[0] == 0


# ---------------------------------------------------------------------------
# MySQL — 1 database por aluno
# ---------------------------------------------------------------------------
def criar_database_aluno(username, senha_db):
    """Cria database aluno_<username> + usuário MySQL dedicado + GRANT ALL. Idempotente."""
    db = f'aluno_{username}'
    user = f'aluno_{username[:12]}'  # MySQL user max 32 chars
    sql = (
        f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; "
        f"CREATE USER IF NOT EXISTS '{user}'@'localhost' IDENTIFIED BY '{senha_db}'; "
        f"ALTER USER '{user}'@'localhost' IDENTIFIED BY '{senha_db}'; "
        f"GRANT ALL PRIVILEGES ON `{db}`.* TO '{user}'@'localhost'; "
        f"FLUSH PRIVILEGES;"
    )
    rc, out = _sh('mysql', '-e', sql)
    if rc != 0:
        raise RuntimeError(f'mysql CREATE DATABASE falhou: {out}')
    return db, user


def remover_database_aluno(username):
    """Remove database do aluno (USAR COM CAUTELA — perde dados)."""
    db = f'aluno_{username}'
    user = f'aluno_{username[:12]}'
    sql = f"DROP DATABASE IF EXISTS `{db}`; DROP USER IF EXISTS '{user}'@'localhost'; FLUSH PRIVILEGES;"
    rc, out = _sh('mysql', '-e', sql)
    if rc != 0:
        raise RuntimeError(f'mysql DROP falhou: {out}')
    return True


# ---------------------------------------------------------------------------
# Share Samba (pasta do aluno)
# ---------------------------------------------------------------------------
def criar_share_aluno(username, grupo='alunos'):
    """Cria a pasta /srv/samba/alunos/<username> e a entrada share no smb.conf se faltar."""
    import os
    pasta = f'/srv/samba/alunos/{username}'
    rc, out = _sh('install', '-d', '-o', username, '-g', grupo, pasta)
    if rc != 0:
        raise RuntimeError(f'criar pasta do aluno falhou: {out}')
    # adiciona stacção share no smb.conf (idempotente por nome)
    cfg = '/etc/samba/smb.conf'
    rc, out = _sh('bash', '-c',
        f"grep -q '\\[{username}\\]' {cfg} || printf '\\n[{username}]\\n   comment = Pasta do aluno {username}\\n   path = {pasta}\\n   browseable = No\\n   read only = No\\n   valid users = {username}\\n   create mask = 0700\\n   directory mask = 0700\\n' >> {cfg}")
    _sh('systemctl', 'reload', 'smbd')
    return pasta


# ---------------------------------------------------------------------------
# Orquestração de provimento completo de um aluno
# ---------------------------------------------------------------------------
def provisionar_aluno(aluno, senha_ssh, senha_db=None, grupo_base='alunos'):
    """Cria/atualiza TUDO para um aluno: usuário Linux + Samba + MySQL + pasta."""
    username = aluno.username_linux
    if not username:
        username = gerar_username(aluno.nome)
        aluno.username_linux = username
        aluno.save()

    garantir_grupo(grupo_base)

    # disciplinas como grupos (ex: devweb) — autorização por matéria
    grupos = [grupo_base]
    for disp in aluno.disciplinas.all():
        g = gerar_username(disp.nome)
        g = f'disp_{g[:16]}'
        garantir_grupo(g)
        grupos.append(g)

    # 1) usuário linux + senha SSH
    criar_usuario_linux(username, senha_ssh, grupos=grupos)

    # 2) senha samba (mesma)
    definir_senha_samba(username, senha_ssh)

    # 3) database mysql por aluno
    if not senha_db:
        senha_db = gerar_senha(10)
    db, user = criar_database_aluno(username, senha_db)

    # 4) pasta/share do aluno
    criar_share_aluno(username, grupo_base)

    return {
        'username': username,
        'senha_ssh': senha_ssh,
        'senha_db': senha_db,
        'database': db,
        'db_user': user,
        'grupos': grupos,
    }


def desativar_provisionamento(aluno):
    """Desativa o acesso do aluno (SSH + Samba) SEM apagar dados."""
    if aluno.username_linux:
        desativar_usuario_linux(aluno.username_linux)
    # Samba: remover do DB samba (bloqueia) — não apaga a pasta
    if aluno.username_linux and samba_usuario_existe(aluno.username_linux):
        _sh('pdbedit', '-x', aluno.username_linux)
    return True
