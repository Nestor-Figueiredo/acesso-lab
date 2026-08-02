# 🛡️ Segurança — Acesso Lab

## Princípios
1. **Nenhuma credencial versionada** — SECRET_KEY, senha MySQL e Google OAuth
   vivem em `/etc/acesso_lab/config` (fora do git). O código lê com fallback de DEV.
2. **Menor privilégio** — o Django usa `sudo NOPASSWD` *apenas* para os comandos
   de provisão (não para sudo genérico). Ver `scripts/setup_infra.sh` (sudoers).
3. **Isolamento por aluno no MySQL** — cada aluno tem database dedicado
   (`aluno_<login>`) e usuário com `GRANT ALL` **somente** nesse database.
   Um aluno NÃO enxerga os databases dos outros.

## Comandos autorizados no sudoers (NOPASSWD)
```
useradd, usermod, groupadd, chpasswd, smbpasswd, pdbedit, mysql, install, bash
```
> ⚠️ O `bash` está incluso para os comandos com `printf | smbpasswd` e
> `echo | chpasswd`. **Revise se é aceitável no seu ambiente** — alternativa:
> criar scripts de provisão com permissão específica e autorizar só eles.

## Google OAuth2 (login)
- Restrito **por email** ao domínio `@escola.edu.br` (validado no servidor em
  `oauth2.validar_dominio`). Mesmo que peçam escopo, não aceita outro domínio.
- Client ID/Secret em `/etc/acesso_lab/config` (ou env `GOOGLE_OAUTH2_*`).
- State de CSRF do OAuth guardado em sessão (valida no retorno).

## Ações destrutivas
- **Exclusão de database do aluno** (`services.remover_database_aluno`) → perde
  dados. **Sempre perguntar/confirmar antes** (regra do AGENTS/boa prática).
- **Desativar aluno** (`usermod -L` + `pdbedit -x`) → só bloqueia, NÃO apaga.

## Checklist antes de produção
- [ ] `DEBUG=False` em `/etc/acesso_lab/config` (ou settings) 
- [ ] `ALLOWED_HOSTS` com o IP/hostname real do servidor
- [ ] `collectstatic` + servir via gunicorn/apache atrás de alguma proteção
- [ ] HTTPS se exposto fora da rede local (use Caddy/nginx como proxy)
- [ ] Backup diário do MySQL (database `acesso_lab`): usar o padrão
      `/home/pi/script/backup_automatico.sh` se o servidor for acessível, ou
      crontab próprio no WSL2
