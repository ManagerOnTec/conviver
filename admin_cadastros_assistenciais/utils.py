from .models import CadastroProfissional, ProfissionalEspecialidade
from contas.models import Perfil

# extrair dados do cadastro profissional


def get_dados_profissional(user):
    try:
        # Obter o perfil relacionado ao usuário
        perfil = Perfil.objects.get(user=user)
        # Obter o nome da pessoa associada ao perfil
        nome_profissional = perfil.pessoa.nome if perfil.pessoa else ''

        # Obter o cadastro profissional
        cadastro_profissional = CadastroProfissional.objects.get(
            profissional=user, status="A")

        # Extrair os valores necessários para especialidades e números de especialidade
        especialidades_relacionadas = ProfissionalEspecialidade.objects.filter(
            profissional=cadastro_profissional)
        especialidades = [
            rel.especialidade.especialidade for rel in especialidades_relacionadas]
        numeros_especialidade = [
            rel.numero_especialidade for rel in especialidades_relacionadas]

        # Constrói um dicionário com os dados do profissional
        dados = {
            'nome': nome_profissional,
            'profissao': cadastro_profissional.profissao.profissao if cadastro_profissional.profissao else '',
            'especialidades': especialidades,
            # Adicionado como lista de números RQE
            'numeros_especialidade': numeros_especialidade,
            'orgao_regulador': cadastro_profissional.orgao_regulador.sigla if cadastro_profissional.orgao_regulador else '',
            'numero': cadastro_profissional.numero if cadastro_profissional.numero else '',
        }
        return dados

    except (CadastroProfissional.DoesNotExist, Perfil.DoesNotExist, ProfissionalEspecialidade.DoesNotExist):
        # Se não houver CadastroProfissional, Perfil, ou ProfissionalEspecialidade para este usuário, retorna um dicionário com valores padrão
        return {
            'nome': '',
            'profissao': '',
            'especialidades': [],
            'numeros_especialidade': [],  # Vazio se não houver especialidades/RQE
            'orgao_regulador': '',
            'numero': '',
        }
