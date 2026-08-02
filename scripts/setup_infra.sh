# Instalação do Ambiente do Laboratório — WSL2
# Rode como usuário com sudo (Ex.: sudo bash scripts/setup_infra.sh)
#
# Instala/configura: dependências Python, MySQL, Samba, SSHd dentro do WSL2,
# criação do share de alunos, sudo NOPASSWD p/ o app, e o database do Django.
set -euo pipefail

echo "==> [1/7] Atualizando pacotes"
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv \
    mysql-server mysql-client \
    samba samba-common-bin smbclient \
    openssh-server \
    libmysqlclient-dev pkg-config build-essential || true
sudo apt-get install -y python3-mysqldb default-libmysqlclient-dev 2>/dev/null || true

echo "==> [2/7] Serviços base (sshd, mysql, smbd)"
sudo service ssh start || true
sudo service mysql start || true
sudo service smbd start || true

echo "==> [3/7] Banco MySQL do Django (acesso_lab)"
# senha root do MySQL p/ o app (ajuste se quiser) — fica no /etc/acesso_lab/config
APP_DB="acesso_lab"
APP_USER="acesso_lab"
# Senha vem de env; se não vier, gera aleatória e imprime no final
if [ -n "${APP_PASS:-}" ]; then
  SENHA_DB="$APP_PASS"
else
  SENHA_DB="$(python3 -c 'import secrets;print(secrets.token_urlsafe(16))')"
fi
sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${APP_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${APP_USER}'@'localhost' IDENTIFIED BY '${SENHA_DB}';
ALTER USER '${APP_USER}'@'localhost' IDENTIFIED BY '${SENHA_DB}';
GRANT ALL PRIVILEGES ON \`${APP_DB}\`.* TO '${APP_USER}'@'localhost';
-- o root do MySQL precisa poder criar database por aluno (o app roda sudo mysql)
FLUSH PRIVILEGES;
SQL

echo "==> [4/7] Diretório do share de alunos /srv/samba/alunos"
sudo mkdir -p /srv/samba/alunos
sudo chown root:alunos /srv/samba/alunos 2>/dev/null || sudo groupadd -f alunos
sudo chmod 2770 /srv/samba/alunos || sudo chmod 770 /srv/samba/alunos

echo "==> [5/7] share Samba [alunos] no smb.conf (idempotente)"
sudo bash -c 'grep -q "^\[alunos\]" /etc/samba/smb.conf || cat >> /etc/samba/smb.conf <<EOF

[alunos]
   comment = Pasta de alunos do lab
   path = /srv/samba/alunos
   browseable = No
   read only = No
   valid users = @alunos
   create mask = 0700
   directory mask = 0700
EOF'
sudo service smbd reload || sudo service smbd restart

echo "==> [6/7] sudo NOPASSWD p/ o app provisionar contas"
# Permite ao usuário que roda o Django executar useradd/groupadd/smbpasswd/mysql
# sem senha. TROQUE 'pi' pelo usuário que roda o Django se for diferente.
usuario_django="${USER:-pi}"
sudo bash -c "cat > /etc/sudoers.d/acesso-lab <<EOFS
$usuario_django ALL=(root) NOPASSWD: /usr/sbin/useradd, /usr/sbin/usermod, /usr/sbin/groupadd, /usr/bin/chpasswd, /usr/bin/smbpasswd, /usr/bin/pdbedit, /usr/bin/mysql, /usr/sbin/install, /usr/bin/install, /bin/bash
EOFS"
sudo chmod 440 /etc/sudoers.d/acesso-lab
sudo visudo -c || echo "⚠️  sudoers com problema — revise!" || true

echo "==> [7/7] Config do app em /etc/acesso_lab/config (não versionada)"
sudo mkdir -p /etc/acesso_lab
sudo bash -c "cat > /etc/acesso_lab/config <<EOFC
# Config acesso_lab - NÃO versionar (fora do repo). Padrão SIM808/RouterLog.
secret_key=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')
db_name=${APP_DB}
db_user=${APP_USER}
db_pass=${SENHA_DB}
db_host=127.0.0.1
db_port=3306
google_allowed_domain=escola.edu.br
lab_samba_group=alunos
lab_samba_share_root=/srv/samba/alunos
EOFC"
sudo chown root:"$usuario_django" /etc/acesso_lab/config
sudo chmod 640 /etc/acesso_lab/config

echo ""
echo "✅ Infraestrutura pronta. Usuário MySQL do Django: ${APP_USER} / senha gerada (em /etc/acesso_lab/config)."
echo "  1) Instalar dependências Python do app: pip install -r requirements.txt"
echo "  2) Ajustar /etc/acesso_lab/config (Google OAuth: google_client_id / google_client_secret)"
echo "  3) python manage.py migrate"
echo "  4) python manage.py createsuperuser"
echo "  5) Ver docs/deploy-wsl2.md p/ SSH forwarding (alunos acessarem de fora do WSL2)"
