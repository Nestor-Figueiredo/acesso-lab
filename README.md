# 🎓 Acesso Lab — Sistema de Controle de Acesso SSH/Samba/MySQL

Sistema para **laboratório de escola** (práticas de Desenvolvimento de Sistemas).
Controla o acesso dos **alunos** a um **servidor Linux (WSL2)** usando o **mesmo
usuário e senha para SSH e Samba**, com **1 database MySQL por aluno** e
**autenticação via conta Google** (login + recuperação de senha).

## ✨ Funcionalidades

- 🔐 **Autenticação única**: mesmo usuário e senha para **SSH** e **Samba**
- 👩‍🎓 **Gestão de alunos**: cadastro, RA, turma, disciplinas, ativar/desativar acesso
- 🗄️ **MySQL por aluno**: cada aluno ganha `aluno_<login>` com senha própria e `GRANT ALL`
- 🧩 **Autorização por recurso**: admin define quais recursos o aluno pode usar
  (SSH, Samba, MySQL, pasta) — liga/desliga individualmente
- 🔑 **Login via Google** `@escola.edu.br` (professores/admin)
- 🔄 **Recuperação de senha** via conta Google (aluno redefine a senha SSH/Samba)
- 📁 **Pasta por aluno** no share Samba (`\\servidor\<login>`)
- 📊 Dashboard Bootstrap 5 (dark) + Django Admin completo

## 🏗️ Stack

| Componente | Tecnologia |
|---|---|
| Backend | Django 4.2 + Python 3 |
| Frontend | Bootstrap 5 (dark) |
| Banco | MySQL (MariaDB) — 1 database por aluno |
| Login | Google OAuth2 (restrito a @escola.edu.br) |
| Servidor | Linux via **WSL2** na escola |

## 🖥️ Como funciona (arquitetura)

```
            Notebook do aluno
                 │  ssh aluno@<servidor>:22
                 ▼
        ┌────────────────────────────────┐
        │  Windows (rede da escola)      │
        │  netsh portproxy: 22→WSL2      │
        └───────────────┬────────────────┘
                        ▼
        ┌────────────────────────────────────────┐
        │  WSL2 (roda o Django + SSH + Samba)    │
        │   • /etc/passwd      → usuário SSH     │
        │   • smbpasswd        → mesma senha     │
        │   • /srv/samba/alunos → pasta por aluno│
        │   • MySQL            → 1 db por aluno  │
        └────────────────────────────────────────┘
```

O **Django é o "dono" do usuário Linux**: cria o usuário (`useradd`), define a
senha (`chpasswd`), aplica a **mesma senha no Samba** (`smbpasswd`), cria o
**database MySQL** do aluno e a **pasta** no share. Tudo via `sudo NOPASSWD`
(configurado no setup).

## 📦 Instalação no WSL2 (servidor da escola)

### 1. Infraestrutura (MySQL, Samba, SSHd, share, sudo)
```bash
cd acesso-lab
sudo bash scripts/setup_infra.sh     # instala tudo e cria /etc/acesso_lab/config
```

### 2. Dependências Python + config do app
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edite /etc/acesso_lab/config (root:www-data 640) e preencha o Google OAuth:
#   google_client_id=xxxxxxxx.apps.googleusercontent.com
#   google_client_secret=xxxx
```

### 3. Migrar + criar superusuário + coletar estáticos
```bash
python manage.py migrate
python manage.py createsuperuser       # professor admin
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8019
```
*(Em produção, usar gunicorn: `gunicorn acesso_lab.wsgi -b 0.0.0.0:8019`)*

### 4. SSH forwarding WSL2 → alunos acessarem (importante!)
Como é **WSL2**, use o `scripts/ssh_forward.ps1` no **Windows (PowerShell
Admin)** para encaminhar a porta 22 do Windows para o WSL2. Ou, em Windows 11
22H2+, configure `networkingMode=mirrored` no `.wslconfig` para o WSL usar o
IP do host (aí o forwarding não é necessário).

### 5. Google Cloud — OAuth2
- Criar credenciais OAuth2 em https://console.cloud.google.com/ (projeto
  `gen-lang-client-0262377533` ou um novo)
- **URI de redirecionamento**: `http://<servidor>:8019/` (a rota de callback é a
  própria `/`, que pega o parâmetro `code`)
- Restringir ao domínio `escola.edu.br` (o app já valida no servidor)

## 🧪 Como testar (desenvolvimento no pip5)
```bash
python manage.py check
# Para testar modelos/serviços sem MySQL ainda:
#   (ver docs — roda test client com SQLite temporário)
```

## ✅ Regras de segurança
- **Nunca** versionar credenciais — vivem em `/etc/acesso_lab/config` (fora do repo)
- Desativar aluno **bloqueia SSH+Samba** na hora (sem apagar dados)
- Exclusão de database do aluno (`remover_database_aluno`) é **destrutiva** — sempre perguntar antes

## 🗂️ Estrutura
```
acesso-lab/
├── manage.py
├── requirements.txt
├── acesso_lab/          # config do projeto (settings/urls/wsgi)
├── alunos/              # app principal
│   ├── models.py        # Aluno, Professor, Turma, Disciplina, Recurso, AcessoAluno
│   ├── services.py      # provimento: useradd/smbpasswd/mysql/share
│   ├── oauth2.py        # login Google @escola.edu.br
│   ├── views.py         # dashboard, CRUD, provisionar, recuperar senha
│   └── templates/       # Bootstrap 5 dark
├── scripts/
│   ├── setup_infra.sh   # infra WSL2 (MySQL/Samba/SSH/install)
│   └── ssh_forward_wsl2.ps1  # forwarding SSH Windows→WSL2
└── docs/                # arquitetura, deploy-wsl2, seguranca
```

## 📁 Repositório
Privado: `Nestor-Figueiredo/acesso-lab` (não versionar credenciais).
