"""URLs do app alunos (acesso_lab)."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('recuperar-senha/', views.recuperar_senha, name='recuperar_senha'),

    path('alunos/', views.lista_alunos, name='lista_alunos'),
    path('alunos/novo/', views.criar_aluno, name='criar_aluno'),
    path('alunos/<int:pk>/', views.detalhe_aluno, name='detalhe_aluno'),
    path('alunos/<int:pk>/provisionar/', views.provisionar_conta, name='provisionar_conta'),
    path('alunos/<int:pk>/alternar/', views.alternar_ativo, name='alternar_ativo'),
    path('alunos/<int:pk>/acessos/', views.salvar_acesso_aluno, name='salvar_acesso_aluno'),

    path('recursos/', views.admin_recursos, name='admin_recursos'),
]
