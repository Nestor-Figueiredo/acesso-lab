"""Modelos do acesso_lab — Controle de Acesso SSH/Samba/MySQL do laboratório."""
from django.contrib.auth.models import User
from django.db import models


class Turma(models.Model):
    """Turma de alunos (ex: 3º Ano A, Técnico em Desenvolvimento de Sistemas)."""
    nome = models.CharField('Turma', max_length=80, unique=True)
    periodo = models.CharField('Período', max_length=40, blank=True)  # manhã/tarde/noite
    ano_letivo = models.CharField('Ano letivo', max_length=9, blank=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Disciplina(models.Model):
    """Disciplina (ex: Desenvolvimento Web, Banco de Dados)."""
    nome = models.CharField('Disciplina', max_length=80, unique=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Recurso(models.Model):
    """Recurso de sistema que pode ser liberado ao aluno.
    Tipos principais: ssh, samba, mysql, pasta.
    """
    TIPO_CHOICES = [
        ('ssh', 'SSH (terminal)'),
        ('samba', 'Samba (compartilhamento de arquivos)'),
        ('mysql', 'MySQL (database próprio)'),
        ('pasta', 'Pasta de arquivos (share)'),
    ]
    nome = models.CharField('Nome', max_length=60)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField('Descrição', blank=True)
    # p/ mysql: nome do database; p/ samba/pasta: caminho do share; p/ ssh: 'shell'
    valor = models.CharField('Valor/parâmetro', max_length=120, blank=True,
                             help_text='Ex: nome do database MySQL, caminho do share, ou "shell" p/ SSH')

    class Meta:
        ordering = ['tipo', 'nome']
        unique_together = ('nome', 'tipo')

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'


class Aluno(models.Model):
    """Aluno do laboratório. O username (login Linux/SSH/Samba) é gerado a partir do nome."""
    nome = models.CharField('Nome completo', max_length=120)
    email = models.EmailField('Email Google (@escola.edu.br)', unique=True)
    ra = models.CharField('RA/Matrícula', max_length=40, unique=True, blank=True)
    turma = models.ForeignKey(Turma, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='alunos')
    disciplinas = models.ManyToManyField(Disciplina, blank=True, related_name='alunos',
                                         verbose_name='Disciplinas matriculadas')
    username_linux = models.CharField('Login Linux/SSH/Samba', max_length=32, unique=True, blank=True,
                                      help_text='Preenchido automaticamente na criação da conta.')
    ativo = models.BooleanField('Acesso ativo', default=True,
                                help_text='Desativar bloqueia SSH+Samba+MySQL na hora.')
    data_criacao = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def recursos_habilitados(self):
        """Recursos que o aluno PODE usar (Recurso com acesso ativo)."""
        return Recurso.objects.filter(
            acessoaluno__aluno=self,
            acessoaluno__ativo=True,
        )


class Professor(models.Model):
    """Professor que administra o laboratório (login via Google no Django)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='professor')
    nome = models.CharField('Nome', max_length=120)
    email = models.EmailField('Email Google', unique=True)
    turmas = models.ManyToManyField(Turma, blank=True, related_name='professores')

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class AcessoAluno(models.Model):
    """Autorização por recurso: quais recursos cada aluno PODE usar e status."""
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='acessos')
    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name='acessos_alunos')
    ativo = models.BooleanField('Autorizado', default=True)
    # p/ mysql: senha do database do aluno (armazenada aqui p/ exibição ao aluno)
    senha_recurso = models.CharField('Senha do recurso (ex: db MySQL)', max_length=128, blank=True)
    observacao = models.CharField('Observação', max_length=200, blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        ordering = ['aluno', 'recurso']
        unique_together = ('aluno', 'recurso')

    def __str__(self):
        return f'{self.aluno} → {self.recurso}'
