"""Views do acesso_lab — login Google, dashboard, gestão de alunos e provisão."""
import secrets

from django.contrib import messages
from django.contrib.auth import authenticate, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import oauth2, services
from .models import AcessoAluno, Aluno, Disciplina, Professor, Recurso, Turma


# ---------------------------------------------------------------------------
# Login via Google
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if 'code' in request.GET:
        return _callback_google(request)
    state = secrets.token_urlsafe(16)
    request.session['oauth_state'] = state
    redirect_uri = request.build_absolute_uri(reverse('login'))
    url = oauth2.url_autorizacao(redirect_uri, state)
    return render(request, 'alunos/login.html', {'google_url': url})


def _callback_google(request):
    """Trata o retorno do Google (callback)."""
    # valida state
    if request.GET.get('state') != request.session.pop('oauth_state', None):
        messages.error(request, 'Falha de segurança na autenticação (state inválido). Tente novamente.')
        return redirect('login')
    if 'error' in request.GET:
        messages.error(request, f'Autenticação cancelada/não autorizada: {request.GET["error"]}')
        return redirect('login')
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Código de autorização ausente.')
        return redirect('login')
    try:
        redirect_uri = request.build_absolute_uri(reverse('login'))
        info = oauth2.autenticar_google(code, redirect_uri)
    except oauth2.OAuth2Error as e:
        messages.error(request, f'Erro na autenticação Google: {e}')
        return redirect('login')

    email = info['email']
    # login local (cria user Django se for professor/admin com conta autorizada)
    user = User.objects.filter(email=email).first()
    if not user:
        # professor com email @escola.edu.br vira admin do sistema
        user = User.objects.create_user(
            username=email.split('@')[0],
            email=email,
            first_name=info['nome'],
            is_staff=True,
        )
    # garante que o domínio foi validado (oauth2 já faz)
    from django.contrib.auth import login as auth_login
    auth_login(request, user)
    # vincula professor se não existir
    if not Professor.objects.filter(user=user).exists():
        Professor.objects.create(user=user, nome=info['nome'], email=email)
    messages.success(request, f'Bem-vindo(a), {info["nome"]}!')
    return redirect('dashboard')


def logout_view(request):
    django_logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Dashboard / listagem
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    return render(request, 'alunos/dashboard.html', {
        'qtd_alunos': Aluno.objects.count(),
        'qtd_ativos': Aluno.objects.filter(ativo=True).count(),
        'qtd_turmas': Turma.objects.count(),
        'qtd_disciplinas': Disciplina.objects.count(),
        'recursos': Recurso.objects.all(),
        'turmas': Turma.objects.all().prefetch_related('alunos'),
    })


@login_required
def lista_alunos(request):
    alunos = Aluno.objects.all().select_related('turma').prefetch_related('disciplinas', 'acessos__recurso')
    return render(request, 'alunos/lista_alunos.html', {'alunos': alunos})


# ---------------------------------------------------------------------------
# CRUD de aluo + provisão de conta
# ---------------------------------------------------------------------------
@login_required
def detalhe_aluno(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    return render(request, 'alunos/detalhe_aluno.html', {
        'aluno': aluno,
        'acessos': aluno.acessos.select_related('recurso'),
        'recursos': Recurso.objects.all(),
    })


@login_required
def criar_aluno(request):
    turmas = Turma.objects.all()
    disciplinas = Disciplina.objects.all()
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip().lower()
        ra = request.POST.get('ra', '').strip()
        turma_id = request.POST.get('turma') or None
        if not nome or not email:
            messages.error(request, 'Nome e email são obrigatórios.')
        else:
            try:
                aluno = Aluno.objects.create(
                    nome=nome, email=email, ra=ra,
                    turma=Turma.objects.filter(pk=turma_id).first() if turma_id else None,
                )
                ds = request.POST.getlist('disciplinas')
                aluno.disciplinas.set(Disciplina.objects.filter(pk__in=ds))
                messages.success(request, f'Aluno {nome} criado. Use "Provisionar" para criar a conta.')
                return redirect('detalhe_aluno', pk=aluno.pk)
            except Exception as e:
                messages.error(request, f'Erro ao criar: {e}')
    return render(request, 'alunos/form_aluno.html', {
        'turmas': turmas, 'disciplinas': disciplinas,
    })


@login_required
def provisionar_conta(request, pk):
    """Cria/atualiza a conta do aluno no servidor (Linux + Samba + MySQL + pasta)."""
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        senha_ssh = request.POST.get('senha_ssh', '').strip()
        if len(senha_ssh) < 8:
            messages.error(request, 'Senha deve ter no mínimo 8 caracteres.')
            return redirect('detalhe_aluno', pk=aluno.pk)
        try:
            senha_db = services.gerar_senha(10)
            resultado = services.provisionar_aluno(aluno, senha_ssh, senha_db=senha_db)
            aluno.ativo = True
            aluno.save()
            # registra os acessos SSH + MySQL como ativos
            for nome_tipo in [('ssh', None), ('mysql', None)]:
                recurso = Recurso.objects.filter(tipo=nome_tipo[0]).first()
                if recurso:
                    AcessoAluno.objects.update_or_create(
                        aluno=aluno, recurso=recurso,
                        defaults={'ativo': True,
                                  'senha_recurso': resultado['senha_db'] if nome_tipo[0] == 'mysql' else ''},
                    )
            messages.success(
                request,
                f'Conta criada/atualizada: login {resultado["username"]} · SSH/Samba senha informada · '
                f'MySQL db {resultado["database"]} (senha {resultado["senha_db"]})',
            )
            request.session['flash_resultado'] = resultado
            return redirect('provisionar_conta', pk=aluno.pk)
        except Exception as e:
            messages.error(request, f'Erro ao provisionar: {e}')
            return redirect('detalhe_aluno', pk=aluno.pk)

    resultado = request.session.pop('flash_resultado', None)
    return render(request, 'alunos/provisionar.html', {'aluno': aluno, 'resultado': resultado})


@login_required
def alternar_ativo(request, pk):
    """Ativa/desativa o acesso do aluno (bloqueia SSH+Samba)."""
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        if aluno.ativo:
            services.desativar_provisionamento(aluno)
            aluno.ativo = False
            aluno.save()
            messages.success(request, f'Acesso de {aluno.nome} DESATIVADO (SSH+Samba bloqueados).')
        else:
            services.reprovisionar = None
            aluno.ativo = True
            aluno.save()
            messages.success(request, f'Acesso de {aluno.nome} REATIVADO.')
        return redirect('detalhe_aluno', pk=aluno.pk)
    return redirect('detalhe_aluno', pk=aluno.pk)


@login_required
def salvar_acesso_aluno(request, pk):
    """Define autorização por recurso (SSH/Samba/MySQL/pasta) do aluno."""
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        # marca como inativo tudo e depois reativa o selecionado
        for rec in Recurso.objects.all():
            marcado = request.POST.get(f'recurso_{rec.pk}') == '1'
            AcessoAluno.objects.update_or_create(
                aluno=aluno, recurso=rec,
                defaults={'ativo': marcado},
            )
        messages.success(request, 'Autorizações atualizadas.')
        return redirect('detalhe_aluno', pk=aluno.pk)
    return redirect('detalhe_aluno', pk=aluno.pk)


# ---------------------------------------------------------------------------
# Administração de recursos/turmas/disciplinas (básica)
# ---------------------------------------------------------------------------
@login_required
def admin_recursos(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Acesso restrito a administradores.')
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', '')
        valor = request.POST.get('valor', '').strip()
        if nome and tipo in dict(Recurso.TIPO_CHOICES):
            try:
                Recurso.objects.get_or_create(nome=nome, tipo=tipo, defaults={'valor': valor})
                messages.success(request, f'Recurso {nome} criado.')
            except Exception as e:
                messages.error(request, f'Erro: {e}')
        return redirect('admin_recursos')
    return render(request, 'alunos/admin_recursos.html', {'recursos': Recurso.objects.all()})


# ---------------------------------------------------------------------------
# Recuperação de senha via Google
# ---------------------------------------------------------------------------
def recuperar_senha(request):
    """Recuperação de senha: aluno autentica com a conta Google e redefine a senha SSH/Samba."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        nova = request.POST.get('nova_senha', '').strip()
        confirm = request.POST.get('confirmar', '').strip()
        aluno = Aluno.objects.filter(email=email).first()
        if not aluno:
            messages.error(request, 'Nenhum aluno encontrado com esse email Google.')
        elif nova != confirm or len(nova) < 8:
            messages.error(request, 'Senhas não conferem ou muito curta (mínimo 8).')
        elif not aluno.username_linux:
            messages.error(request, 'Este aluno ainda não tem conta provisionada no servidor.')
        else:
            try:
                services.criar_usuario_linux(aluno.username_linux, nova, grupos=['alunos'])
                services.definir_senha_samba(aluno.username_linux, nova)
                messages.success(request, f'Senha redefinida para o login {aluno.username_linux} (SSH e Samba).')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'Erro ao redefinir senha: {e}')
    return render(request, 'alunos/recuperar_senha.html', {})
