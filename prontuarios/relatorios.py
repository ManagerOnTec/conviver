import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from io import BytesIO

from admin_relatorios.rel_header import genHeaderRel
from admin_relatorios.rel_dados_pessoais import genDadosPessoaisRel
from admin_relatorios.rel_paragrafos import genParagrafosRel
from admin_relatorios.rel_assinatura import genAssinaturaRel
from admin_relatorios.rel_footer import genFooterRel
from admin_relatorios.rel_usuario import genDadosUsuarioRel
from admin_relatorios.rel_dados_obj import genDadosObjRel

from managerontec import settings
from atendimentos.models import Atendimento
from contas.models import Perfil

from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Frame, PageTemplate, Image
from admin_relatorios.utils import assinar_pdf
from admin_cadastros.utils import extrair_iniciais
from admin_cadastros_assistenciais.utils import get_dados_profissional
import html
import re
from admin_relatorios.models import GerenciadorRelatorioGeral, GerenciadorRelatorioPersonalizado

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from django.utils import timezone

from prontuarios.models import ProdutoPrescricao, Adep
from django.db.models import Q


INLINE_REPORT_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
REPORT_IMAGE_FIELDS = {
    'evolucao': 'anexo_evolucao',
    'atas': 'anexo',
    'oficios': 'anexo',
    'orcamentos': 'anexo',
}


def _is_supported_report_image(file_name):
    if not file_name:
        return False

    return os.path.splitext(str(file_name).lower())[1] in INLINE_REPORT_IMAGE_EXTENSIONS


def _resolve_report_image_path(obj, nome_modelo):
    field_name = REPORT_IMAGE_FIELDS.get(nome_modelo)
    if not field_name:
        return None

    file_field = getattr(obj, field_name, None)
    if not file_field or not getattr(file_field, 'name', None):
        return None

    if not _is_supported_report_image(file_field.name):
        return None

    try:
        return file_field.path
    except (AttributeError, NotImplementedError, OSError, ValueError):
        return None


def gerar_pdf_prontuario(obj, user, assinar=False, assinatura_texto=None):
    # buffer e nao pdf
    buffer = BytesIO()

    # gerar o pdf só que em buffer
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    #########################################
    # Dados do objeto
    nome_modelo = obj.__class__.__name__.lower()
    vardin = obj
    vardinpk = str(obj.pk)
    usuario_registro = obj.us_registro
    estabelecimento_id = vardin.estabelecimento_id
    dt_registro_local = timezone.localtime(
        vardin.dt_registro) if vardin.dt_registro else None
    dt_registro = dt_registro_local.strftime(
        '%d/%m/%Y %H:%M') if dt_registro_local else 'Data não disponível'
    # Fim dados objeto
    ########################################

    ############################################
    # propriedades do PDF
    titulo = f'{nome_modelo}'
    autor = user.perfil.pessoa.nome
    assunto = f'{titulo}_{vardin.pk}'
    p.setTitle(titulo)
    p.setAuthor(autor)
    p.setSubject(assunto)
    # fim propriedades
    ############################################

    ############################################
    # Inicializado variaveis
    iniciais = False
    logo_path = None
    header_data = None
    right_data = None
    footer_data = None
    ############################################

    ##############################################
    # parametros dos gerenciadores de relatorio
    gerenciador_personalizado = GerenciadorRelatorioPersonalizado.objects.filter(
        relatorio=nome_modelo, estabelecimento_id=estabelecimento_id, status='A').first()

    gerenciador_geral = GerenciadorRelatorioGeral.objects.filter(
        estabelecimento_id=estabelecimento_id, status='A').first()
    # fim dados gerenciadores de relatorio
    ############################################################################

    #####################################################################
    # Objeto evolucao - de acordo com o tipo de evolucao e configuração do gerenciador pode obter apenas as iniciais
    if nome_modelo == 'evolucao':
        iniciais = vardin.tipo_evolucao.iniciais_nome
        texto_parag = html.unescape(vardin.evolucao or '')
        tipo_evolucao_id = vardin.tipo_evolucao_id

        if gerenciador_personalizado and nome_modelo == 'evolucao':
            gerenciador_personalizado = GerenciadorRelatorioPersonalizado.objects.filter(
                relatorio=nome_modelo, estabelecimento_id=estabelecimento_id, tipo_evolucao_id=tipo_evolucao_id, status='A').first()
        else:
            gerenciador_geral = GerenciadorRelatorioGeral.objects.filter(
                estabelecimento_id=estabelecimento_id, status='A').first()
    #########################################################################

    ###############################
    # Dados Prescrição e Adep
    if nome_modelo == 'prescricao':

        prescricao = obj.pk

        produtos = ProdutoPrescricao.objects.filter(
            prescricao_id=prescricao)

        # Filtra os objetos Adep
        adeps_a = Adep.objects.filter(
            prescricao_id=prescricao,
            us_adep=user,
            fase_adep__in=['A'],
            assinar=True,
            pdf=False
        )

        adeps_n = Adep.objects.filter(
            prescricao_id=prescricao,
            us_adep=user,
            fase_adep__in=['N'],
            assinar=True,
            pdf=False
        )

        adeps = Adep.objects.filter(
            prescricao_id=prescricao,
            us_adep=user,
            fase_adep__in=['A', 'N'],
            assinar=True,
            pdf=False
        )

        print(f'adepsa:[adeps_a]')
        print(f'adepsn:[adeps_n]')
        print(f'adeps:[adeps]')

        texto_produtos = ""
        # Adiciona cabeçalhos das colunas
        inicio = obj.dt_inicio.strftime('%d/%m') if obj.dt_inicio else ' '
        final = timezone.localtime(obj.dt_final).strftime(
            '%d/%m/%Y %H:%M') if obj.dt_final else ' '
        texto_cabecalho = ""
        texto_produtos += texto_cabecalho
        dt_ah = None
        dt_nh = None

        if adeps.exists() and produtos.exists():

            texto_cabecalho = f"Vigência: {inicio} até: {final}\tH\tSN\tUnica\tAdministrado\tNão Admin...\n"
            texto_produtos += texto_cabecalho

            # Antes do loop dos produtos, inicialize as variáveis para coletar as datas
            datas_administrados = {}
            datas_nao_administrados = {}

            # Durante a iteração de adeps_a e adeps_n, colete as datas
            for adepa in adeps_a:
                dt_a = timezone.localtime(
                    adepa.data_hora).strftime('%d/%m %H:%M')
                if adepa.produto_prescricao_id not in datas_administrados:
                    datas_administrados[adepa.produto_prescricao_id] = []
                datas_administrados[adepa.produto_prescricao_id].append(dt_a)

            for adepn in adeps_n:
                dt_n = timezone.localtime(
                    adepn.data_hora).strftime('%d/%m %H:%M')
                if adepn.produto_prescricao_id not in datas_nao_administrados:
                    datas_nao_administrados[adepn.produto_prescricao_id] = []
                datas_nao_administrados[adepn.produto_prescricao_id].append(
                    dt_n)

            # Durante a geração do texto do produto, inclua as datas de administração e não administração
            for produto_prescricao in produtos:
                # Defina as variáveis com base no objeto produto_prescricao atual
                produto_str = produto_prescricao.produto.descricao
                um = produto_prescricao.produto.unidade_medida
                via = produto_prescricao.produto.via
                intervalo_horas_display = produto_prescricao.intervalo_horas.get_intervalo_horas_display()

                # Use o ID do produto_prescricao para buscar as datas
                produto_prescricao_id = produto_prescricao.id
                dt_ah = ', '.join(datas_administrados.get(
                    produto_prescricao_id, [' ']))
                dt_nh = ', '.join(datas_nao_administrados.get(
                    produto_prescricao_id, [' ']))

                # Gere o texto do produto incluindo todas as datas relevantes
                texto_produto = f"{produto_str}:{um}:{via}\t" \
                                f"{intervalo_horas_display}\t" \
                                f"{'SN' if produto_prescricao.se_necessario else ' '}\t" \
                                f"{'Sim' if produto_prescricao.dose_unica else ' '}\t" \
                                f"{dt_ah}\t" \
                                f"{dt_nh}\n"

                texto_produtos += texto_produto

            Adep.objects.filter(id__in=[adep.id for adep in adeps_a] +
                                [adep.id for adep in adeps_n], pdf=False).update(pdf=True)

            nome_modelo = 'adep'

            if nome_modelo == 'adep':
                gerenciador_personalizado = GerenciadorRelatorioPersonalizado.objects.filter(
                    relatorio=nome_modelo, estabelecimento_id=estabelecimento_id, status='A').first()

                usuario_registro = user

            else:
                gerenciador_geral = GerenciadorRelatorioGeral.objects.filter(
                    estabelecimento_id=estabelecimento_id, status='A').first()

        elif produtos.exists() and not adeps:
            # Adiciona o cabeçalho das colunas para produtos sem registros de ADEP
            texto_cabecalho = f"Vigência: {inicio} até: {final}\tH\tSN\tÚnica\tObs\tAdep\n"
            texto_produtos += texto_cabecalho

            for produto_prescricao in produtos:
                # Extrai as informações do produto prescrito
                produto_str = produto_prescricao.produto.descricao
                um = produto_prescricao.produto.unidade_medida
                via = produto_prescricao.produto.via
                intervalo_horas_display = produto_prescricao.intervalo_horas.get_intervalo_horas_display()
                se_necessario = 'SN' if produto_prescricao.se_necessario else ' '
                dose_unica = 'Sim' if produto_prescricao.dose_unica else ' '
                observacao = produto_prescricao.observacao if produto_prescricao.observacao else ' '

                # Monta a linha de texto para o produto seguindo o formato tabular
                linha_produto = f"{produto_str}:{um}:{via}\t{intervalo_horas_display}\t{se_necessario}\t{dose_unica}\t{observacao}\n"
                texto_produtos += linha_produto
                nome_modelo = 'prescricao'
        else:
            texto_produtos += "Sem dados de produtos\t"

        # Substituir texto_prescricao com texto_produtos no local apropriado
        texto_parag = texto_produtos

    # Fim dados Prescrição e Adep
    #####################################################

    # Inicio relatório Diagnostico ###############################################
    if nome_modelo == 'diagnostico':
        # Assumindo que diagnostico é um ManyToManyField e você deseja todos os diagnósticos
        diagnosticos = obj.diagnostico.all()

        # Inicializa a string para armazenar os nomes dos diagnósticos
        diagnostico_nomes = ""

        # Itera sobre cada objeto CID e adiciona o nome à string, seguido de uma quebra de linha
        for diagnostico in diagnosticos:
            diagnostico_nomes += f"{str(diagnostico)}\n"

        # Pega a observação do objeto e converte para string
        observacao = str(obj.observacoes) if obj.observacoes else ' '

        # Concatena os nomes dos diagnósticos com a observação
        texto_parag = f"{diagnostico_nomes}\n {observacao}"

    # Fim relatório diagnóstico #####################################################

    # Início do relatório Sinais Vitais ###############################################
    if nome_modelo == 'sinaisvitais':
        texto_sinal = (
            f"Temperatura: {obj.temperatura or ''} °C,\t"
            f"Pressão Arterial: {obj.pressao_arterial or ''},\t"
            f"Frequência Cardíaca: {obj.frequencia_cardiaca or ''} bpm,\t"
            f"Frequência Respiratória: {obj.frequencia_respiratoria or ''} rpm,\t"
            f"Saturação de Oxigênio: {obj.saturacao_oxigenio or ''}%,\t"
            f"Controle de Glicemia: {obj.controle_glicemia or ''} mg/dL,\t"
            f"Observações: {obj.observacoes or ''}\n"
        )
        texto_parag = texto_sinal

    # Fim relatório sinais vitais #####################################################

    # INICIO SAE #######################################################################
    if nome_modelo == 'sae':
        # Inicializa a string com informações básicas do SAE
        texto_sae = ""

        # Formatando aspecto, aspecto_analisado, e diagnostico_enfermagem
        texto_sae += (
            f"Aspecto: {obj.aspecto},\t"
            f"Aspecto Analisado: {obj.aspecto_analisado},\t"
            f"Diagnóstico de Enfermagem: {obj.diagnostico_enfermagem},\t"
        )

        # Evidências/Características Definidoras
        evidencias = ", ".join(
            [evidencia.descricao for evidencia in obj.evidencia.all()])
        texto_sae += f"Evidências/Características Definidoras: {evidencias},\t"

        # Fatores Relacionados
        fatores_relacionados = ", ".join(
            [fator.descricao for fator in obj.fator_relacionado.all()])
        texto_sae += f"Fatores Relacionados: {fatores_relacionados},\t"

        # Intervenções
        intervencoes = ", ".join(
            [intervencao.descricao for intervencao in obj.intervencao.all()])
        texto_sae += f"Intervenções: {intervencoes},\t"

        # Anotações de Enfermagem
        texto_sae += f"Anotações de Enfermagem: {obj.anotacao or 'N/A'}\n"

        # Essa string pode ser usada diretamente pelo seu método de geração de relatório
        texto_parag = texto_sae

    # FIM SAE #######################################################################

    # Início do relatório Plano de Cuidados ###############################################
    if nome_modelo == 'planocuidados':
        texto_plano_cuidados = (
            f"Turnos: {obj.turnos.turnos or ''},\t"
            f"Eliminações Vesicais: {'Sim' if obj.eliminacoes_vesicais else 'Não'},\t"
            f"Eliminações Intestinais: {'Sim' if obj.eliminacoes_intestinais else 'Não'},\t"
            f"Alimentação: {'Sim' if obj.alimentacao else 'Não'},\t"
            f"Hidratação: {'Sim' if obj.hidratacao else 'Não'},\t"
            f"Higiene Conforto: {'Sim' if obj.higiene_conforto else 'Não'},\t"
            f"Higiene Bucal: {'Sim' if obj.higiene_bucal else 'Não'},\t"
            f"Atividades de Lazer e Recreação: {'Sim' if obj.atividades_lazer else 'Não'},\t"
            f"Terapia Ocupacional: {'Sim' if obj.terapia_ocupacional else 'Não'},\t"
            f"Humor: {obj.humor.humor or ''},\t"
            f"Observações: {obj.observacoes or 'Nenhuma observação'},\n"

        )
        texto_parag = texto_plano_cuidados

    # Fim relatório Plano de Cuidados #####################################################

    # Início do relatório Perdas e Ganhos ###############################################
    if nome_modelo == 'perdasganhos':

        texto_perdas_ganhos = (
            f"Peso: {obj.peso or ''} kg,\t"
            f"Altura: {obj.altura or ''} cm,\t"
            f"Observações: {obj.observacoes or 'Nenhuma observação'},\n"
        )
        texto_parag = texto_perdas_ganhos

    # Fim relatório Perdas e Ganhos #####################################################

    if nome_modelo == 'atas':
        texto_parag = obj.ata or ''
        atendimento = None
        pessoa = None

    if nome_modelo == 'orcamentos':
        texto_parag = obj.orcamento or ''
        atendimento = None
        pessoa = None

    if nome_modelo == 'oficios':
        texto_parag = obj.oficio or ''
        atendimento = None
        pessoa = None

    else:
        ###########################################################################
        # Obter dados da pessoa / cliente / paciente do objeto
        # Verificar se atendimento existe antes de acessar pessoa
        atendimento = vardin.atendimento if vardin and vardin.atendimento else None
        pessoa = atendimento.pessoa if atendimento and atendimento.pessoa else None

    # pessoa = vardin.atendimento.pessoa if vardin.atendimento.pessoa else None
    # Se o objeto Pessoa estiver presente, recuperamos e concatenamos os dados
    if pessoa:
        atendimento = vardin.atendimento_id if vardin.atendimento else " _________ "
        dt_nascimento = pessoa.dt_nascimento.strftime(
            '%d/%m/%Y') if pessoa.dt_nascimento else " __ /__ /____ "

        if iniciais:
            nome = extrair_iniciais(pessoa.nome)
            cpf = 'Divulgação não autorizada!'
        else:
            nome = pessoa.nome if pessoa.nome else " ___________________________________ "
            cpf = pessoa.cpf if pessoa.cpf else " ___.___.___-__ "
            # Concatenando os dados em uma string
        informacoes_concatenadas = f"Atendimento:{atendimento}.     Paciente:{nome}.<br/>DN:{dt_nascimento}.     CPF:{cpf}."
    else:
        informacoes_concatenadas = " "
    # Nome da pessoa (com fallback para uma mensagem padrão)
    nome_pessoa = informacoes_concatenadas
    # Fim dados da pessoa / cliente / paciente
    ########################################################################

    ####################################################
    # Preparar a string com os dados do profissional
    dados_profissional = get_dados_profissional(usuario_registro)
    if dados_profissional:
        # Combina cada especialidade com seu número RQE correspondente
        especialidades_com_numeros = [
            f"{esp}: {num}" for esp, num in zip(dados_profissional['especialidades'], dados_profissional['numeros_especialidade'])
        ]

        dados_profissionais_str = (
            f"{dados_profissional['nome']} "
            f"{dados_profissional['profissao']} "
            f"{dados_profissional['orgao_regulador']} "
            f"{dados_profissional['numero']} "
            f"{', '.join(especialidades_com_numeros)}"
        )
    else:
        dados_profissionais_str = " "

    # Concatenar as informações de registro
    dados = f"{dados_profissionais_str} {dt_registro}"
    # Fim dados do profissional do registro
    ##########################################################################

    ########################################################################
    # Definindo as alturas para cada seção
    heightList = [
        height * 8 / 100,  # Cabeçalho
        height * 8 / 100,  # Dados Atendimento
        height * 8 / 100,  # Dados Usuario
        height * 3 / 100,  # Dados Objeto
        height * 59 / 100,  # Dados Parágrafos
        height * 7 / 100,  # Assinatura
        height * 7 / 100,  # Rodapé
    ]
    # Fim das alturas da pagina

    ####################################
    # atribuindo os valores do gerenciador ou do modelo para var dos dados principais

    if gerenciador_personalizado:
        # header objetos
        logo_path = gerenciador_personalizado.logo_header.path if gerenciador_personalizado.logo_header else None
        header_data = gerenciador_personalizado.dados_header
        right_data = gerenciador_personalizado.dados_right_header
        # footer objeto
        footer_data = gerenciador_personalizado.dados_footer

    elif gerenciador_geral:
        # header objeto
        logo_path = gerenciador_geral.logo_header.path if gerenciador_geral.logo_header else None
        header_data = gerenciador_geral.dados_header
        right_data = gerenciador_geral.dados_right_header
        # footer objeto
        footer_data = gerenciador_geral.dados_footer

    if header_data is not None:
        header_data = str(header_data)

    if right_data is not None:
        right_data = str(right_data)

    if footer_data is not None:
        footer_data = str(footer_data)
    # fim dados das variaveis dos gerenciadores para passar aos metodos construtores da tabela
    ################################################################

    left_margin = 12 * mm
    right_margin = 12 * mm
    top_margin = 10 * mm
    bottom_margin = 18 * mm
    footer_draw_y = 6 * mm
    footer_gap = 3 * mm
    signature_bottom = 62
    signature_height = 50
    page_width, page_height = A4
    content_width = page_width - left_margin - right_margin
    reserve_signature_space = bool(assinar or getattr(vardin, 'assinar', False))
    report_image_path = _resolve_report_image_path(vardin, nome_modelo)

    body_flowable = genParagrafosRel(texto_parag, content_width, 0, None, tipo=nome_modelo)
    story = []
    if isinstance(body_flowable, list):
        story.extend(body_flowable)
    else:
        story.append(body_flowable)

    canvas_obj = canvas.Canvas(buffer, pagesize=A4)

    def build_fixed_tables():
        return [
            genHeaderRel(logo_path, header_data, right_data, content_width, 22 * mm),
            genDadosPessoaisRel(nome_pessoa, content_width, 10 * mm),
            genDadosUsuarioRel(dados, content_width, 10 * mm),
            genDadosObjRel(vardinpk, content_width, 8 * mm),
        ]

    def draw_fixed_sections():
        page_top = page_height - top_margin - 4 * mm
        y = page_top
        for table in build_fixed_tables():
            _, table_h = table.wrap(content_width, page_height)
            table.drawOn(canvas_obj, left_margin, y - table_h)
            y -= table_h + 2 * mm

        footer_top = 0
        if footer_data:
            footer_table = genFooterRel(footer_data, content_width, 10 * mm)
            _, footer_h = footer_table.wrap(content_width, page_height)
            footer_table.drawOn(canvas_obj, left_margin, footer_draw_y)
            footer_top = footer_draw_y + footer_h

        return y, footer_top

    def get_body_bottom(footer_top):
        reserved_bottom = max(bottom_margin, footer_top + footer_gap)
        if reserve_signature_space:
            reserved_bottom = max(reserved_bottom, signature_bottom + signature_height + footer_gap)
        return reserved_bottom

    current_y, footer_top = draw_fixed_sections()
    body_bottom = get_body_bottom(footer_top)
    page_start_y = current_y

    pending = list(story)
    while pending:
        flowable = pending.pop(0)
        available_height = current_y - body_bottom

        if available_height <= 0:
            canvas_obj.showPage()
            current_y, footer_top = draw_fixed_sections()
            body_bottom = get_body_bottom(footer_top)
            page_start_y = current_y
            available_height = current_y - body_bottom

        _, flowable_h = flowable.wrap(content_width, available_height)

        if 0 < flowable_h <= available_height:
            flowable.drawOn(canvas_obj, left_margin, current_y - flowable_h)
            current_y -= flowable_h
            continue

        pieces = flowable.split(content_width, available_height) if hasattr(flowable, 'split') else []
        if pieces:
            first_piece = pieces[0]
            _, first_piece_h = first_piece.wrap(content_width, available_height)

            if first_piece_h > 0:
                first_piece.drawOn(canvas_obj, left_margin, current_y - first_piece_h)
                current_y -= first_piece_h

            pending = pieces[1:] + pending
            continue

        if current_y < page_start_y:
            canvas_obj.showPage()
            current_y, footer_top = draw_fixed_sections()
            body_bottom = get_body_bottom(footer_top)
            page_start_y = current_y
            pending.insert(0, flowable)
            continue

        if flowable_h > 0:
            flowable.drawOn(canvas_obj, left_margin, current_y - flowable_h)
            current_y = body_bottom

    if report_image_path:
        canvas_obj.showPage()
        image_top_y, footer_top = draw_fixed_sections()
        image_bottom_y = get_body_bottom(footer_top)
        available_height = max(image_top_y - image_bottom_y, 1)

        try:
            anexo = Image(report_image_path)
            max_width = min(content_width * 0.55, 90 * mm)
            max_height = min(available_height * 0.70, 110 * mm)
            escala = min(
                max_width / anexo.drawWidth,
                max_height / anexo.drawHeight,
                1,
            )

            anexo.drawWidth *= escala
            anexo.drawHeight *= escala

            image_x = left_margin + ((content_width - anexo.drawWidth) / 2)
            image_y = image_bottom_y + ((available_height - anexo.drawHeight) / 2)
            anexo.drawOn(canvas_obj, image_x, image_y)
        except Exception:
            pass

    canvas_obj.save()
    buffer.seek(0)
    return buffer
