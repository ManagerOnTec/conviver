"""Verificação (rollback): criação inline completa."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from admin_cadastros.models import Pessoa, Estado, Cidade
    from admin_cadastros_assistenciais.models import CID
    from atendimentos.models import Atendimento
    user = User.objects.filter(is_superuser=True).first()
    at = Atendimento.objects.select_related('estabelecimento').first()
    est = at.estabelecimento
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()

    # 1. página: seletor de estados + modais + JS
    html = client.get('/atendimentos/atendimento_cadastrar/').content.decode()
    resultados = {
        'seletor_estado': 'inline-cidade-estado' in html,
        'estados_options': html.count('inline-cidade-estado') > 0 and
                           '<option value="' in html,
        'opcao_novo': '__novo__' in html,
    }
    print('1:', resultados)
    assert all(resultados.values())

    # 2. criar PACIENTE (o fluxo do modal: só nome/cpf/classificação)
    r = client.post('/atendimentos/inline/pessoa/', {
        'nome': 'QA MODAL PAC', 'cpf': '', 'classificacao': 'paciente'})
    p = Pessoa.objects.filter(nome='QA MODAL PAC').first()
    print('2 paciente criado:', p is not None and
          p.classificacao_pessoa == 'paciente', '| id:', r.json().get('id'))

    # 3. criar FAMILIAR
    r = client.post('/atendimentos/inline/pessoa/', {
        'nome': 'QA MODAL FAM', 'cpf': '', 'classificacao': 'familiar'})
    pf = Pessoa.objects.filter(nome='QA MODAL FAM').first()
    print('3 familiar criado:', pf is not None and
          pf.classificacao_pessoa == 'familiar')

    # 4. CID
    r = client.post('/atendimentos/inline/cid/', {
        'codigo': 'QM99', 'descricao': 'QA modal'})
    cid = CID.objects.filter(codigo='QM99').first()
    print('4 cid criado:', cid is not None)

    # 5. cidade COM estado existente (via estado_pk)
    estado = Estado.objects.filter(status='A').first()
    r = client.post('/atendimentos/inline/cidade/', {
        'cidade': 'QA CID SE', 'estado_pk': estado.pk})
    cidade = Cidade.objects.filter(cidade='QA CID SE').first()
    print('5 cidade com estado_pk:', cidade is not None and
          cidade.estado_id == estado.pk)

    # 6. cidade com estado NOVO (uf + nome)
    r = client.post('/atendimentos/inline/cidade/', {
        'cidade': 'QA CID ZN', 'uf': 'ZN', 'estado': 'ZN Estado'})
    cidade2 = Cidade.objects.filter(cidade='QA CID ZN').first()
    estado2 = Estado.objects.filter(uf='ZN').first()
    print('6 cidade+estado novo:', cidade2 is not None and estado2 is not None
          and cidade2.estado_id == estado2.pk)

    raise RuntimeError('rollback')
