from rest_framework import serializers
from .models import Prescricao
from atendimentos.models import Atendimento


class PrescricaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescricao
        fields = '__all__'
