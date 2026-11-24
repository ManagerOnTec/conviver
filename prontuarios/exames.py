from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import timezone
from .forms_exames import ResultadoExameEdicaoForm
from .models import Exame, ResultadoExame
ResultadoExameFormSet = inlineformset_factory(
    Exame, ResultadoExame, form=ResultadoExameEdicaoForm,
    extra=3, can_delete=False,
)


def salvar_resultados_exame(exame, formset, usuario):
    # Persiste resultados e atualiza auditoria na mesma transação do exame.
    if not formset.is_valid():
        raise ValidationError('Revise os dados de resultado e os anexos do exame.')

    formset.instance = exame
    resultados = formset.save(commit=False)
    agora = timezone.now()
    for resultado in resultados:
        if resultado.pk:
            resultado.us_atualizacao = usuario
            resultado.dt_atualizacao = agora
        else:
            resultado.us_registro = usuario
        resultado.full_clean()
        resultado.save()

    formset.save_m2m()
    for resultado in formset.deleted_objects:
        resultado.delete()
