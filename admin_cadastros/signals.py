from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import ConfigPessoa, Pessoa, ConfigEmpresa, Empresa


# este serve de exemplo para atualizar um model com informação do outro
# @receiver(pre_save, sender=Pessoa)
# def pre_save_pessoa(sender, instance, **kwargs):
#    # assume que há apenas um objeto ConfigPessoa
#    config = ConfigPessoa.objects.first()
#    if config:
#        # verifica se houve mudança nas configurações de obrigatoriedade do campo data_nascimento
#        if config.data_nascimento != instance._meta.get_field('data_nascimento').null:
#            instance.data_nascimento = None if config.data_nascimento else instance.data_nascimento
#        # verifica se houve mudança nas configurações de obrigatoriedade do campo cpf
#        if config.cpf != instance._meta.get_field('cpf').null:
#            instance.cpf = None if config.cpf else instance.cpf


# este serve para atualizar obrigacoes de null e blank nos models de acordo com o configmodel

# inativo

# @receiver(post_save, sender=ConfigPessoa)
# def update_pessoa_fields(sender, **kwargs):
#    pessoa_fields = {'dt_nascimento': 'dt_nascimento_config', 'cpf': 'cpf_config',
#                     'rg': 'rg_config', 'whats': 'whats_config', 'telefone': 'telefone_config',
#                     'email': 'email_config', 'mae': 'mae_config', 'pai': 'pai_config',
#                     'cep': 'cep_config', 'rua': 'rua_config', 'numero': 'numero_config',
#                     'bairro': 'bairro_config', 'estado': 'estado_config', 'cidade': 'cidade_config'
#                     }
#    for field, config_func in pessoa_fields.items():
#        config_value = getattr(ConfigPessoa, config_func)()
#        Pessoa._meta.get_field(field).null = config_value
#        Pessoa._meta.get_field(field).blank = config_value


# @receiver(post_save, sender=ConfigEmpresa)
# def update_empresa_fields(sender, **kwargs):
#    empresa_fields = {'nome_responsavel': 'nome_responsavel_config', 'nome_contato': 'nome_contato_config', 'whats': 'whats_config', 'telefone': 'telefone_config',
#                      'email': 'email_config', 'rua': 'rua_config', 'numero': 'numero_config', 'bairro': 'bairro_config', 'cep': 'cep_config', 'estado': 'estado_config', 'cidade': 'cidade_config'}
#    for field, config_func in empresa_fields.items():
#        config_value = getattr(ConfigEmpresa, config_func)()
#        Empresa._meta.get_field(field).null = config_value
#        Empresa._meta.get_field(field).blank = config_value
