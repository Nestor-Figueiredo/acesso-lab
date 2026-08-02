"""Google OAuth2 — login de professores/admin + recuperação de senha dos alunos.

Fluxo Authorization Code padrão. Restringe acesso ao domínio @escola.edu.br
via verificação do email do token (config GOOGLE_OAUTH2_ALLOWED_DOMAIN).

Requer 'requests'. Config via env ou /etc/acesso_lab/config:
  GOOGLE_OAUTH2_CLIENT_ID, GOOGLE_OAUTH2_CLIENT_SECRET, GOOGLE_OAUTH2_ALLOWED_DOMAIN
"""
import json
import urllib.parse

import requests
from django.conf import settings

AUTH_URI = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URI = 'https://oauth2.googleapis.com/token'
USERINFO_URI = 'https://openidconnect.googleapis.com/v1/userinfo'
SCOPES = 'openid email profile'


class OAuth2Error(Exception):
    pass


def url_autorizacao(redirect_uri, state):
    """Monta a URL de login do Google."""
    params = {
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': SCOPES,
        'state': state,
        'prompt': 'select_account',
    }
    return AUTH_URI + '?' + urllib.parse.urlencode(params)


def trocar_code_por_token(code, redirect_uri):
    """Troca o code de autorização por access_token + id_token."""
    resp = requests.post(TOKEN_URI, data={
        'code': code,
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }, timeout=15)
    if resp.status_code != 200:
        raise OAuth2Error(f'Falha ao obter token: {resp.status_code} {resp.text[:200]}')
    return resp.json()


def obter_userinfo(access_token):
    """Retorna email/nome/sub do usuário Google."""
    resp = requests.get(USERINFO_URI, headers={'Authorization': f'Bearer {access_token}'}, timeout=15)
    if resp.status_code != 200:
        raise OAuth2Error(f'Falha ao obter userinfo: {resp.status_code}')
    return resp.json()


def validar_dominio(email):
    """Confere se o email pertence ao domínio permitido (@escola.edu.br)."""
    dominio = getattr(settings, 'GOOGLE_OAUTH2_ALLOWED_DOMAIN', 'escola.edu.br')
    return email.lower().endswith('@' + dominio.lower())


def autenticar_google(code, redirect_uri):
    """Fluxo completo: code → token → userinfo → valida domínio. Retorna dict email/nome."""
    token = trocar_code_por_token(code, redirect_uri)
    acesso = token.get('access_token')
    if not acesso:
        raise OAuth2Error('Token sem access_token')
    info = obter_userinfo(acesso)
    email = (info.get('email') or '').lower()
    if not email:
        raise OAuth2Error('Email não retornado pelo Google')
    if not validar_dominio(email):
        raise OAuth2Error(f'Domínio não permitido: {email}. Só @{getattr(settings, "GOOGLE_OAUTH2_ALLOWED_DOMAIN", "escola.edu.br")} é aceito.')
    return {
        'email': email,
        'nome': info.get('name') or email.split('@')[0],
        'sub': info.get('sub'),
    }
