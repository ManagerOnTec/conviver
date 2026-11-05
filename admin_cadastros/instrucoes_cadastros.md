# admin_cadastros — instruções

Cadastros base do sistema: **Pessoas** (pacientes/funcionários), **Empresas**,
**Estabelecimentos**, Estados e Cidades. Segue o **Padrão obrigatório dos
admins** do `AGENTS.md`.

## Fluxo de negócio

Não há fluxo de etapas (não há “trava de fluxo” como em faturas/pagamentos).
O que existe é o **PAPEL** de cada cadastro, que determina onde ele pode ser
usado.

```
Pessoa     ──► paciente (cliente dos convênios) / funcionário
Empresa    ──► fornecedor | convênio | estabelecimento
Estabelecimento ──► a unidade física (aponta para uma Empresa do tipo estabelecimento)
```

## Regras obrigatórias (invariantes)

### 1. `Empresa.tipo` — o papel da empresa

A **mesma tabela** `Empresa` atende três vínculos diferentes. O campo `tipo`
diz qual papel ela exerce e **cada vínculo exige o tipo certo**:

| Vínculo | Campo | Tipo exigido |
|---|---|---|
| Fornecedor (fluxo de saída) | `Fornecedor.empresa` | `fornecedor` |
| Convênio (fluxo de entrada) | `AcordoFaturamento.pagador_pj` | `convenio` |
| Estabelecimento (unidade) | `Estabelecimento.empresa` | `estabelecimento` |

**Validação em DOIS lugares** (as duas são obrigatórias):

1. **No form** — o queryset do campo já vem recortado pelo tipo, então o
   usuário só enxerga as empresas válidas. O registro **já salvo** é
   preservado no queryset (`Q(pk=atual)`), senão editar um registro antigo
   falharia com “não é uma das escolhas”.
2. **No modelo** (`clean()`) — a regra vale para qualquer entrada (admin,
   shell, importação, API):

```python
if self.empresa_id and self.empresa.tipo != 'fornecedor':
    raise ValidationError({'empresa': 'A empresa “X” é do tipo “Y”. …'})
```

A mensagem sempre diz **o que fazer**: qual tipo escolher e onde cadastrar
(“…cadastre-a em “8. Empresas””).

### 2. Novo cadastro sempre carrega o estabelecimento PADRÃO

Ver `AGENTS.md` item 9.a — `AdminEstabelecimentoPadraoMixin` fixa o campo no
`get_form` com o estabelecimento da **sessão** (ou do perfil).

### 3. Listagem com `list_editable` exige `get_changelist` próprio

Todo `ModelAdmin` com `list_editable` **precisa** de:

```python
def get_changelist(self, request, **kwargs):
    from admin_faturas.changelist_editavel import ChangeListEditavel
    return ChangeListEditavel

def get_linhas_nao_editaveis(self, request):
    return set()   # sem regra de fluxo → nenhuma linha travada
```

Sem isso o `templates/admin/change_list.html` cai no ramo que renderiza
`cl.linhas_renderizadas` e a tela quebra com
`'ChangeList' object has no attribute 'linhas_renderizadas'`.

## BARRA SUPERIOR (KPIs + filtros) — `Pessoa`

### Indicadores (5 KPIs)

| KPI | Mostra |
|---|---|
| Pessoas | total no filtro + quantas ativas |
| Feminino | feminino + masculino |
| Aniversariantes do mês | nascidos no mês corrente |
| Idade média | média em anos (só com data de nascimento) |
| Sem data de nascimento | pendências de cadastro |

### Presets (substituem período)

`Todas as idades` · `Crianças (0-11)` · `Adolescentes (12-17)` ·
`Adultos (18-59)` · `Idosos (60+)` · `Aniversariantes MM/AAAA`

### Atalhos e selects — COMBINÁVEIS

- **Atalhos** (`get_top_extra_filters`): tipo (todos/paciente/funcionário) e
  sexo (todos/feminino/masculino).
- **Selects** (`get_top_dropdown_subfilters`): **Mês de nascimento**,
  **Faixa de idade**, **Tipo**, **Sexo** — cada um mostra o valor atual e
  troca mantendo os demais.
- **Limpar filtros do topo** (`is_clear`): zera **só** os parâmetros do topo
  (`tipo_pessoa`, `mes_nascimento`, `idade_faixa`, `sexo_filtro`, `status`,
  `dt_nascimento__*`, `periodo`) e **preserva busca e filtros laterais**.

> O cruzamento (ex.: pacientes femininas nascidas em agosto com 0-11 anos)
> funciona porque os quatro recortes são aplicados **no mesmo
> `get_queryset`** — e todos usam `_url_com()`, que preserva a query string.

### Como declarar parâmetros do topo

O ChangeList **exige** um `SimpleListFilter` real para cada parâmetro;
lista vazia (`('tipo_pessoa', [])`) **não basta** — o Django tenta resolver
o nome como campo e levanta `FieldDoesNotExist` (`?e=1`).

Use `ParametroTopoFilter.para('<parametro>')`: um filtro “de passagem” que
declara o parâmetro como conhecido mas **não recorta** (o recorte fica no
`get_queryset`, que consegue combinar).

> O Django instancia filtros com `(request, params, model, model_admin)` —
> por isso o parâmetro vai na **classe** (fábrica), não no `__init__`.

### Faixa de idade portátil

**Não use** `EXTRACT(YEAR FROM age(...))`: `age()` não existe no SQLite.
Calcule as datas-limite em Python e compare:

```python
mais_novo  = date(hoje.year - minimo, hoje.month, hoje.day)
mais_velho = date(hoje.year - maximo - 1, hoje.month, hoje.day)
queryset.filter(dt_nascimento__lte=mais_novo, dt_nascimento__gt=mais_velho)
```

### `sexo` é minúsculo

As choices são `('f', 'Feminino')` / `('m', 'Masculino')`. Filtre sempre por
**`'f'`/`'m'`** — `'F'`/`'M'` retorna zero e não dá erro.

## BARRA SUPERIOR — `Empresa`

- **Presets**: `Todos os tipos` + um por tipo (Fornecedor, Convênio,
  Estabelecimento) — o recorte mais importante desta tela é o **papel**.
- **Atalhos**: Todos / Ativas / Inativas.
- **Selects**: **UF** e **Cidade** (cada um preserva os demais).
- **KPIs**: Empresas (ativas), Fornecedores, Convênios, Estabelecimentos,
  Sem CNPJ.
- `list_editable = ['status', 'tipo']`.

> UF/Cidade do topo usam `estado__id__exact`/`cidade__id__exact`, que **não
> são** lookups válidos para o Django declarar como filtro
> (`NotRelationField`). São lidos **direto da URL** no `get_queryset` e não
> entram no `get_list_filter`. O filtro lateral (`estado`, `cidade`) segue
> funcionando normalmente.

## BARRA SUPERIOR — `Produto` (`admin_estoques`)

Hierarquia: **Tipo de Produto → Grupo → Produto** (Classe e Via são
classificações paralelas).

- **Presets**: `Todos os tipos` + um por **Tipo de Produto**.
- **Atalhos**: Todos / Medicamentos / Materiais / Prescritíveis /
  Princípio ativo.
- **Selects**: **Grupo** (mostra também o tipo), **Classe**, **Via** —
  combináveis; **Limpar filtros do topo** preserva busca e laterais.
- **KPIs**: Produtos (ativos), Medicamentos, Prescritíveis, Princípios
  ativos, Grupos no filtro.

### “Medicamento” não é campo — vem do GRUPO

Não existe `Produto.medicamento`. O recorte é sempre pelo grupo:

```python
queryset.filter(grupo__grupo_de_medicamento=True)   # medicamentos
queryset.filter(grupo__grupo_de_medicamento=False)  # materiais
```

### Prescritível = grupo OU exceção do produto

`Grupo.pode_ser_prescrito` libera o grupo inteiro; `Produto.pode_ser_prescrito`
é a **exceção** do item. O filtro considera os dois:

```python
queryset.filter(Q(grupo__pode_ser_prescrito=True)
                | Q(pode_ser_prescrito=True))
```

Combinar os recortes exige `distinct()` (o `|` sobre M2M/FK pode duplicar).

## BARRA SUPERIOR — `Grupo`

- **Presets**: por Tipo de Produto · **Atalhos**: Todos / Medicamentos /
  Prescritíveis · **Select**: Tipo de produto + limpar.
- **KPIs**: Grupos (ativos), Medicamentos, Prescritíveis, **Sem produtos**
  (grupos sem nenhum produto vinculado — cadastro esquecido).
- `list_display` inclui **`qtd_produtos`** com `annotate(Count('produto'))`:
  uma consulta para a página inteira, não uma por linha (evita N+1).

## `change_list_template` próprio

`ProdutoAdmin` usa `admin_estoques/produto/change_list.html` (botão
“Importar Medicamentos (XLSX)”). Ele **estende** `admin/change_list.html`,
então a barra de KPIs/filtros continua aparecendo normalmente.

## Menu e telas

1. Classificação Fornecedores · 2. Pessoas - campos obrigatórios ·
3. Empresa - campos obrigatórios · **7. Pessoas** · **8. Empresas** ·
**9. Estabelecimentos**

Estoques (`admin_estoques`): 1. Tipos de Produtos · 2. Grupos · 3. Classes ·
4. Sub Classes · 5. Categorias · 6. Unidades de Medidas · 7. Vias de
Administração · **8. Produtos**

## Não fazer

- Não deixar o select de empresa livre: **sempre** recortar por `tipo`.
- Não remover a validação do modelo achando que o form basta (importação e
  shell não passam pelo form).
- Não usar `EXTRACT(age())` (quebra no SQLite).
- Não usar `'F'`/`'M'` no filtro de sexo.
- Não usar lista vazia para declarar parâmetro do topo.
- Não usar `get_list_filter` para UF/Cidade do topo (`NotRelationField`).
- Não criar `_btn(..., param=None, ...)` esperando `**{None: ...}` —
  `**` exige chaves `str` (“keywords must be strings”). O botão “Todos”
  deve montar o dicionário de mudanças **sem** a chave.

## Como testar

Em `with transaction.atomic():` + `raise RuntimeError('rollback')`:

1. `Fornecedor(empresa=<tipo convenio>).full_clean()` → **recusa**;
2. `Fornecedor(empresa=<tipo fornecedor>)` → **aceita**;
3. mesmo par para `Estabelecimento` e `AcordoFaturamento.pagador_pj`;
4. tela `/admin/admin_cadastros/empresa/` com `?tipo=fornecedor` filtra;
5. tela `/admin/admin_cadastros/pessoa/` com os 4 parâmetros combinados;
6. `/admin/admin_estoques/produto/` com `?tipo_produto=N&medicamento=sim`;
7. `/admin/admin_estoques/grupo/` — `qtd_produtos` não deve gerar N+1;
8. `python manage.py check` antes de concluir.
