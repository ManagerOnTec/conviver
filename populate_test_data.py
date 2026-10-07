#!/usr/bin/env python
"""
Script para popular o banco de dados com dados de teste para validação dos módulos.
Execução: python manage.py shell < populate_test_data.py
"""

import os
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db.models import Sum
from django.core.files.base import ContentFile

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.contrib.auth import get_user_model
from admin_cadastros.models import Estabelecimento, Empresa, Pessoa
from admin_cadastros_financeiros.models import Conta, Banco, Agencia
from apptesouraria.models import Tesouraria, Caixa, SaldoCaixa, MovimentacaoCaixa
from appcartao.models import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao
from appconciliacao.models import ExtratoBancario

User = get_user_model()

print("=" * 80)
print("POPULANDO BANCO DE DADOS COM DADOS DE TESTE")
print("=" * 80)

# 1. Criar usuário de teste
print("\n1. Criando usuário de teste...")
try:
    user = User.objects.get(username='admin')
    print(f"   OK: Usuário 'admin' já existe")
except User.DoesNotExist:
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    print(f"   OK: Usuário 'admin' criado com sucesso")

# 2. Criar Empresa
print("\n2. Criando empresa...")
try:
    empresa = Empresa.objects.first()
    if not empresa:
        empresa = Empresa.objects.create(
            razao_social='Empresa Teste LTDA',
            nome_fantasia='Empresa Teste',
            cnpj='12.345.678/0001-90',
            us_registro=user
        )
        print(f"   OK: Empresa '{empresa.nome_fantasia}' criada")
    else:
        print(f"   OK: Usando empresa existente: {empresa.nome_fantasia}")
except Exception as e:
    print(f"   ERRO: {e}")

# 3. Criar Estabelecimento
print("\n3. Criando estabelecimento...")
try:
    estabelecimento = Estabelecimento.objects.first()
    if not estabelecimento:
        estabelecimento = Estabelecimento.objects.create(
            empresa=empresa,
            nome_fantasia='Filial Teste',
            cnpj='12.345.678/0001-91',
            endereco='Rua Teste, 123',
            cidade='Sao Paulo',
            estado='SP',
            cep='01234-567',
            us_registro=user
        )
        print(f"   OK: Estabelecimento '{estabelecimento.nome_fantasia}' criado")
    else:
        print(f"   OK: Usando estabelecimento existente: {estabelecimento.nome_fantasia}")
except Exception as e:
    print(f"   ERRO: {e}")

# 4. Criar Banco e Agência
print("\n4. Criando banco e agência...")
try:
    banco, created = Banco.objects.get_or_create(
        nome='Banco Teste',
        defaults={'codigo': '001', 'us_registro': user}
    )
    if created:
        print(f"   OK: Banco '{banco.nome}' criado")
    else:
        print(f"   OK: Banco '{banco.nome}' já existe")
    
    agencia, created = Agencia.objects.get_or_create(
        banco=banco,
        numero='0001',
        defaults={'us_registro': user}
    )
    if created:
        print(f"   OK: Agência '{agencia.numero}' criada")
    else:
        print(f"   OK: Agência '{agencia.numero}' já existe")
except Exception as e:
    print(f"   ERRO: {e}")

# 5. Criar Conta Bancária
print("\n5. Criando conta bancária...")
try:
    conta = Conta.objects.filter(estabelecimento=estabelecimento).first()
    if not conta:
        conta = Conta.objects.create(
            estabelecimento=estabelecimento,
            banco=banco,
            agencia=agencia,
            numero_conta='123456',
            us_registro=user
        )
        print(f"   OK: Conta '{conta.numero_conta}' criada")
    else:
        print(f"   OK: Usando conta existente: {conta.numero_conta}")
except Exception as e:
    print(f"   ERRO: {e}")

# 6. Criar Caixa
print("\n6. Criando caixa...")
try:
    tesouraria = Tesouraria.objects.filter(estabelecimento=estabelecimento).first()
    if not tesouraria:
        tesouraria = Tesouraria.objects.create(
            estabelecimento=estabelecimento,
            descricao='Tesouraria Principal',
            numero_tesouraria='TES-001',
            us_registro=user
        )

    caixa = Caixa.objects.filter(tesouraria=tesouraria).first()
    if not caixa:
        caixa = Caixa.objects.create(
            descricao='Caixa Teste',
            tesouraria=tesouraria,
            numero_caixa='001',
            us_registro=user
        )
        print(f"   OK: Caixa '{caixa.descricao}' criada")
    else:
        print(f"   OK: Usando caixa existente: {caixa.descricao}")
except Exception as e:
    print(f"   ERRO: {e}")

# 7. Criar Saldo de Caixa
print("\n7. Criando saldo de caixa...")
try:
    hoje = date.today()
    saldo_caixa = SaldoCaixa.objects.filter(
        caixa=caixa,
        data_abertura=hoje
    ).first()
    
    if not saldo_caixa:
        saldo_caixa = SaldoCaixa.objects.create(
            caixa=caixa,
            data_abertura=hoje,
            saldo_inicial=Decimal('5000.00'),
            us_registro=user
        )
        print(f"   OK: Saldo de Caixa criado com R$ {saldo_caixa.saldo_inicial}")
    else:
        print(f"   OK: Saldo de Caixa já existe para hoje")
except Exception as e:
    print(f"   ERRO: {e}")

# 8. Criar Movimentações de Caixa
print("\n8. Criando movimentações de caixa...")
try:
    movimentacoes_count = MovimentacaoCaixa.objects.filter(saldo_caixa=saldo_caixa).count()
    if movimentacoes_count == 0:
        # Entrada
        mov1 = MovimentacaoCaixa.objects.create(
            saldo_caixa=saldo_caixa,
            tipo='ENTRADA',
            descricao='Recebimento de cliente',
            valor=Decimal('2000.00'),
            origem='BANCO',
            us_registro=user
        )
        print(f"   OK: Movimentacao ENTRADA criada: R$ {mov1.valor}")
        
        # Saída
        mov2 = MovimentacaoCaixa.objects.create(
            saldo_caixa=saldo_caixa,
            tipo='SAIDA',
            descricao='Pagamento a fornecedor',
            valor=Decimal('500.00'),
            origem='PAGAMENTO',
            us_registro=user
        )
        print(f"   OK: Movimentacao SAIDA criada: R$ {mov2.valor}")
    else:
        print(f"   OK: {movimentacoes_count} movimentacoes já existem")
except Exception as e:
    print(f"   ERRO: {e}")

# 9. Criar Cartão de Pagamento
print("\n9. Criando cartao de pagamento...")
try:
    cartao = CartaoPagamento.objects.filter(estabelecimento=estabelecimento).first()
    if not cartao:
        cartao = CartaoPagamento.objects.create(
            descricao='Cartao Corporativo',
            tipo='CREDITO',
            numero_cartao='1234',
            bandeira='Visa',
            estabelecimento=estabelecimento,
            conta_bancaria=conta,
            limite=Decimal('50000.00'),
            dia_fechamento=10,
            dia_vencimento=20,
            us_registro=user
        )
        print(f"   OK: Cartao '{cartao.descricao}' criado com limite R$ {cartao.limite}")
    else:
        print(f"   OK: Usando cartao existente: {cartao.descricao}")
except Exception as e:
    print(f"   ERRO: {e}")

# 10. Criar Transações do Cartão
print("\n10. Criando transacoes do cartao...")
try:
    transacoes_count = TransacaoCartao.objects.filter(cartao=cartao).count()
    if transacoes_count == 0:
        # Transação 1
        trans1 = TransacaoCartao.objects.create(
            cartao=cartao,
            descricao='Compra de materiais de escritorio',
            valor=Decimal('1500.00'),
            data_transacao=date.today(),
            categoria='Materiais',
            fornecedor='Fornecedor A',
            us_registro=user
        )
        print(f"   OK: Transacao 1 criada: R$ {trans1.valor}")
        
        # Transação 2
        trans2 = TransacaoCartao.objects.create(
            cartao=cartao,
            descricao='Passagens aereas',
            valor=Decimal('3200.00'),
            data_transacao=date.today() - timedelta(days=5),
            categoria='Viagem',
            fornecedor='Agencia de Viagens',
            us_registro=user
        )
        print(f"   OK: Transacao 2 criada: R$ {trans2.valor}")
        
        # Transação 3
        trans3 = TransacaoCartao.objects.create(
            cartao=cartao,
            descricao='Hospedagem',
            valor=Decimal('800.00'),
            data_transacao=date.today() - timedelta(days=3),
            categoria='Viagem',
            fornecedor='Hotel XYZ',
            us_registro=user
        )
        print(f"   OK: Transacao 3 criada: R$ {trans3.valor}")
    else:
        print(f"   OK: {transacoes_count} transacoes já existem")
except Exception as e:
    print(f"   ERRO: {e}")

# 11. Criar Fatura do Cartão
print("\n11. Criando fatura do cartao...")
try:
    mes_ref = date(date.today().year, date.today().month, 1)
    fatura = FaturaCartao.objects.filter(
        cartao=cartao,
        mes_referencia=mes_ref
    ).first()
    
    if not fatura:
        total_transacoes = TransacaoCartao.objects.filter(cartao=cartao).aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        fatura = FaturaCartao.objects.create(
            cartao=cartao,
            mes_referencia=mes_ref,
            data_fechamento=date.today(),
            data_vencimento=date.today() + timedelta(days=10),
            valor_total=total_transacoes,
            us_registro=user
        )
        print(f"   OK: Fatura criada com valor total R$ {fatura.valor_total}")
    else:
        print(f"   OK: Fatura já existe para este mes")
except Exception as e:
    print(f"   ERRO: {e}")

# 12. Criar Pagamento de Fatura
print("\n12. Criando pagamento de fatura...")
try:
    pagamentos_count = PagamentoCartao.objects.filter(fatura=fatura).count()
    if pagamentos_count == 0:
        pagamento = PagamentoCartao.objects.create(
            fatura=fatura,
            valor_pagamento=Decimal('2500.00'),
            data_pagamento=date.today(),
            forma_pagamento='Transferencia',
            us_registro=user
        )
        print(f"   OK: Pagamento criado: R$ {pagamento.valor_pagamento}")
    else:
        print(f"   OK: {pagamentos_count} pagamentos já existem")
except Exception as e:
    print(f"   ERRO: {e}")

# 13. Criar Extrato Bancário
print("\n13. Criando extrato bancario...")
try:
    extrato = ExtratoBancario.objects.filter(
        estabelecimento=estabelecimento,
        numero_conta=conta.numero_conta
    ).first()
    if not extrato:
        csv_demo = ContentFile(
            b"data,descricao,tipo,valor,numero_documento\n01/01/2026,Saldo Inicial,C,10000.00,INI001\n",
            name='extrato_teste.csv'
        )
        extrato = ExtratoBancario.objects.create(
            estabelecimento=estabelecimento,
            numero_banco=getattr(banco, 'codigo', '001'),
            numero_agencia=agencia.numero,
            numero_conta=conta.numero_conta,
            data_inicio=date.today() - timedelta(days=30),
            data_fim=date.today(),
            saldo_inicial=Decimal('10000.00'),
            saldo_final=Decimal('12500.00'),
            tipo_arquivo='CSV',
            arquivo=csv_demo,
            us_registro=user
        )
        print(f"   OK: Extrato Bancario criado")
    else:
        print(f"   OK: Extrato Bancario já existe")
except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "=" * 80)
print("DADOS DE TESTE POPULADOS COM SUCESSO!")
print("=" * 80)
print("\nResumo:")
print(f"  - Usuario: admin / admin123")
print(f"  - Empresa: {empresa.nome_fantasia}")
print(f"  - Estabelecimento: {estabelecimento.nome_fantasia}")
print(f"  - Conta Bancaria: {conta.numero_conta}")
print(f"  - Caixa: {caixa.descricao}")
print(f"  - Cartao: {cartao.descricao}")
print(f"  - Transacoes: {TransacaoCartao.objects.filter(cartao=cartao).count()}")
print(f"  - Fatura: Criada para {mes_ref.strftime('%m/%Y')}")
print("\nAgora você pode fazer login e testar os modulos!")
print("=" * 80)
