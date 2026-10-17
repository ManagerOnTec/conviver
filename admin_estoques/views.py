import tempfile

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import ImportarMedicamentosForm
from .importacao import ler_planilha, mapear_via, normalizar_texto
from .models import (
    Classe, Grupo, Produto, SubClasse, TipoProduto, UnidadeMedida, ViaAdministracao,
)

# Chave de sessão onde a pré-visualização da importação é guardada
SESSAO_IMPORTACAO = 'admin_estoques_importacao'

GRUPO_GENERICO = 'Medicamento Genérico'
GRUPO_COMERCIAL = 'Medicamento Referência/Comercial'

TIPO_PRODUTO_PADRAO = 'Medicamento'

# Unidade de medida padrão usada quando a planilha não informa a UM
# (o campo Produto.unidade_medida é obrigatório no banco).
UM_PADRAO = 'UN'


def _get_tipo_produto(criar=True):
    """Localiza (ou cria) o tipo de produto de medicamentos.

    Reaproveita tipos existentes cujo nome contenha "medicamento" para evitar
    duplicidade (ex.: "Medicamentos" já cadastrado).
    """
    tipo = TipoProduto.objects.filter(descricao__iexact=TIPO_PRODUTO_PADRAO).first()
    if tipo is None:
        tipo = TipoProduto.objects.filter(
            descricao__icontains='medicamento').first()
    if tipo is None and criar:
        tipo = TipoProduto.objects.create(descricao=TIPO_PRODUTO_PADRAO)
    return tipo


def _get_grupo(descricao, tipo_produto, criar=True, palavra_chave=None):
    """Localiza (ou cria) um grupo de medicamento.

    Tenta reaproveitar um grupo existente que contenha a palavra-chave
    (ex.: "genéric"/"comercial") antes de criar um novo, evitando duplicidade
    com grupos já cadastrados manualmente (ex.: "Medicamentos Genéricos").
    """
    grupo = Grupo.objects.filter(descricao__iexact=descricao).first()
    if grupo is None and palavra_chave:
        grupo = Grupo.objects.filter(
            descricao__icontains=palavra_chave,
            grupo_de_medicamento=True,
        ).first()
    if grupo is None and criar:
        grupo = Grupo.objects.create(
            descricao=descricao,
            tipo_produto=tipo_produto,
            grupo_de_medicamento=True,
            pode_ser_prescrito=True,
        )
    return grupo


def _get_classe(descricao, criar=True):
    descricao = (descricao or '').strip()
    if not descricao:
        return None
    classe = Classe.objects.filter(descricao__iexact=descricao).first()
    if classe is None and criar:
        classe = Classe.objects.create(descricao=descricao)
    return classe


def _get_subclasse(descricao, classe, criar=True):
    descricao = (descricao or '').strip()
    # "Único" é apenas um rótulo da planilha, não é uma subclasse real
    if not descricao or normalizar_texto(descricao) == 'UNICO':
        return None
    subclasse = SubClasse.objects.filter(
        descricao__iexact=descricao, classe=classe).first()
    if subclasse is None and criar:
        subclasse = SubClasse.objects.create(descricao=descricao, classe=classe)
    return subclasse


def _get_unidade_medida(codigo, criar=True):
    codigo = (codigo or '').strip() or UM_PADRAO
    um = UnidadeMedida.objects.filter(unidade_medida__iexact=codigo).first()
    if um is None and criar:
        um = UnidadeMedida.objects.create(
            unidade_medida=codigo.upper()[:3],
            descricao='Unidade' if codigo.upper() == UM_PADRAO else codigo.upper(),
        )
    return um


# Unidade de medida de via usada quando a planilha não informa a via
VIA_PADRAO = '--'


def _get_via_administracao(valor, criar=True):
    """Localiza a ViaAdministracao pelo código mapeado a partir do texto da planilha."""
    codigo = mapear_via(valor)
    via = ViaAdministracao.objects.filter(codigo__iexact=codigo).first()
    if via is None:
        via = ViaAdministracao.objects.filter(codigo__iexact=VIA_PADRAO).first()
    return via


def _resolver_vinculos(linhas):
    """
    Converte as linhas cruas da planilha em uma lista de itens prontos para
    revisão, sinalizando situações de dúvida:
      - um produto com o mesmo nome já existe com status ativo (atualizar?);
      - o genérico e o comercial têm o mesmo nome (produto único);
      - via de administração não informada;
      - unidade de medida não informada.
    """
    itens = []
    for linha in linhas:
        duvidas = []

        gen = linha['generico']
        coms = linha['comerciais']

        nomes_comerciais = list(coms)
        # Se o genérico tiver o mesmo nome de um comercial, tratamos como único
        mesmo_nome = any(
            normalizar_texto(gen) == normalizar_texto(c) for c in nomes_comerciais
        ) if gen else False

        if mesmo_nome:
            duvidas.append(
                'O genérico e o comercial possuem o mesmo nome: '
                'será cadastrado como um único produto.')
            nomes_comerciais = [
                c for c in nomes_comerciais
                if normalizar_texto(c) != normalizar_texto(gen)
            ]

        # Já existe produto ativo com esse nome?
        for nome in [n for n in [gen] + nomes_comerciais if n]:
            if Produto.objects.filter(descricao__iexact=nome, status='A').exists():
                duvidas.append(f'Já existe um produto ativo chamado "{nome}".')

        if not linha['via']:
            duvidas.append('Via de administração não informada (definida como "--").')
        if not linha['um']:
            duvidas.append(
                f'Unidade de medida não informada (será usada a UM padrão "{UM_PADRAO}").')

        itens.append({
            'linha': linha['linha'],
            'generico': gen,
            'comerciais': nomes_comerciais,
            'classe': linha['classe'],
            'subclasse': linha['subclasse'],
            'um': linha['um'] or UM_PADRAO,
            'via': linha['via'],
            'duvidas': duvidas,
        })
    return itens


@staff_member_required
def importar_medicamentos(request):
    """Passo 1: upload da planilha e geração da pré-visualização."""
    if request.method == 'POST':
        form = ImportarMedicamentosForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data['arquivo']
            criar = form.cleaned_data.get('criar_automatico', True)

            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=True) as tmp:
                for chunk in arquivo.chunks():
                    tmp.write(chunk)
                tmp.flush()
                try:
                    linhas, avisos = ler_planilha(tmp.name)
                except Exception as exc:  # noqa: BLE001
                    messages.error(
                        request, f'Não foi possível ler a planilha: {exc}')
                    return render(request, 'admin_estoques/importar.html', {
                        'form': form,
                        'title': 'Importar Medicamentos',
                    })

            itens = _resolver_vinculos(linhas)
            request.session[SESSAO_IMPORTACAO] = {
                'itens': itens,
                'avisos': avisos,
                'criar_automatico': criar,
                'arquivo': arquivo.name,
            }
            return redirect('admin_estoques:importar_confirmar')
    else:
        form = ImportarMedicamentosForm()

    return render(request, 'admin_estoques/importar.html', {
        'form': form,
        'title': 'Importar Medicamentos',
    })


@staff_member_required
def importar_confirmar(request):
    """Passo 2: revisão/ajuste das dúvidas e confirmação da importação."""
    dados = request.session.get(SESSAO_IMPORTACAO)
    if not dados:
        messages.warning(
            request, 'Nenhuma importação pendente. Envie a planilha novamente.')
        return redirect('admin_estoques:importar')

    itens = dados['itens']

    if request.method == 'POST':
        # Ajustes enviados pelo usuário, por linha
        for item in itens:
            prefixo = f'item_{item["linha"]}'
            item['generico'] = request.POST.get(f'{prefixo}_generico', item['generico'])
            item['classe'] = request.POST.get(f'{prefixo}_classe', item['classe'])
            item['subclasse'] = request.POST.get(f'{prefixo}_subclasse', item['subclasse'])
            item['um'] = request.POST.get(f'{prefixo}_um', item['um'])
            item['via'] = request.POST.get(f'{prefixo}_via', item['via'])

            # Ação por linha: importar / pular
            acao = request.POST.get(f'{prefixo}_acao', 'importar')
            item['acao'] = acao

        resultado = _executar_importacao(
            itens, dados.get('criar_automatico', True), request.user)

        request.session.pop(SESSAO_IMPORTACAO, None)

        messages.success(
            request,
            f'Importação concluída: {resultado["criados"]} produto(s) criado(s), '
            f'{resultado["atualizados"]} atualizado(s), '
            f'{resultado["pulados"]} pulado(s).')

        for erro in resultado['erros']:
            messages.warning(request, erro)

        return redirect('admin:admin_estoques_produto_changelist')

    return render(request, 'admin_estoques/importar_confirmar.html', {
        'itens': itens,
        'avisos': dados.get('avisos', []),
        'arquivo': dados.get('arquivo', ''),
        'title': 'Confirmar Importação de Medicamentos',
    })


def _executar_importacao(itens, criar_automatico, usuario):
    """Cria/atualiza os produtos no banco a partir dos itens revisados."""
    resultado = {'criados': 0, 'atualizados': 0, 'pulados': 0, 'erros': []}
    agora = timezone.now()

    tipo_produto = _get_tipo_produto(criar=criar_automatico)
    if tipo_produto is None:
        resultado['erros'].append(
            'Tipo de produto "Medicamento" não encontrado e a criação automática '
            'está desabilitada. Nenhum produto foi importado.')
        return resultado

    grupo_generico = _get_grupo(
        GRUPO_GENERICO, tipo_produto, criar=criar_automatico, palavra_chave='Genéric')
    grupo_comercial = _get_grupo(
        GRUPO_COMERCIAL, tipo_produto, criar=criar_automatico, palavra_chave='Comerci')

    def _criar_ou_atualizar(descricao, grupo, classe, subclasse, um, via,
                            principio_ativo=False, produto_referencia=None):
        descricao = (descricao or '').strip()
        if not descricao:
            return None, False
        if grupo is None:
            raise ValueError(
                f'Grupo necessário para o produto "{descricao}" não existe e a '
                'criação automática está desabilitada.')

        produto = Produto.objects.filter(
            descricao__iexact=descricao, status='A').first()

        criado = False
        if produto is None:
            produto = Produto(descricao=descricao)
            produto.us_registro = usuario
            produto.dt_registro = agora
            criado = True
        else:
            produto.us_atualizacao = usuario
            produto.dt_atualizacao = agora

        produto.grupo = grupo
        if classe is not None:
            produto.classe = classe
        if subclasse is not None:
            produto.subclasse = subclasse
        if um is not None:
            produto.unidade_medida = um
        if via is not None:
            produto.via = via
        produto.principio_ativo = principio_ativo
        if produto_referencia is not None:
            produto.produto_referencia = produto_referencia
        produto.save()
        return produto, criado

    for item in itens:
        if item.get('acao') == 'pular':
            resultado['pulados'] += 1
            continue

        try:
            with transaction.atomic():
                classe = _get_classe(item.get('classe'), criar=criar_automatico)
                if item.get('classe') and classe is None:
                    raise ValueError(
                        f'Classe "{item.get("classe")}" não existe e a criação '
                        'automática está desabilitada.')
                subclasse = _get_subclasse(
                    item.get('subclasse'), classe, criar=criar_automatico)
                um = _get_unidade_medida(item.get('um'), criar=criar_automatico)
                via = _get_via_administracao(item.get('via'), criar=criar_automatico)

                # 1) Produtos comerciais (referência)
                produtos_comerciais = []
                for nome_com in item.get('comerciais', []):
                    produto, criado = _criar_ou_atualizar(
                        nome_com, grupo_comercial, classe, subclasse, um,
                        via, principio_ativo=False)
                    if produto is not None:
                        produtos_comerciais.append(produto)
                        resultado['criados' if criado else 'atualizados'] += 1

                # 2) Produto genérico (princípio ativo) vinculado ao comercial
                generico = item.get('generico')
                if generico:
                    referencia = produtos_comerciais[0] if produtos_comerciais else None
                    produto, criado = _criar_ou_atualizar(
                        generico, grupo_generico, classe, subclasse, um,
                        via, principio_ativo=True,
                        produto_referencia=referencia)
                    if produto is not None:
                        resultado['criados' if criado else 'atualizados'] += 1
        except Exception as exc:  # noqa: BLE001
            resultado['erros'].append(
                f'Linha {item.get("linha")}: {exc}')
            resultado['pulados'] += 1

    return resultado
