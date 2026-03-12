# Adicionar este decorator no início do arquivo admin_conciliacao/views.py

from django.db import OperationalError
from django.shortcuts import redirect
from functools import wraps

def handle_database_error(view_func):
    """Decorator para tratar erros de banco de dados em views de conciliação"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OperationalError as e:
            error_msg = str(e)
            if 'no such table' in error_msg:
                messages.error(
                    request,
                    'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_conciliacao'
                )
            elif 'no such column' in error_msg:
                messages.error(
                    request,
                    'Estrutura do banco de dados está desatualizada. Execute: python manage.py migrate admin_conciliacao'
                )
            else:
                messages.error(request, f'Erro no banco de dados: {error_msg}')
            return redirect('cadastros_index')
    return wrapper


# Aplicar o decorator em todas as views:
# @handle_database_error
# def index_conciliacao(request):
#     ...

# @handle_database_error
# def listar_extratos(request):
#     ...

# E assim por diante para todas as outras views
