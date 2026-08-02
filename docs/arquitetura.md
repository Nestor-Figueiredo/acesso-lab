# 🏗️ Arquitetura — Acesso Lab

## Visão geral
Sistema web (Django) que roda **no WSL2 do servidor da escola** e gerencia
acessos de alunos ao servidor Linux (SSH + Samba + MySQL). O Django é o ponto
único de verdade (source of truth) para quem tem acesso e o quê.

## Modelo de dados (resumo)
- **Turma** — turma de alunos (3º Ano A, etc.)
- **Disciplina** — matéria (Desenvolvimento Web...)
- **Recurso** — recurso de sistema com tipo: `ssh`, `samba`, `mysql`, `pasta`
- **Aluno** — dados do aluno + `username_linux` (login real no servidor) + `ativo`
- **Professor** — vincula ao User Django (login via Google)
- **AcessoAluno** — autorização por recurso (aluno X recurso, `ativo`)

## Fluxo de provisão (criação da conta de um aluno)
Quando o professor cadastra um aluno e clica em **"Provisionar"**, o app executa
(em ordem, via `sudo NOPASSWD`):
1. **Gera `username_linux`** a partir do nome (translitera acentos, max 20 chars)
2. **Cria usuário Linux** (`useradd -m -s /bin/bash -G alunos,...`)
3. **Define a senha** (`echo 'user:senha' | chpasswd`) → usada no SSH
4. **Define a MESMA senha no Samba** (`smbpasswd`) → login Samba idêntico
5. **Cria database MySQL** `aluno_<login>` + usuário + `GRANT ALL`
6. **Cria a pasta** `/srv/samba/alunos/<login>` e o share no `smb.conf`

Tudo é **idempotente**: rodar de novo não duplica (usa `IF NOT EXISTS`,
`update_or_create`, `grep -q` no smb.conf).

## Autorização por recurso
O admin liga/desliga recursos individuais do aluno (SSH, Samba, MySQL, pasta).
Ao desativar o aluno (`ativo=False`) o app bloqueia o login Linux
(`usermod -L`) e remove do DB Samba (`pdbedit -x`) — sem apagar a pasta/dados.

## Segurança de senha
- Senha do aluno: informada pelo admin na provisão (valida ≥8 chars)
- Senha MySQL do aluno: gerada automaticamente (`secrets`)
- Credenciais do sistema (SECRET_KEY, MySQL, Google) em `/etc/acesso_lab/config`
  (fora do repo, root:www-data 640) — padrão usado no SIM808 e RouterLog

## WSL2 e rede
- O `sshd` roda dentro do WSL2; WSL2 tem **NAT própria**, então o acesso dos
  notebooks demanda **forwarding** da porta 22 do Windows → WSL2 (`netsh
  portproxy`, script `scripts/ssh_forward_wsl2.ps1`) OU `networkingMode=mirrored`
  no `.wslconfig` (Windows 11 22H2+), que faz o WSL compartilhar o IP do host.
- Alunos acessam `ssh aluno@<ip_do_servidor>` na mesma rede.
