from django.contrib import admin

from .models import AcessoAluno, Aluno, Disciplina, Professor, Recurso, Turma


class AcessoAlunoInline(admin.TabularInline):
    model = AcessoAluno
    extra = 0


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ra', 'username_linux', 'turma', 'ativo', 'data_criacao')
    list_filter = ('ativo', 'turma', 'disciplinas')
    search_fields = ('nome', 'ra', 'email', 'username_linux')
    inlines = [AcessoAlunoInline]
    filter_horizontal = ('disciplinas',)


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email')
    search_fields = ('nome', 'email')
    filter_horizontal = ('turmas',)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'periodo', 'ano_letivo')
    search_fields = ('nome',)


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'valor', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('nome', 'valor')


@admin.register(AcessoAluno)
class AcessoAlunoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'recurso', 'ativo', 'atualizado_em')
    list_filter = ('ativo', 'recurso__tipo')
    search_fields = ('aluno__nome', 'recurso__nome')
