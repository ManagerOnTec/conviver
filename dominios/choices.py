# CHOICES ###################################################
periodos_choices = (
    (0, 'À Vista'),
    (7, 'Semanal'),
    (15, 'Quinzenal'),
    (30, 'Mensal'),
)

periodos_faturas_choices = (
    (31, '01 a 31'),
    (1, '02 a 01'),
    (2, '03 a 02'),
    (3, '04 a 03'),
    (4, '05 a 04'),
    (5, '06 a 05'),
    (6, '07 a 06'),
    (7, '08 a 07'),
    (8, '09 a 08'),
    (9, '10 a 09'),
    (10, '11 a 10'),
    (11, '12 a 11'),
    (12, '13 a 12'),
    (13, '14 a 13'),
    (14, '15 a 14'),
    (15, '16 a 15'),
    (16, '17 a 16'),
    (17, '18 a 17'),
    (18, '19 a 18'),
    (19, '20 a 19'),
    (20, '21 a 20'),
    (21, '22 a 21'),
    (22, '23 a 22'),
    (23, '24 a 23'),
    (24, '25 a 24'),
    (25, '26 a 25'),
    (26, '27 a 26'),
    (27, '28 a 27'),
    (28, '29 a 28'),
    (29, '30 a 29'),
    (30, '31 a 30'),
)


dias_choices = tuple((i, str(i)) for i in range(1, 32))


obrigatorios_choices = (
    (True, 'Opcional'),
    (False, 'Obrigatório'),
)

status_choices = (
    ('A', 'Ativo'),
    ('I', 'Inativo'),
)


tipo_atas_choices = (
    ('ADMINISTRATIVA', 'Administrativa'),
    ('REUNIAO', 'Reunião'),
    ('COMISSOES', 'Comissões'),
    ('TREINAMENTO', 'Treinamento'),
    ('OUTRAS', 'Outras'),
)

forma_pagamento_choices = (
    ('B', 'Boleto'),
    ('C', 'Cartão Crédito'),
    ('D', 'Cartão Débito'),
    ('P', 'Pix'),
    ('T', 'Transferência'),
    ('I', 'Dinheiro'),
    ('H', 'Cheque'),
    ('O', 'Outros'),
)


sn_choices = (
    ('S', 'Sim'),
    ('N', 'Não'),
)

pessoa_choices = (
    ('F', 'Funcionario'),
    ('L', 'Cliente'),
    ('C', 'Candidato'),
)


estabelecimento_choices = (
    ('M', 'Matriz'),
    ('F', 'Filial'),
    ('O', 'Outras'),
)


pessoa_atributo_choices = (
    ('pais', 'pais'),
    ('dt_nascimento', 'dt_nascimento'),
    ('alergias', 'alergias'),
    ('cpf', 'cpf'),
    ('rg', 'rg'),
    ('genero', 'genero'),
    ('whats', 'whats'),
    ('estado_civil', 'estado_civil'),
    ('telefone', 'telefone'),
    ('email', 'email'),
    ('responsavel', 'responsavel'),
    ('mae', 'mae'),
    ('pai', 'pai'),
    ('cor_raca', 'cor_raca'),
    ('religiao', 'religiao'),
    ('cep', 'cep'),
    ('rua', 'rua'),
    ('numero', 'numero'),
    ('bairro', 'bairro'),
    ('complemento', 'complemento'),
    ('estado', 'estado'),
    ('cidade', 'cidade'),
    ('naturalidade', 'naturalidade'),
)

empresa_atributo_choices = (
    ('nome_responsavel', 'nome_responsavel'),
    ('empresa', 'empresa'),
    ('cnpj', 'cnpj'),
    ('nome_contato', 'nome_contato'),
    ('whats', 'whats'),
    ('telefone', 'telefone'),
    ('email', 'email'),
    ('rua', 'rua'),
    ('numero', 'numero'),
    ('bairro', 'bairro'),
    ('cep', 'cep'),
    ('estado', 'estado'),
    ('cidade', 'cidade'),
)

nacionalidade_choices = (
    ('b', 'Brasileira'),
    ('e', 'Estrangeira'),
)


sexo_choices = (
    ('f', 'Feminino'),
    ('m', 'Masculino'),
)


humor_choices = (
    ('Feliz', 'Feliz'),
    ('Triste', 'Triste'),
    ('Queixoso', 'Queixoso'),
    ('Agressivo', 'Agressivo'),
    ('Agitado', 'Agitado'),
    ('Ansioso', 'Ansioso'),
    ('Apatia', 'Apatia'),
    ('Desconfiado', 'Desconfiado'),
    ('Irritado', 'Irritado'),
    ('Eufórico', 'Eufórico'),
    ('Sonolento', 'Sonolento'),
    ('Confuso', 'Confuso'),
    ('Desorientado', 'Desorientado'),
    ('Calmo', 'Calmo'),
    ('Eutimia', 'Eutimia'),
    ('Hipotomia', 'Hipotomia'),
    ('Hipertemia', 'Hipertemia'),
)


turnos = (
    ('Manhã', 'Manhã'),
    ('Tarde', 'Tarde'),
    ('Noite', 'Noite'),
    ('Diurno', 'Diurno'),
    ('Noturno', 'Noturno'),
    ('Integral', 'Integral'),
)

estado_civil_choices = (
    ('C', 'Casado'),
    ('S', 'Solteiro'),
    ('D', 'Divorciado'),
    ('V', 'Viúvo'),
)

carater_atendimento_choices = (
    ('E', 'Eletivo'),
    ('U', 'Urgência'),
    ('M', 'Emergência'),
)

tipo_alta_choices = (
    ('alta', 'Alta'),
    ('transferencia', 'Transferência'),
    ('obito', 'Óbito'),
    ('pedido', 'Pedido'),
)


entidade_encaminha_choices = (
    ('fundo_municipal_assistencia_social', 'Fundo Municipal de Assistência Social'),
    ('fundo_municipal_saude', 'Fundo Municipal de Saúde'),
    ('fundo_estadual_assistencia_social', 'Fundo Estadual de Assistência Social'),
    ('fundo_estadual_saude', 'Fundo Estadual de Saúde'),
    ('fundo_nacional_assistencia_social', 'Fundo Nacional de Assistência Social'),
    ('fundo_nacional_saude', 'Fundo Nacional de Saúde'),
    ('fundo_municipal', 'Fundo Municipal'),
    ('fundo_estadual', 'Fundo Estadual'),
    ('fundo_nacional', 'Fundo Nacional'),
    ('outros', 'Outros'),
)

intervalo_horas_choices = (
    (1, '1/1 h'),
    (2, '2/2 h'),
    (3, '3/3 h'),
    (4, '4/4 h'),
    (5, '5/5 h'),
    (6, '6/6 h'),
    (7, '7/7 h'),
    (8, '8/8 h'),
    (9, '9/9 h'),
    (10, '10/10 h'),
    (11, '11/11 h'),
    (12, '12/12 h'),
    (24, '24/24 h'),
)

horas_choices = (
    (1, '1 hora'),
    (2, '2 horas'),
    (3, '3 horas'),
    (4, '4 horas'),
    (5, '5 horas'),
    (6, '6 horas'),
    (7, '7 horas'),
    (8, '8 horas'),
    (9, '9 horas'),
    (10, '10 horas'),
    (11, '11 horas'),
    (12, '12 horas'),
    (13, '13 horas'),
    (14, '14 horas'),
    (15, '15 horas'),
    (16, '16 horas'),
    (17, '17 horas'),
    (18, '18 horas'),
    (19, '19 horas'),
    (20, '20 horas'),
    (21, '21 horas'),
    (22, '22 horas'),
    (23, '23 horas'),
    (00, '00 hora'),
)

duracao_dias_choices = (
    (1, '1 dia'),
    (2, '2 dias'),
    (3, '3 dias'),
    (4, '4 dias'),
    (5, '5 dias'),
    (6, '6 dias'),
    (7, '7 dias'),
    (8, '8 dias'),
    (9, '9 dias'),
    (10, '10 dias'),
    (11, '11 dias'),
    (12, '12 dias'),
    (13, '13 dias'),
    (14, '14 dias'),
    (15, '15 dias'),
    (16, '16 dias'),
    (17, '17 dias'),
    (18, '18 dias'),
    (19, '19 dias'),
    (20, '20 dias'),
    (21, '21 dias'),
    (22, '22 dias'),
    (23, '23 dias'),
    (24, '24 dias'),
    (25, '25 dias'),
    (26, '26 dias'),
    (27, '27 dias'),
    (28, '28 dias'),
    (29, '29 dias'),
    (30, '30 dias'),
    (31, '31 dias'),
)


duracao_presc_choices = (
    (1, 'Mesmo dia'),
    (2, '2 dias'),
    (3, '3 dias'),
    (4, '4 dias'),
    (5, '5 dias'),
    (6, '6 dias'),
    (7, '7 dias'),
    (8, '8 dias'),
    (9, '9 dias'),
    (10, '10 dias'),
    (11, '11 dias'),
    (12, '12 dias'),
    (13, '13 dias'),
    (14, '14 dias'),
    (15, '15 dias'),
    (16, '15 dias'),
    (17, '17 dias'),
    (18, '18 dias'),
    (19, '19 dias'),
    (20, '20 dias'),
    (21, '21 dias'),
    (22, '22 dias'),
    (23, '23 dias'),
    (24, '24 dias'),
    (25, '25 dias'),
    (26, '26 dias'),
    (27, '27 dias'),
    (28, '28 dias'),
    (29, '29 dias'),
    (30, '30 dias'),
)


regras_emails_choices = (
    ('redefinicao de senha', 'redefinicao de senha'),
    ('financeiro', 'financeiro'),
    ('nota fiscal', 'nota fiscal'),
)

fase_prescricao_choices = (
    ('U', 'Em uso'),
    ('S', 'Suspensa'),
)

fase_adep_choices = (
    ('P', 'Pendente'),
    ('A', 'Administrado'),
    ('N', 'Não Administrado'),
    ('S', 'Suspenso'),
)


relatorios_choices = (
    ('evolucao', 'Evolução'),
    ('prescricao', 'Prescrição'),
    ('adep', 'ADEP'),
    ('sae', 'SAE'),
    ('sinais_vitais', 'Sinais Vitais'),
    ('perdas_ganhos', 'Perdas e Ganhos'),
    ('plano_cuidados', 'Plano de Cuidados'),
    ('diagnostico', 'Diagnóstico'),
    ('oficios', 'Ofício'),
    ('orcamentos', 'Orçamento'),
    ('atas', 'Ata'),
    ('documentos_legais', 'Documentos Legais'),
)


cor_raca_choices = (
    ('branco', 'Branco'),
    ('preto', 'Preto'),
    ('pardo', 'Pardo'),
    ('amarelo', 'Amarelo'),
    ('indigena', 'Indigena'),
)


religiao_choices = (
    ('cristianismo', 'Cristianismo'),
    ('catolico', 'Católico'),
    ('evangelico', 'Evangélico'),
    ('luterano', 'Luterano'),
    ('testemunha_jeova', 'Testemunha de Jeová'),
    ('budismo', 'Budismo'),
    ('hinduismo', 'Hinduísmo'),
    ('islamismo', 'Islamismo'),
    ('judaismo', 'Judaísmo'),
    ('siquismo', 'Siquismo'),
    ('taoismo', 'Taoísmo'),
    ('ateismo', 'Ateísmo'),
    ('agnosticismo', 'Agnosticismo'),
)

via_administracao_choices = (
    ('vo', 'VO'),
    ('ev', 'EV'),
    ('im', 'IM'),
    ('--', '--'),
)


modalidade_contrato_choices = (
    ('CR', 'Credenciamento'),
    ('CO', 'Contrato'),
    ('PA', 'Particular'),
    ('OU', 'Outro'),
)

tipo_contrato_choices = (
    ('C', 'Contrato'),
    ('A', 'Aditivo'),
    ('O', 'Outros'),
)

modo_fatura_choices = (
    ('CL', 'Cliente'),
    ('CO', 'Convenio'),
)

descricao_internacao_choices = (
    ('internacao', 'Internação'),
    ('tratamento', 'Tratamento'),
    ('acolhimento', 'Acolhimento'),
)
# FIM CHOICES ###############################################

classificacao_pessoa_choices = (
    ('paciente', 'Paciente'),
    ('funcionario', 'Funcionário'),
)
