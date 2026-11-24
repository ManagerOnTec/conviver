# admin_exames — instruções
## Fluxo de negócio
- Administrar tipos de exames e liberações por estabelecimento, profissão ou profissional.
- O prontuário cria exames por atendimento; cada exame pode possuir resultados, anotações e até três anexos por resultado.

## Relação Exame ↔ Agenda (`agenda_pacientes`)
- O agendamento de exame é **por atendimento** e referencia o **exame
  solicitado** (`AgendaPaciente.exame` → `prontuarios.Exame`). Não existe
  `pessoa` no agendamento — o paciente é sempre o do atendimento.
- Regras da agenda (validadas no `AgendaPacienteForm` e no model):
  - tipo do tipo exame → **exige** `exame` do **mesmo atendimento**, que **não
    pode ter sido executado** (sem `ResultadoExame` ativo);
  - tipo não-exame → **não** pode ter `exame` vinculado.
- **Execução espelhada**: efetuar na agenda marca/genera o `ResultadoExame` do
  exame; desfazer remove. O que faz em um reflete no outro.
- A listagem de exames do prontuário (`exame_listar.html`) mostra o painel
  “Agendamentos de exame” do atendimento; a agenda nunca derruba a listagem.

## Regras obrigatórias
- O tipo de exame padrão deve pertencer aos tipos liberados no parâmetro.
## Validações
- **Agenda ↔ Exame** (ver detalhes em `agenda_pacientes/instrucoes_agenda_pacientes.md`):
  - exame solicitado só é obrigatório quando o tipo de agendamento é do tipo
    exame; o exame deve pertencer ao **mesmo atendimento** e não pode ter sido
    executado (sem `ResultadoExame` ativo);
  - efetuar na agenda marca/remove o `ResultadoExame` do exame — e o que faz
    em um reflete no outro.
- Não remover a validação de `atendimento` no agendamento: **não existe**
  `AgendaPaciente.pessoa` (o paciente é sempre o do atendimento).
- Arquivos de resultado limitados a PDF, PNG, JPG e JPEG, com limite de 5 MB por arquivo.
- Exames e resultados mantêm auditoria de criação e alteração.
- A assinatura do PDF usa a infraestrutura `salvar_pdf_prontuario` e os gerenciadores geral/personalizado do `admin_relatorios`.

## Não fazer
- Não aceitar extensões adicionais nem mais de três arquivos por resultado.
- Não expor resultados inativos na listagem do prontuário.

## Como testar
- `python manage.py check`.
- Testar cadastro/edição de exame, permissão por estabelecimento e upload de cada extensão permitida e rejeição de uma extensão proibida.
