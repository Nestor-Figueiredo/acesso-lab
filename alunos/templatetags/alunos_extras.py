"""Filtros de template do app alunos."""
from django import template

register = template.Library()


@register.filter(name='filter_recurso')
def filter_recurso(acessos, recurso_pk):
    """Retorna o AcessoAluno de um recurso específico (ou um objeto vazio)."""
    try:
        return acessos.get(recurso_id=int(recurso_pk))
    except Exception:
        class _Vazio:
            ativo = False
        return _Vazio()
