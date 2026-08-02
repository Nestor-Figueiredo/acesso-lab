# 🚀 Deploy no WSL2 (servidor da escola) — passo a passo

## Pré-requisitos no WSL2
- WSL2 com uma distro Linux (Ubuntu/Debian recomendado)
- Windows 10/11 com WSL2 habilitado
- Acesso sudo dentro do WSL

## 1. Copiar o projeto para o WSL2
```bash
# no WSL2
git clone https://github.com/Nestor-Figueiredo/acesso-lab.git
cd acesso-lab
```

## 2. Infraestrutura (uma vez)
```bash
sudo bash scripts/setup_infra.sh
```
Isso instala: python, mysql, samba, openssh-server, cria o database `acesso_lab`,
o share `[alunos]` em `/srv/samba/alunos`, o sudoers NOPASSWD, e escreve
`/etc/acesso_lab/config` com SECRET_KEY gerada.

> Se `mysql`/`samba`/`ssh` já estão instalados e configurados do seu jeito,
> rode o script e ajuste o que for necessário (ele é o mais idempotente possível).

## 3. Configurar o Google OAuth (obrigatório p/ login)
No `/etc/acesso_lab/config` (criado pelo script), preencha:
```
google_client_id=xxxx.apps.googleusercontent.com
google_client_secret=<coloque-aqui-o-seu-client-secret>
```
Crie as credenciais OAuth2 no Console do Google Cloud:
- Projeto: `gen-lang-client-0262377533` (ou um novo da escola)
- "OAuth client ID" (tipo **Web application**)
- **Authorized redirect URIs**: `http://<ip_do_servidor>:8019/`
- Domínio: `escola.edu.br`

## 4. Instalar deps + migrar + superuser
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 5. Rodar (desenvolvimento)
```bash
python manage.py runserver 0.0.0.0:8019
```
Acesse `http://<ip_do_servidor>:8019/` e entre com a conta Google @escola.edu.br.

## 6. SSH forwarding (ACESSO DOS ALUNOS) ⚠️ CRÍTICO
WSL2 tem NAT própria; o aluno **não alcança** o sshd do WSL diretamente.
Duas opções:

### Opção A — Portproxy (Windows, PowerShell Admin)
```powershell
# O IP do WSL2 (rode DENTRO do WSL):  hostname -I
netsh interface portproxy add v4tov4 listenport=22 listenaddress=0.0.0.0 connectport=22 connectaddress=<IP_WSL2>
netsh advfirewall firewall add rule name="SSH-WSL2" dir=in action=allow protocol=TCP localport=22
```
Também é preciso o sshd no WSL escutar em 0.0.0.0:22 (editar `/etc/ssh/sshd_config`).

### Opção B — networkingMode=mirrored (Windows 11 22H2+)
No Windows, crie `%UserProfile%\.wslconfig`:
```ini
[wsl2]
networkingMode=mirrored
```
Depois `wsl --shutdown` e reabra. Com mirrored, o WSL usa o **mesmo IP do
Windows**, então `ssh aluno@<ip_do_servidor>` funciona direto, sem portproxy.

## 7. Samba (alunos)
- Share `[alunos]` em `/srv/samba/alunos`, válido para o grupo `@alunos`.
- Pasta individual de cada aluno: `/srv/samba/alunos/<login>` (o app cria).
- Aluno acessa: `\\<ip_do_servidor>\<login>` (ou `smbclient //servidor/<login>`).

## 8. Backup
- O database `acesso_lab` (Django) + os databases `aluno_*` devem entrar no
  backup. Exemplo crontab no WSL2 (diário 04:00):
```cron
0 4 * * * mysqldump --all-databases > /mnt/c/backup/mysql_all_$(date +\%F).sql
```
- O `pip5` pode puxar via `rsync` se houver rede; senão, faz o backup localmente no WSL.

## Resolução de problemas
- **"Connection refused" ao conectar aluno por SSH**: o forwarding não está
  apontando pro IP certo do WSL2 (mudou após reboot) → refazer netsh.
- **Samba não libera**: conferir se o aluno está no grupo `alunos` e se a
  senha foi definida (`smbpasswd`) — o app faz isso na provisão.
- **Login Google falha**: conferir `google_client_id/secret` e a redirect URI
  exata no Console (deve ser a URL completa com a porta).
