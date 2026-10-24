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

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.contrib.auth import get_user_model
from admin_cadastros.models import Estabelecimento, Empresa, Pessoa
from admin_cadastros_financeiros.models import Conta, Banco, Agencia
from admin_pagamentos.models_cartao import (
    CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao,
)

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

# 6. Criar Cartão de Pagamento
print("\n6. Criando cartao de pagamento...")
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

# 7. Criar Transações do Cartão
print("\n7. Criando transacoes do cartao...")
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

# 8. Criar Fatura do Cartão
print("\n8. Criando fatura do cartao...")
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

# 9. Criar Pagamento de Fatura
print("\n9. Criando pagamento de fatura...")
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

print("\n" + "=" * 80)
print("DADOS DE TESTE POPULADOS COM SUCESSO!")
print("=" * 80)
print("\nResumo:")
print(f"  - Usuario: admin / admin123")
print(f"  - Empresa: {empresa.nome_fantasia}")
print(f"  - Estabelecimento: {estabelecimento.nome_fantasia}")
print(f"  - Conta Bancaria: {conta.numero_conta}")
print(f"  - Cartao: {cartao.descricao}")
print(f"  - Transacoes: {TransacaoCartao.objects.filter(cartao=cartao).count()}")
print(f"  - Fatura: Criada para {mes_ref.strftime('%m/%Y')}")
print("\nAgora você pode fazer login e testar os modulos!")
print("=" * 80)
