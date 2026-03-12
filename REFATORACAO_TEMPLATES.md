# Guia de Refatoração de Templates - Dark Theme

## Objetivo
Melhorar o layout de todos os templates existentes mantendo funcionalidade, adicionando dark theme e corrigindo a navegação lateral.

---

## 1. PADRÃO DE CORES DARK THEME

### Paleta de Cores
```css
/* Fundos */
--bg-dark: #1a1a1a;
--bg-darker: #0d0d0d;
--bg-light-dark: #2d2d2d;

/* Bordas */
--border-dark: #404040;
--border-light: #505050;

/* Textos */
--text-light: #e0e0e0;
--text-lighter: #f0f0f0;
--text-muted: #a0a0a0;

/* Acentos */
--primary: #0d6efd;
--success: #198754;
--danger: #dc3545;
--warning: #ffc107;
--info: #0dcaf0;
```

### Classes Bootstrap Utilizadas
- `bg-dark`: Fundo escuro
- `text-light`: Texto claro
- `text-muted`: Texto cinzento
- `border-secondary`: Bordas sutis
- `table-dark`: Tabelas escuras
- `table-hover`: Efeito hover em linhas

---

## 2. ESTRUTURA DE TEMPLATE BASE MELHORADA

### Template Base Padrão

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="container-fluid bg-dark min-vh-100 p-0">
    <!-- Navbar Fixa Superior -->
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary sticky-top" style="z-index: 1030;">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="fas fa-icon me-2"></i>{{ titulo }}
            </span>
            <div class="d-flex align-items-center gap-3">
                <span class="text-light">{{ user.get_full_name }}</span>
                <a href="{% url 'logout' %}" class="btn btn-sm btn-outline-danger">
                    <i class="fas fa-sign-out-alt"></i> Sair
                </a>
            </div>
        </div>
    </nav>

    <div class="d-flex" style="margin-top: 58px;">
        <!-- Sidebar Lateral -->
        <nav id="sidebar" class="bg-dark border-end border-secondary" 
             style="width: 250px; height: calc(100vh - 58px); overflow-y: auto; position: fixed; left: 0; top: 58px; transition: all 0.3s ease;">
            
            <div class="p-3">
                <h6 class="text-light text-uppercase mb-3">Menu</h6>
                <ul class="nav flex-column">
                    <li class="nav-item">
                        <a class="nav-link text-light" href="{% url 'home' %}">
                            <i class="fas fa-home me-2"></i> Início
                        </a>
                    </li>
                    <!-- Mais itens de menu -->
                </ul>
            </div>
        </nav>

        <!-- Conteúdo Principal -->
        <main class="flex-grow-1" style="margin-left: 250px; padding: 20px;">
            {% include 'parciais/_messages.html' %}
            
            {% block page_content %}
            {% endblock %}
        </main>
    </div>
</div>

<style>
    #sidebar {
        transition: all 0.3s ease;
    }
    
    .nav-link {
        transition: all 0.3s ease;
        border-radius: 0.25rem;
        color: #e0e0e0 !important;
    }
    
    .nav-link:hover {
        background-color: rgba(255, 255, 255, 0.1);
        color: #0d6efd !important;
    }
    
    .nav-link.active {
        background-color: #0d6efd;
        color: white !important;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        #sidebar {
            width: 200px;
        }
        main {
            margin-left: 200px !important;
        }
    }
</style>

{% endblock %}
```

---

## 3. COMPONENTES PADRÃO

### Card
```html
<div class="card bg-dark border-secondary">
    <div class="card-header bg-dark border-secondary">
        <h5 class="card-title text-light mb-0">Título</h5>
    </div>
    <div class="card-body">
        <!-- Conteúdo -->
    </div>
</div>
```

### Tabela
```html
<div class="table-responsive">
    <table class="table table-dark table-hover">
        <thead class="table-secondary">
            <tr>
                <th>Coluna 1</th>
                <th>Coluna 2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dados</td>
                <td>Dados</td>
            </tr>
        </tbody>
    </table>
</div>
```

### Formulário
```html
<form method="post" class="form">
    {% csrf_token %}
    
    <div class="mb-3">
        <label for="{{ form.campo.id_for_label }}" class="form-label text-light">
            Label
        </label>
        {{ form.campo }}
        {% if form.campo.errors %}
        <div class="text-danger small mt-1">{{ form.campo.errors }}</div>
        {% endif %}
    </div>
    
    <button type="submit" class="btn btn-primary">
        <i class="fas fa-save"></i> Salvar
    </button>
</form>
```

### Botões
```html
<!-- Primário -->
<a href="#" class="btn btn-primary">
    <i class="fas fa-icon"></i> Ação
</a>

<!-- Sucesso -->
<a href="#" class="btn btn-success">
    <i class="fas fa-check"></i> Confirmar
</a>

<!-- Perigo -->
<a href="#" class="btn btn-danger">
    <i class="fas fa-trash"></i> Deletar
</a>

<!-- Pequeno -->
<a href="#" class="btn btn-sm btn-info">
    <i class="fas fa-eye"></i>
</a>
```

### Alertas
```html
{% if messages %}
<div class="alert alert-info alert-dismissible fade show" role="alert">
    {% for message in messages %}
    <div>{{ message }}</div>
    {% endfor %}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}
```

---

## 4. INPUTS E FORMULÁRIOS

### Input Text
```html
<input type="text" class="form-control bg-dark text-light border-secondary" 
       placeholder="Placeholder">
```

### Select
```html
<select class="form-control bg-dark text-light border-secondary">
    <option>Opção 1</option>
    <option>Opção 2</option>
</select>
```

### Textarea
```html
<textarea class="form-control bg-dark text-light border-secondary" 
          rows="3" placeholder="Texto..."></textarea>
```

### Checkbox
```html
<div class="form-check">
    <input type="checkbox" class="form-check-input" id="check1">
    <label class="form-check-label text-light" for="check1">
        Opção
    </label>
</div>
```

### Radio
```html
<div class="form-check">
    <input type="radio" class="form-check-input" name="radio" id="radio1">
    <label class="form-check-label text-light" for="radio1">
        Opção 1
    </label>
</div>
```

---

## 5. CARDS COM ESTATÍSTICAS

```html
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-dark border-secondary">
            <div class="card-body">
                <h6 class="card-title text-light">Métrica</h6>
                <h4 class="text-success">R$ 1.234,56</h4>
            </div>
        </div>
    </div>
    <!-- Mais cards -->
</div>
```

---

## 6. NAVEGAÇÃO LATERAL COM TOGGLE

### HTML
```html
<button id="toggle-sidebar" class="btn btn-dark position-fixed" 
        style="bottom: 20px; right: 20px; z-index: 1040;">
    <i class="fas fa-bars"></i>
</button>

<nav id="sidebar" class="bg-dark border-end border-secondary" 
     style="width: 250px; height: calc(100vh - 58px); overflow-y: auto; 
            position: fixed; left: 0; top: 58px; transition: all 0.3s ease;">
    <!-- Conteúdo do sidebar -->
</nav>
```

### JavaScript
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar');
    const main = document.querySelector('main');
    
    // Verificar estado salvo no localStorage
    const sidebarVisible = localStorage.getItem('sidebarVisible') !== 'false';
    
    if (!sidebarVisible) {
        sidebar.style.left = '-250px';
        main.style.marginLeft = '0';
    }
    
    // Toggle do sidebar
    toggleBtn.addEventListener('click', function() {
        const isVisible = sidebar.style.left === '0px';
        
        if (isVisible) {
            sidebar.style.left = '-250px';
            main.style.marginLeft = '0';
            localStorage.setItem('sidebarVisible', 'false');
        } else {
            sidebar.style.left = '0';
            main.style.marginLeft = '250px';
            localStorage.setItem('sidebarVisible', 'true');
        }
    });
});
```

---

## 7. RESPONSIVIDADE

### Media Queries
```css
/* Tablets */
@media (max-width: 768px) {
    #sidebar {
        width: 200px;
    }
    main {
        margin-left: 200px !important;
    }
}

/* Celulares */
@media (max-width: 576px) {
    #sidebar {
        position: fixed;
        left: -250px;
        width: 250px;
        z-index: 1040;
    }
    main {
        margin-left: 0 !important;
    }
    .navbar {
        padding: 0.5rem 0.5rem;
    }
}
```

---

## 8. CHECKLIST DE REFATORAÇÃO POR TEMPLATE

### Para Cada Template
- [ ] Adicionar navbar fixa superior
- [ ] Adicionar sidebar lateral
- [ ] Converter cores para dark theme
- [ ] Testar responsividade
- [ ] Manter toda funcionalidade JS
- [ ] Manter IDs e classes existentes
- [ ] Testar em diferentes navegadores
- [ ] Validar acessibilidade

### Templates Prioritários
1. `cadastros/cadastros_index.html`
2. `admin_pagamentos/templates/pagamento_*.html`
3. `admin_faturas/templates/fatura_*.html`
4. `admin_conciliacao/templates/conciliacao_*.html`
5. Outros templates de módulos

---

## 9. EXEMPLO COMPLETO DE REFATORAÇÃO

### Antes
```html
{% extends 'base.html' %}

{% block content %}
<div class="container">
    <h1>Título</h1>
    <table class="table">
        <tr>
            <th>Coluna</th>
        </tr>
    </table>
</div>
{% endblock %}
```

### Depois
```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="container-fluid bg-dark min-vh-100 p-0">
    <!-- Navbar -->
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary sticky-top" style="z-index: 1030;">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="fas fa-list me-2"></i>Título
            </span>
        </div>
    </nav>

    <div class="d-flex" style="margin-top: 58px;">
        <!-- Sidebar -->
        <nav id="sidebar" class="bg-dark border-end border-secondary" 
             style="width: 250px; height: calc(100vh - 58px); overflow-y: auto; position: fixed; left: 0; top: 58px;">
            <div class="p-3">
                <h6 class="text-light text-uppercase mb-3">Menu</h6>
                <ul class="nav flex-column">
                    <li class="nav-item">
                        <a class="nav-link text-light" href="#">Item</a>
                    </li>
                </ul>
            </div>
        </nav>

        <!-- Conteúdo -->
        <main class="flex-grow-1" style="margin-left: 250px; padding: 20px;">
            <div class="card bg-dark border-secondary">
                <div class="card-header bg-dark border-secondary">
                    <h5 class="card-title text-light mb-0">Título</h5>
                </div>
                <div class="table-responsive">
                    <table class="table table-dark table-hover">
                        <thead class="table-secondary">
                            <tr>
                                <th>Coluna</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Dados -->
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>
</div>
{% endblock %}
```

---

## 10. DICAS E BOAS PRÁTICAS

### Mantendo Funcionalidade
- Preservar todos os IDs e classes existentes
- Não remover scripts ou funções JavaScript
- Testar após cada mudança
- Usar Git para controle de versão

### Performance
- Usar classes CSS ao invés de estilos inline quando possível
- Minificar CSS e JavaScript
- Otimizar imagens
- Usar lazy loading para imagens

### Acessibilidade
- Manter contraste adequado
- Usar labels em formulários
- Adicionar `aria-label` quando necessário
- Testar com leitores de tela

### Segurança
- Sempre usar `{% csrf_token %}`
- Validar dados no servidor
- Usar `|escape` em templates
- Proteger endpoints com permissões

---

## 11. FERRAMENTAS ÚTEIS

### Validação
```bash
# Validar HTML
python manage.py validate_templates

# Testar responsividade
# Use Chrome DevTools - F12 > Toggle device toolbar
```

### Debugging
```python
# No template
{{ variable|pprint }}

# No console do navegador
console.log(data);
```

---

**Versão**: 1.0  
**Data**: 26 de Fevereiro de 2026  
**Status**: Pronto para Implementação
