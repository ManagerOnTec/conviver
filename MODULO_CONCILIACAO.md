# Módulo de Conciliação Bancária - ManagerOntec ERP

## Visão Geral

O módulo de conciliação bancária (`admin_conciliacao`) foi desenvolvido para o ERP ManagerOntec com o objetivo de automatizar e facilitar o processo de reconciliação entre os extratos bancários e os movimentos financeiros registrados internamente no sistema.

## Características Principais

### 1. Importação de Extratos Bancários
- Suporte para upload de arquivos em formato CSV
- Processamento automático de transações
- Cálculo de totais de entrada e saída
- Armazenamento seguro de arquivos

### 2. Gestão de Transações
- Registro individual de cada transação do extrato
- Classificação por tipo (débito/crédito)
- Rastreamento de status de conciliação
- Busca e filtros avançados

### 3. Conciliação Inteligente
- Associação automática de transações com movimentos internos
- Detecção de divergências
- Cálculo de diferenças de valor
- Status de conciliação (Pendente, Conciliado, Divergente, Anulado)

### 4. Gestão de Divergências
- Registro de divergências encontradas
- Classificação por tipo (valor, data, faltante, excedente, duplicada)
- Priorização (Alta, Média, Baixa)
- Rastreamento de resolução

## Estrutura de Dados

### Modelos

#### ExtratoBancario
Armazena informações do extrato bancário importado.

**Campos principais:**
- `competencia_bancaria`: Referência à competência bancária
- `conta`: Conta bancária associada
- `arquivo`: Arquivo do extrato (CSV/OFX)
- `data_extrato_inicio` e `data_extrato_fim`: Período do extrato
- `saldo_inicial` e `saldo_final`: Saldos do período
- `total_entradas` e `total_saidas`: Totalizadores
- `quantidade_transacoes`: Número de transações importadas

#### TransacaoExtrato
Registra cada transação individual do extrato.

**Campos principais:**
- `extrato_bancario`: Referência ao extrato
- `data_transacao`: Data da transação
- `descricao`: Descrição da transação
- `tipo_transacao`: Débito (D) ou Crédito (C)
- `valor`: Valor da transação
- `numero_documento`: Número do documento
- `referencia_banco`: Referência do banco
- `conciliada`: Status de conciliação

#### Conciliacao
Registra a conciliação entre transações do extrato e movimentos internos.

**Campos principais:**
- `transacao_extrato`: Transação do extrato
- `movimento_bancario`: Movimento interno associado
- `competencia_bancaria`: Período de conciliação
- `valor_conciliado`: Valor conciliado
- `diferenca`: Diferença calculada
- `status`: Status (Pendente, Conciliado, Divergente, Anulado)
- `motivo_divergencia`: Descrição da divergência

#### DivergenciaConciliacao
Registra divergências encontradas durante a conciliação.

**Campos principais:**
- `conciliacao`: Referência à conciliação
- `tipo_divergencia`: Tipo de divergência
- `descricao`: Descrição detalhada
- `prioridade`: Nível de prioridade
- `resolvida`: Status de resolução
- `solucao`: Descrição da solução aplicada

## Interfaces e Views

### Views Principais

#### `index_conciliacao`
Dashboard principal com estatísticas gerais:
- Total de extratos
- Transações pendentes de conciliação
- Conciliações realizadas
- Divergências não resolvidas

#### `listar_extratos`
Lista todos os extratos bancários importados com filtros por competência e conta.

#### `criar_extrato`
Formulário para upload de novo extrato bancário com processamento automático.

#### `detalhar_extrato`
Visualiza detalhes de um extrato e suas transações.

#### `conciliar_transacoes`
Interface principal de conciliação com:
- Lista de transações do extrato não conciliadas
- Lista de movimentos internos
- Filtros avançados (data, valor, descrição)
- Ações de conciliação

#### `listar_conciliações`
Lista todas as conciliações realizadas com filtros por status e competência.

#### `listar_divergencias`
Lista todas as divergências com filtros por tipo, prioridade e status de resolução.

## Formulários

### ExtratoBancarioForm
Formulário para criação de novo extrato com validação de datas.

### TransacaoExtratoForm
Formulário para criação manual de transações.

### ConciliacaoForm
Formulário para conciliação com cálculo automático de diferenças.

### FiltrosConciliacaoForm
Formulário avançado de filtros para a tela de conciliação.

## Integração com o Django Admin

Todos os modelos foram registrados no Django Admin com:
- Listagens customizadas com campos coloridos
- Filtros por status, tipo, data e prioridade
- Busca por descrição e referências
- Campos somente leitura para auditoria
- Fieldsets organizados por seção

## Rotas (URLs)

```
/admin_conciliacao/                          # Dashboard principal
/admin_conciliacao/extratos/                 # Listar extratos
/admin_conciliacao/extratos/criar/           # Criar novo extrato
/admin_conciliacao/extratos/<id>/            # Detalhes do extrato
/admin_conciliacao/conciliar/                # Tela de conciliação
/admin_conciliacao/conciliar/criar/          # Criar conciliação
/admin_conciliacao/conciliações/             # Listar conciliações
/admin_conciliacao/conciliações/<id>/        # Detalhes da conciliação
/admin_conciliacao/divergências/             # Listar divergências
```

## Fluxo de Uso

### 1. Importação de Extrato
1. Acesse `/admin_conciliacao/extratos/criar/`
2. Selecione a competência bancária
3. Escolha a conta bancária
4. Faça upload do arquivo CSV
5. Preencha os saldos inicial e final
6. Clique em "Salvar"
7. O sistema processará automaticamente as transações

### 2. Conciliação de Transações
1. Acesse `/admin_conciliacao/conciliar/`
2. Aplique filtros conforme necessário
3. Selecione uma transação do extrato
4. Selecione o movimento interno correspondente
5. Clique em "Conciliar"
6. O sistema calculará automaticamente as diferenças

### 3. Gestão de Divergências
1. Acesse `/admin_conciliacao/divergências/`
2. Visualize divergências não resolvidas
3. Priorize as divergências
4. Registre a solução aplicada
5. Marque como resolvida

## Formato do Arquivo CSV

O arquivo CSV deve conter as seguintes colunas:

```
data,descricao,tipo,valor,numero_documento,referencia_banco
01/02/2026,Depósito Cheque,C,1000.00,CHQ001,REF001
02/02/2026,Transferência Fornecedor,D,500.00,TRF001,REF002
```

**Campos:**
- `data`: Data da transação (formato DD/MM/YYYY)
- `descricao`: Descrição da transação
- `tipo`: D (Débito) ou C (Crédito)
- `valor`: Valor da transação (usar ponto como separador decimal)
- `numero_documento`: Número do documento (opcional)
- `referencia_banco`: Referência do banco (opcional)

## Segurança e Auditoria

- Todos os registros mantêm rastreamento de usuário e data
- Campos de auditoria são somente leitura
- Suporte a soft delete através do campo `status`
- Proteção contra exclusão de registros relacionados

## Dependências

O módulo utiliza as seguintes dependências do Django:
- `django.db.models`: ORM do Django
- `django.contrib.auth`: Sistema de autenticação
- `django.utils.timezone`: Manipulação de datas
- `decimal.Decimal`: Precisão em cálculos monetários

## Próximos Passos de Desenvolvimento

1. **Importação de OFX**: Adicionar suporte para arquivos OFX
2. **Reconciliação Automática**: Implementar algoritmo de matching automático
3. **Relatórios**: Criar relatórios de conciliação e divergências
4. **API REST**: Expor funcionalidades via API
5. **Notificações**: Sistema de alertas para divergências críticas
6. **Integração Bancária**: Conexão com APIs de bancos para extrato automático

## Troubleshooting

### Erro: "Competência Bancária não encontrada"
Certifique-se de que existe uma competência bancária ativa para o período do extrato.

### Erro: "Arquivo CSV inválido"
Verifique se o arquivo está no formato correto com as colunas esperadas.

### Transações não aparecem após upload
Verifique os logs para erros de processamento e certifique-se de que o arquivo foi enviado corretamente.

## Contato e Suporte

Para dúvidas ou sugestões sobre o módulo de conciliação, entre em contato com a equipe de desenvolvimento do ManagerOntec.

---

**Versão**: 1.0  
**Data de Criação**: Fevereiro de 2026  
**Desenvolvido por**: Manus AI  
**Status**: Produção
