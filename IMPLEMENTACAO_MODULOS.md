# Implementação de Novos Módulos - ManagerONTEC ERP

## Resumo das Mudanças Realizadas

Este documento descreve todas as modificações e novos módulos implementados no projeto ManagerONTEC.

---

## 1. MÓDULO DE TESOURARIA E CAIXA

### Estrutura Criada

#### Modelos (`admin_tesouraria/models.py`)
- **Caixa**: Representa um caixa físico da tesouraria
  - Campos: descricao, tipo, numero_caixa, estabelecimento, responsavel, status
  - Relacionamentos: Estabelecimento, User

- **SaldoCaixa**: Registra o saldo de um caixa em um período específico
  - Campos: caixa, dt_abertura, dt_fechamento, saldo_inicial, saldo_final, total_entradas, total_saidas
  - Métodos: `calcular_saldo_final()`, `save()` com validação de saldo único aberto

- **MovimentacaoCaixa**: Registra cada movimentação de caixa
  - Tipos: ENTRADA_BANCO, ENTRADA_RECEBIMENTO, SAIDA_PAGAMENTO, SAIDA_BANCO, SAIDA_OUTRA
  - Campos: tipo_movimentacao, descricao, valor, data_movimentacao, pagamento (FK), conta_bancaria (FK)
  - Métodos: `save()` e `delete()` com atualização automática de totais

#### Views (`admin_tesouraria/views.py`)
- `tesouraria_index()`: Dashboard principal com estatísticas do dia
- `CaixaListView`: Listagem de caixas com filtros
- `CaixaCreateView`: Criar novo caixa
- `CaixaUpdateView`: Editar caixa
- `CaixaDetailView`: Detalhar caixa com histórico
- `abrir_caixa()`: Abrir novo saldo de caixa
- `fechar_caixa()`: Fechar saldo com cálculo de saldo final
- `MovimentacaoCaixaListView`: Listagem de movimentações
- `MovimentacaoCaixaCreateView`: Registrar movimentação
- `MovimentacaoCaixaUpdateView`: Editar movimentação
- `deletar_movimentacao()`: Deletar movimentação
- `relatorio_tesouraria()`: Relatório por período com filtros

#### Forms (`admin_tesouraria/forms.py`)
- `CaixaForm`: Formulário para criar/editar caixa
- `SaldoCaixaForm`: Formulário para abrir saldo
- `MovimentacaoCaixaForm`: Formulário para movimentações

#### URLs (`admin_tesouraria/urls.py`)
```
/admin_tesouraria/                          - Dashboard
/admin_tesouraria/caixas/                   - Listar caixas
/admin_tesouraria/caixas/criar/             - Criar caixa
/admin_tesouraria/caixas/<id>/              - Detalhar caixa
/admin_tesouraria/caixas/<id>/editar/       - Editar caixa
/admin_tesouraria/caixas/<id>/abrir/        - Abrir caixa
/admin_tesouraria/saldos/<id>/fechar/       - Fechar saldo
/admin_tesouraria/saldos/<id>/movimentacoes/  - Listar movimentações
/admin_tesouraria/saldos/<id>/movimentacoes/criar/ - Criar movimentação
/admin_tesouraria/movimentacoes/<id>/editar/    - Editar movimentação
/admin_tesouraria/movimentacoes/<id>/deletar/   - Deletar movimentação
/admin_tesouraria/relatorio/                - Relatório
```

#### Templates
- `base_tesouraria.html`: Template base com navbar e sidebar
- `tesouraria_index.html`: Dashboard com cards de estatísticas
- `caixa_listar.html`: Listagem de caixas com filtros
- `caixa_form.html`: Formulário de caixa
- (Outros templates para detalhe, abrir, fechar, movimentações)

---

## 2. MÓDULO DE CARTÃO DE PAGAMENTO

### Estrutura Criada

#### Modelos (`admin_pagamentos/models_cartao.py`)

- **CartaoPagamento**: Representa um cartão de crédito/débito
  - Campos: descricao, tipo (CREDITO/DEBITO), numero_cartao, bandeira, estabelecimento, conta_bancaria, limite
  - Dias: dia_fechamento, dia_vencimento

- **TransacaoCartao**: Cada transação individual do cartão
  - Campos: cartao, descricao, valor, data_transacao, categoria, fornecedor, numero_documento
  - Upload: nota_fiscal (PDF, JPG, PNG, PEG)
  - Validadores: FileExtensionValidator

- **FaturaCartao**: Agrupa transações de um período
  - Campos: cartao, mes_referencia, data_fechamento, data_vencimento, valor_total, valor_pago
  - Status: ABERTA, FECHADA, PAGA, PARCIAL
  - Métodos: `calcular_total()`, propriedade `saldo_devedor`

- **PagamentoCartao**: Registra pagamentos de faturas
  - Campos: fatura, valor_pagamento, data_pagamento, forma_pagamento
  - Métodos: `save()` com atualização automática de status da fatura

### Fluxo de Funcionamento

1. Transações do cartão são registradas em `TransacaoCartao`
2. Cada transação pode ter upload de nota fiscal
3. Sistema agrupa transações em `FaturaCartao` por período
4. Pagamentos são registrados em `PagamentoCartao`
5. Status da fatura é atualizado automaticamente (ABERTA → PARCIAL → PAGA)
6. Saldo total do cartão é pago de uma vez no banco

---

## 3. MELHORIAS NO MÓDULO PAGAMENTO

### Novos Campos Adicionados

No modelo `Pagamento` (`admin_pagamentos/models.py`):

```python
# Novos campos para anexos
anexo_boleto = models.FileField(
    upload_to='pagamentos/boletos/',
    blank=True,
    null=True,
    verbose_name='Anexo Boleto',
    validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
)

anexo_nota_fiscal = models.FileField(
    upload_to='pagamentos/notas_fiscais/',
    blank=True,
    null=True,
    verbose_name='Anexo Nota Fiscal',
    validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
)
```

### Características
- Campos opcionais (não obrigatórios)
- Validação de extensões: PDF, JPG, JPEG, PNG, PEG
- Upload separado para boleto e nota fiscal
- Armazenamento em diretórios específicos

---

## 4. MÓDULO DE CONCILIAÇÃO (FORA DO ADMIN)

### Estrutura Criada

#### Templates
- `base_conciliacao.html`: Template base com navbar e sidebar
- `conciliacao_index.html`: Dashboard com estatísticas e ações rápidas
- `extrato_listar.html`: Listagem de extratos com filtros

### Funcionalidades Planejadas
- Importação de extratos (CSV, XLS, PDF)
- Conciliação de transações
- Gestão de divergências
- Relatórios de conciliação

---

## 5. LAYOUT E TEMPLATES

### Padrão Dark Theme Implementado

#### Características
- Fundo escuro (`bg-dark`)
- Texto claro (`text-light`)
- Bordas sutis (`border-secondary`)
- Navbar fixa superior com z-index 1030
- Sidebar lateral fixa com 250px de largura
- Conteúdo principal com margin-left ajustado
- Transições suaves em elementos interativos

#### Cores Utilizadas
- **Primária**: `#0d6efd` (Azul)
- **Sucesso**: `#198754` (Verde)
- **Perigo**: `#dc3545` (Vermelho)
- **Aviso**: `#ffc107` (Amarelo)
- **Info**: `#0dcaf0` (Ciano)
- **Fundo**: `#212529` (Cinza escuro)

#### Componentes Padrão
- Cards com `bg-dark border-secondary`
- Tabelas com `table-dark table-hover`
- Botões com classes Bootstrap padrão
- Formulários com inputs `bg-dark text-light border-secondary`
- Select2 integrado para dropdowns

---

## 6. INTEGRAÇÃO NO PROJETO

### URLs Principais Adicionadas

No arquivo `managerontec/urls.py`:
```python
path('admin_tesouraria/', include('admin_tesouraria.urls')),
```

### Permissões Django Padrão

Todos os módulos utilizam o sistema de permissões padrão do Django:
- `view_<model>`: Visualizar
- `add_<model>`: Criar
- `change_<model>`: Editar
- `delete_<model>`: Deletar

Exemplo:
- `admin_tesouraria.view_caixa`
- `admin_tesouraria.add_caixa`
- `admin_tesouraria.change_caixa`
- `admin_tesouraria.delete_caixa`

---

## 7. INSTRUÇÕES DE INSTALAÇÃO

### Pré-requisitos
```bash
# Ativar ambiente virtual (Linux)
source venv/bin/activate

# Ativar ambiente virtual (Windows)
venv\Scripts\activate
```

### Instalação de Dependências
```bash
pip install -r requirements.txt
```

### Criar Migrações
```bash
# Tesouraria
python manage.py migrate admin_tesouraria

# Pagamentos (para novos campos)
python manage.py makemigrations admin_pagamentos
python manage.py migrate admin_pagamentos
```

### Coletar Arquivos Estáticos
```bash
python manage.py collectstatic --noinput
```

### Executar Servidor
```bash
python manage.py runserver
```

---

## 8. ESTRUTURA DE DIRETÓRIOS

```
managerontec/
├── admin_tesouraria/
│   ├── migrations/
│   │   └── 0001_initial.py
│   ├── templates/tesouraria/
│   │   ├── base_tesouraria.html
│   │   ├── tesouraria_index.html
│   │   ├── caixa_listar.html
│   │   ├── caixa_form.html
│   │   └── ... (outros templates)
│   ├── models.py (REESCRITO)
│   ├── views.py (REESCRITO)
│   ├── forms.py (NOVO)
│   ├── urls.py (NOVO)
│   └── admin.py
│
├── admin_pagamentos/
│   ├── models_cartao.py (NOVO)
│   ├── models.py (MODIFICADO - adicionados anexos)
│   ├── templates/cartao/
│   └── ...
│
├── admin_conciliacao/
│   ├── templates/conciliacao/
│   │   ├── base_conciliacao.html
│   │   ├── conciliacao_index.html
│   │   ├── extrato_listar.html
│   │   └── ...
│   └── ...
│
└── managerontec/
    └── urls.py (MODIFICADO - adicionada URL de tesouraria)
```

---

## 9. PRÓXIMOS PASSOS

### Imediato
1. Executar migrações no seu ambiente local
2. Testar acesso aos novos módulos
3. Verificar permissões de usuários

### Curto Prazo
1. Completar templates faltantes de tesouraria
2. Implementar views de cartão de pagamento
3. Implementar importação de extratos (CSV, XLS, PDF)
4. Criar formulários para cartão de pagamento

### Médio Prazo
1. Integrar módulos ao cadastro_index
2. Refatorar todos os templates existentes com novo layout
3. Testes de integração entre módulos
4. Documentação de API (se necessário)

### Longo Prazo
1. Relatórios avançados
2. Exportação de dados
3. Integração com bancos (APIs)
4. Automações e agendamentos

---

## 10. NOTAS IMPORTANTES

### Banco de Dados
- Projeto usa SQLite3 localmente
- Em produção: MySQL no GCP Cloud Run
- Migrações devem ser executadas antes de usar os novos módulos

### Arquivos de Upload
- Boletos: `media/pagamentos/boletos/`
- Notas Fiscais (Pagamento): `media/pagamentos/notas_fiscais/`
- Notas Fiscais (Cartão): `media/cartao/notas_fiscais/`
- Extratos: `media/extratos_bancarios/`

### Variáveis de Ambiente (.env)
Certifique-se de que todas as variáveis estão configuradas:
```
DEBUG=True
USE_SQLITE=True
SECRET_KEY=...
FERNET_KEY=...
ALLOWED_HOSTS=127.0.0.1,localhost
```

### Permissões de Usuários
Para acessar os novos módulos, usuários precisam ter as permissões apropriadas:
```python
# No Django Admin ou via código
user.user_permissions.add(
    Permission.objects.get(codename='view_caixa'),
    Permission.objects.get(codename='add_caixa'),
    # ... etc
)
```

---

## 11. TROUBLESHOOTING

### Erro: "No module named 'admin_tesouraria'"
- Verifique se `admin_tesouraria` está em `INSTALLED_APPS` no settings.py
- Verifique se o arquivo `__init__.py` existe na pasta

### Erro: "ModuleNotFoundError: No module named 'forms'"
- Certifique-se de que `forms.py` foi criado em `admin_tesouraria/`
- Verifique a importação no arquivo

### Erro: "TemplateDoesNotExist"
- Verifique se a pasta `templates/tesouraria/` existe
- Verifique o nome exato do arquivo template
- Limpe cache: `python manage.py clear_cache`

### Erro ao fazer upload de arquivo
- Verifique permissões da pasta `media/`
- Verifique se o arquivo tem extensão válida
- Verifique tamanho máximo de upload

---

## 12. CONTATO E SUPORTE

Para dúvidas ou problemas:
1. Verifique este documento
2. Consulte a documentação do Django
3. Verifique logs do servidor: `python manage.py runserver --verbosity 3`

---

**Data de Implementação**: 26 de Fevereiro de 2026  
**Versão**: 1.0  
**Status**: Pronto para Implementação
