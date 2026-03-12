# Integração dos Novos Módulos no cadastro_index

## Objetivo
Adicionar links para os novos módulos (Tesouraria, Cartão, Conciliação) no menu principal `cadastro_index`, mantendo o padrão de permissões e layout existente.

---

## 1. MODIFICAÇÃO DO TEMPLATE cadastro_index.html

### Localização
`admin_cadastros/templates/cadastros/cadastros_index.html`

### Estrutura Atual
O template provavelmente possui uma estrutura similar a:
```html
<div class="container">
    <div class="row">
        <!-- Cards de módulos -->
        <div class="col-md-4">
            <div class="card">
                <h5>Módulo Existente</h5>
                <a href="...">Acessar</a>
            </div>
        </div>
    </div>
</div>
```

### Adicionar Novos Módulos

Insira os seguintes blocos no template:

#### 1. Card de Tesouraria
```html
<div class="col-md-4 mb-3">
    <div class="card bg-dark border-secondary h-100">
        <div class="card-body">
            <h5 class="card-title text-light">
                <i class="fas fa-cash-register me-2"></i>Tesouraria
            </h5>
            <p class="card-text text-muted">
                Gestão de caixas, movimentações e saldos
            </p>
            {% if perms.admin_tesouraria.view_caixa %}
            <a href="{% url 'admin_tesouraria:index' %}" class="btn btn-primary btn-sm">
                <i class="fas fa-arrow-right"></i> Acessar
            </a>
            {% else %}
            <button class="btn btn-secondary btn-sm" disabled>
                Sem Permissão
            </button>
            {% endif %}
        </div>
    </div>
</div>
```

#### 2. Card de Cartão de Pagamento
```html
<div class="col-md-4 mb-3">
    <div class="card bg-dark border-secondary h-100">
        <div class="card-body">
            <h5 class="card-title text-light">
                <i class="fas fa-credit-card me-2"></i>Cartão de Pagamento
            </h5>
            <p class="card-text text-muted">
                Controle de transações e faturas de cartão
            </p>
            {% if perms.admin_pagamentos.view_cartaopagamento %}
            <a href="{% url 'admin_pagamentos:cartao_index' %}" class="btn btn-primary btn-sm">
                <i class="fas fa-arrow-right"></i> Acessar
            </a>
            {% else %}
            <button class="btn btn-secondary btn-sm" disabled>
                Sem Permissão
            </button>
            {% endif %}
        </div>
    </div>
</div>
```

#### 3. Card de Conciliação
```html
<div class="col-md-4 mb-3">
    <div class="card bg-dark border-secondary h-100">
        <div class="card-body">
            <h5 class="card-title text-light">
                <i class="fas fa-sync-alt me-2"></i>Conciliação Bancária
            </h5>
            <p class="card-text text-muted">
                Importação e conciliação de extratos
            </p>
            {% if perms.admin_conciliacao.view_extratobancario %}
            <a href="{% url 'admin_conciliacao:index' %}" class="btn btn-primary btn-sm">
                <i class="fas fa-arrow-right"></i> Acessar
            </a>
            {% else %}
            <button class="btn btn-secondary btn-sm" disabled>
                Sem Permissão
            </button>
            {% endif %}
        </div>
    </div>
</div>
```

---

## 2. ADICIONAR URLS AO admin_pagamentos/urls.py

Se ainda não existir, crie a view e URL para cartão:

```python
# admin_pagamentos/urls.py

from django.urls import path
from . import views

app_name = 'admin_pagamentos'

urlpatterns = [
    # URLs existentes...
    
    # Cartão de Pagamento
    path('cartao/', views.cartao_index, name='cartao_index'),
    path('cartao/listar/', views.CartaoListView.as_view(), name='cartao_listar'),
    path('cartao/criar/', views.CartaoCreateView.as_view(), name='cartao_criar'),
    path('cartao/<int:pk>/', views.CartaoDetailView.as_view(), name='cartao_detalhe'),
    path('cartao/<int:pk>/editar/', views.CartaoUpdateView.as_view(), name='cartao_editar'),
    
    # Transações
    path('cartao/<int:cartao_id>/transacoes/', views.TransacaoListView.as_view(), name='transacao_listar'),
    path('cartao/<int:cartao_id>/transacoes/criar/', views.TransacaoCreateView.as_view(), name='transacao_criar'),
    path('transacoes/<int:pk>/editar/', views.TransacaoUpdateView.as_view(), name='transacao_editar'),
    
    # Faturas
    path('cartao/<int:cartao_id>/faturas/', views.FaturaListView.as_view(), name='fatura_listar'),
    path('faturas/<int:pk>/', views.FaturaDetailView.as_view(), name='fatura_detalhe'),
    
    # Pagamentos
    path('faturas/<int:fatura_id>/pagamentos/criar/', views.PagamentoCreateView.as_view(), name='pagamento_criar'),
]
```

---

## 3. CRIAR VIEWS BÁSICAS PARA CARTÃO

```python
# admin_pagamentos/views.py (adicionar ao final)

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from .models_cartao import CartaoPagamento, TransacaoCartao, FaturaCartao

@login_required
def cartao_index(request):
    """Dashboard de cartão de pagamento"""
    cartoes = CartaoPagamento.objects.filter(
        estabelecimento_id=request.session.get('estabelecimento_id'),
        status='A'
    )
    context = {
        'titulo': 'Cartão de Pagamento',
        'cartoes': cartoes,
    }
    return render(request, 'cartao/cartao_index.html', context)


class CartaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CartaoPagamento
    template_name = 'cartao/cartao_listar.html'
    context_object_name = 'cartoes'
    permission_required = 'admin_pagamentos.view_cartaopagamento'
    
    def get_queryset(self):
        return CartaoPagamento.objects.filter(
            estabelecimento_id=self.request.session.get('estabelecimento_id')
        )


class CartaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CartaoPagamento
    template_name = 'cartao/cartao_form.html'
    permission_required = 'admin_pagamentos.add_cartaopagamento'
    fields = ['descricao', 'tipo', 'numero_cartao', 'bandeira', 'conta_bancaria', 'limite', 'dia_fechamento', 'dia_vencimento']
    
    def form_valid(self, form):
        form.instance.estabelecimento_id = self.request.session.get('estabelecimento_id')
        form.instance.us_registro = self.request.user
        return super().form_valid(form)


class CartaoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CartaoPagamento
    template_name = 'cartao/cartao_detalhe.html'
    permission_required = 'admin_pagamentos.view_cartaopagamento'
    context_object_name = 'cartao'
```

---

## 4. CRIAR TEMPLATE cartao_index.html

```html
{% extends 'cartao/base_cartao.html' %}
{% load static %}

{% block cartao_content %}
<div class="container-fluid">
    <div class="row mb-3">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center">
                <h3 class="text-light">Cartões de Pagamento</h3>
                {% if perms.admin_pagamentos.add_cartaopagamento %}
                <a href="{% url 'admin_pagamentos:cartao_criar' %}" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Novo Cartão
                </a>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Cards de cartões -->
    <div class="row">
        {% for cartao in cartoes %}
        <div class="col-md-6 col-lg-4 mb-3">
            <div class="card bg-dark border-secondary h-100">
                <div class="card-body">
                    <h5 class="card-title text-light">{{ cartao.descricao }}</h5>
                    <p class="card-text text-muted">
                        <strong>{{ cartao.bandeira }}</strong> - {{ cartao.get_tipo_display }}
                    </p>
                    <p class="card-text text-muted small">
                        Número: ****{{ cartao.numero_cartao }}
                    </p>
                    {% if cartao.limite %}
                    <p class="card-text text-muted small">
                        Limite: R$ {{ cartao.limite|floatformat:2 }}
                    </p>
                    {% endif %}
                    <div class="d-flex gap-2">
                        <a href="{% url 'admin_pagamentos:cartao_detalhe' cartao.pk %}" class="btn btn-sm btn-info">
                            <i class="fas fa-eye"></i> Ver
                        </a>
                        {% if perms.admin_pagamentos.change_cartaopagamento %}
                        <a href="{% url 'admin_pagamentos:cartao_editar' cartao.pk %}" class="btn btn-sm btn-warning">
                            <i class="fas fa-edit"></i> Editar
                        </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-12">
            <p class="text-muted">Nenhum cartão cadastrado.</p>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

---

## 5. AJUSTAR PERMISSÕES DE USUÁRIOS

No Django Admin, para dar acesso aos novos módulos:

```python
# Via Django Shell
from django.contrib.auth.models import Permission, User

user = User.objects.get(username='seu_usuario')

# Adicionar permissões de tesouraria
user.user_permissions.add(
    Permission.objects.get(codename='view_caixa'),
    Permission.objects.get(codename='add_caixa'),
    Permission.objects.get(codename='change_caixa'),
)

# Adicionar permissões de cartão
user.user_permissions.add(
    Permission.objects.get(codename='view_cartaopagamento'),
    Permission.objects.get(codename='add_cartaopagamento'),
    Permission.objects.get(codename='change_cartaopagamento'),
)

# Adicionar permissões de conciliação
user.user_permissions.add(
    Permission.objects.get(codename='view_extratobancario'),
    Permission.objects.get(codename='add_extratobancario'),
)
```

---

## 6. ESTILO CSS PADRÃO

Adicione ao `<head>` dos templates base se necessário:

```html
<style>
    .card {
        transition: all 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(255, 255, 255, 0.1);
    }
    
    .btn-group-vertical .btn {
        border-radius: 0.25rem;
    }
</style>
```

---

## 7. CHECKLIST DE INTEGRAÇÃO

- [ ] Adicionar cards ao `cadastro_index.html`
- [ ] Criar views para cartão de pagamento
- [ ] Criar URLs para cartão de pagamento
- [ ] Criar templates para cartão
- [ ] Testar acesso aos módulos
- [ ] Configurar permissões de usuários
- [ ] Testar com diferentes níveis de permissão
- [ ] Validar layout dark theme
- [ ] Testar responsividade em mobile

---

## 8. NOTAS IMPORTANTES

### Permissões
- Sempre verificar `perms.app.codename` nos templates
- Usar `@permission_required` ou `PermissionRequiredMixin` nas views
- Criar grupos de usuários para facilitar gerenciamento

### URLs
- Manter consistência de nomenclatura
- Usar `reverse_lazy` para redirecionamentos
- Sempre usar `{% url %}` nos templates

### Segurança
- Validar `estabelecimento_id` da sessão
- Filtrar querysets por estabelecimento
- Usar `PROTECT` em ForeignKeys críticas

---

**Versão**: 1.0  
**Data**: 26 de Fevereiro de 2026
