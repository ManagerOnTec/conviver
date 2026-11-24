import re
import hashlib
from django.conf import settings
from django.db import transaction
from django.test import Client
from django.contrib.auth import get_user_model
from atendimentos.models import Atendimento
from admin_exames.models import TipoExame
from prontuarios.models import Exame

User = get_user_model()


def run():
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
    with transaction.atomic():
        atend = Atendimento.objects.filter(estabelecimento__isnull=False).first()
        est = atend.estabelecimento if atend else None
        if not (est and atend):
            print('SKIP: sem estabelecimento/atendimento')
            transaction.set_rollback(True)
            return
        tipo = TipoExame.objects.filter(status='A').first()
        if not tipo:
            print('SKIP: sem TipoExame')
            transaction.set_rollback(True)
            return
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        User.objects.filter(pk=user.pk).update(is_superuser=True, is_staff=True)
        for i in range(18):
            Exame.objects.create(
                atendimento=atend, tipo_exame=tipo, solicitacao=f'teste pag {i}',
                estabelecimento=est, us_registro=user, status='A')

        def nova_sessao():
            c = Client()
            c.force_login(user)
            s = c.session
            s['estabelecimento_id'] = est.pk
            s.save()
            return c

        # Pagina 1 (sessao nova)
        c = nova_sessao()
        r = c.get(f'/prontuarios/exame_listar/{atend.pk}/')
        html = r.content.decode()
        print('--- pagina 1: status', r.status_code)
        print('painel paginacao:', 'listing-pagination-panel' in html)
        m = re.search(r'<strong>(de \d+ registros)</strong>', html)
        print('strong:', m.group(1) if m else 'AUSENTE')
        print('page-link:', len(re.findall(r'class="page-link"', html)),
              '| page=2:', 'page=2' in html)
        print('registros na pagina 1:', len(re.findall(r'teste pag', html)))

        # Pagina 2 usando o LINK gerado na pagina 1 (mesma sessao)
        href = re.search(r'href="([^"]*page=2[^"]*)"', html)
        print('href pagina 2:', href.group(1) if href else 'AUSENTE')
        if href:
            r2 = c.get(href.group(1).replace('&amp;', '&'))
            h2 = r2.content.decode()
            print('--- pagina 2 via link: status', r2.status_code,
                  '| url:', r2.request['QUERY_STRING'])
            print('registros na pagina 2:', len(re.findall(r'teste pag', h2)))
            print('md5 pag1 != pag2:', hashlib.md5(html.encode()).hexdigest()
                  != hashlib.md5(h2.encode()).hexdigest())

        # Pagina 2 direto com ?page=2
        r3 = c.get(f'/prontuarios/exame_listar/{atend.pk}/?page=2')
        h3 = r3.content.decode()
        print('--- pagina 2 direta: status', r3.status_code)
        print('registros:', len(re.findall(r'teste pag', h3)))
        m3 = re.search(r'<strong>(de \d+ registros)</strong>', h3)
        print('strong:', m3.group(1) if m3 else 'AUSENTE')

        transaction.set_rollback(True)


run()
