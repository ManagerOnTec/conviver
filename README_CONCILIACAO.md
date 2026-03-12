# ManagerOntec ERP - Módulo de Conciliação Bancária

## Resumo das Alterações

Este arquivo contém o ERP ManagerOntec com o novo módulo de **Conciliação Bancária** (`admin_conciliacao`) totalmente implementado e integrado.

### O que foi adicionado:

1. **Novo Aplicativo Django**: `admin_conciliacao/`
   - Modelos para gerenciar extratos, transações e conciliações
   - Views para interface web
   - Forms para entrada de dados
   - Admin customizado com interface amigável
   - URLs e rotas integradas

2. **Documentação Completa**:
   - `MODULO_CONCILIACAO.md`: Documentação técnica detalhada
   - `ANALISE_PROJETO.md`: Análise do projeto e planejamento

3. **Correções e Melhorias**:
   - Configuração de SQLite para desenvolvimento local
   - Adição de TEMPLATES no settings.py
   - Correção de importações de dependências
   - Arquivo .env configurado corretamente

## Instalação e Configuração

### Pré-requisitos

- Python 3.11+
- pip (gerenciador de pacotes Python)
- Git (opcional)

### Passo 1: Criar Ambiente Virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Passo 2: Instalar Dependências

```bash
# Instalar todas as dependências
pip install -r requirements_local.txt

# Ou usar o requirements.txt original (pode incluir dependências extras)
pip install -r requirements.txt
```

### Passo 3: Configurar Variáveis de Ambiente

O arquivo `.env` já está configurado para desenvolvimento local com SQLite. Se precisar fazer alterações:

```bash
# Editar o arquivo .env
# Configurações importantes:
DEBUG=True
USE_SQLITE=True
SECRET_KEY=sua_chave_secreta_aqui
FERNET_KEY=sua_chave_fernet_aqui
ALLOWED_HOSTS=127.0.0.1,localhost
```

### Passo 4: Executar Migrações

```bash
# Aplicar todas as migrações
python manage.py migrate

# Ou apenas as migrações do novo módulo
python manage.py migrate admin_conciliacao
```

### Passo 5: Criar Superusuário (Primeiro Acesso)

```bash
python manage.py createsuperuser
```

### Passo 6: Iniciar o Servidor

```bash
python manage.py runserver
```

Acesse o sistema em: `http://127.0.0.1:8000/`

## Acessando o Módulo de Conciliação

### Via Django Admin

1. Acesse: `http://127.0.0.1:8000/admin/`
2. Faça login com suas credenciais
3. Procure por "Conciliação" na seção de aplicativos

### Via URLs Diretas

- **Dashboard**: `http://127.0.0.1:8000/admin_conciliacao/`
- **Extratos**: `http://127.0.0.1:8000/admin_conciliacao/extratos/`
- **Conciliação**: `http://127.0.0.1:8000/admin_conciliacao/conciliar/`
- **Divergências**: `http://127.0.0.1:8000/admin_conciliacao/divergências/`

## Fluxo de Uso Básico

### 1. Importar Extrato Bancário

1. Acesse: `http://127.0.0.1:8000/admin_conciliacao/extratos/criar/`
2. Preencha os dados:
   - Competência Bancária
   - Conta Bancária
   - Tipo de Arquivo (CSV)
   - Arquivo (upload do CSV)
   - Datas do extrato
   - Saldos inicial e final
3. Clique em "Salvar"
4. O sistema processará automaticamente as transações

### 2. Conciliar Transações

1. Acesse: `http://127.0.0.1:8000/admin_conciliacao/conciliar/`
2. Use os filtros para encontrar transações
3. Selecione uma transação do extrato
4. Selecione o movimento interno correspondente
5. Clique em "Conciliar"

### 3. Resolver Divergências

1. Acesse: `http://127.0.0.1:8000/admin_conciliacao/divergências/`
2. Visualize as divergências não resolvidas
3. Clique em uma divergência para ver detalhes
4. Registre a solução e marque como resolvida

## Formato do Arquivo CSV

Crie um arquivo CSV com as seguintes colunas:

```csv
data,descricao,tipo,valor,numero_documento,referencia_banco
01/02/2026,Depósito Cheque,C,1000.00,CHQ001,REF001
02/02/2026,Transferência Fornecedor,D,500.00,TRF001,REF002
03/02/2026,Juros,C,50.00,,REF003
```

**Colunas obrigatórias:**
- `data`: DD/MM/YYYY
- `descricao`: Texto
- `tipo`: D (Débito) ou C (Crédito)
- `valor`: Número com ponto como separador decimal

**Colunas opcionais:**
- `numero_documento`: Texto
- `referencia_banco`: Texto

## Estrutura de Diretórios

```
managerontec/
├── admin_conciliacao/           # Novo módulo
│   ├── migrations/
│   │   └── 0001_initial.py
│   ├── admin.py                 # Configuração do Django Admin
│   ├── apps.py
│   ├── forms.py                 # Formulários
│   ├── models.py                # Modelos de dados
│   ├── urls.py                  # Rotas
│   ├── views.py                 # Views/Controllers
│   └── tests.py
├── MODULO_CONCILIACAO.md        # Documentação técnica
├── ANALISE_PROJETO.md           # Análise do projeto
├── README_CONCILIACAO.md        # Este arquivo
├── requirements_local.txt       # Dependências para desenvolvimento
├── .env                         # Variáveis de ambiente
├── manage.py
└── ... (outros arquivos do projeto)
```

## Modelos de Dados

### ExtratoBancario
Armazena informações dos extratos importados.

### TransacaoExtrato
Registra cada transação individual do extrato.

### Conciliacao
Registra a conciliação entre transações do extrato e movimentos internos.

### DivergenciaConciliacao
Registra divergências encontradas durante a conciliação.

Para mais detalhes, consulte `MODULO_CONCILIACAO.md`.

## Próximos Passos

1. **Criar Competência Bancária**: Acesse o admin e crie uma competência para o período desejado
2. **Criar Conta Bancária**: Configure as contas bancárias da empresa
3. **Importar Extrato**: Faça upload de um extrato em CSV
4. **Conciliar**: Comece a conciliar transações

## Troubleshooting

### Erro: "No module named 'admin_conciliacao'"
Certifique-se de que o app foi adicionado a `INSTALLED_APPS` em `settings.py`.

### Erro: "Tabelas não encontradas"
Execute: `python manage.py migrate admin_conciliacao`

### Erro: "Arquivo CSV inválido"
Verifique se o arquivo tem as colunas corretas e o encoding está em UTF-8.

### Erro: "Competência Bancária não encontrada"
Crie uma competência bancária no admin antes de importar o extrato.

## Configuração para Produção

Para usar em produção com MySQL:

1. Instale o driver MySQL:
   ```bash
   pip install mysqlclient
   ```

2. Configure o `.env`:
   ```
   USE_SQLITE=False
   DB_NAME=seu_banco
   DB_USER=seu_usuario
   DB_PASSWORD=sua_senha
   DB_HOST=seu_host
   DB_PORT=3306
   ```

3. Configure o Google Cloud Storage (se usar GCP):
   ```
   GS_PROJECT_ID=seu_projeto
   GS_BUCKET_NAME=seu_bucket
   GCP_SERVICE_ACCOUNT_JSON_BASE64=sua_chave_base64
   ```

4. Gere novas chaves de segurança:
   ```bash
   python -c "import string as s;from secrets import SystemRandom as SR;print(''.join(SR().choices(s.ascii_letters + s.digits + s.punctuation, k=64)));"
   ```

## Suporte e Documentação

- **Documentação Técnica**: Veja `MODULO_CONCILIACAO.md`
- **Análise do Projeto**: Veja `ANALISE_PROJETO.md`
- **Django Docs**: https://docs.djangoproject.com/

## Informações do Projeto

- **Versão**: 1.0
- **Data**: Fevereiro de 2026
- **Desenvolvido por**: Manus AI
- **Banco de Dados Local**: SQLite3
- **Banco de Dados Produção**: MySQL + Google Cloud Platform

---

**Última atualização**: Fevereiro de 2026
