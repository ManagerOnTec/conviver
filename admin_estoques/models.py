from django.db import models
from admin_cadastros.models import BaseModel
from smart_selects.db_fields import ChainedForeignKey
from dominios.choices import via_administracao_choices


class TipoProduto(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição', unique=True,
                                 help_text='Descrição do tipo de produto. Ex: Medicamento, Material, etc.')

    class Meta:
        verbose_name = 'Tipo de Produto'
        verbose_name_plural = '1. Tipos de Produtos'

    def __str__(self):
        return f'{self.descricao}'


class Grupo(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição', unique=True,
                                 help_text='Descrição do grupo. Ex: Medicamento genérico, Medicamento Referência, Material Hospitalar, Material Geral ou de Escritório, etc.')

    tipo_produto = models.ForeignKey(TipoProduto, on_delete=models.PROTECT)

    pode_ser_prescrito = models.BooleanField(
        default=False, verbose_name='Grupo pode ser prescrito?', help_text='Se marcado, todos os produtos relacionados ao grupo poderão ser prescrito em uma prescrição médica. Recomendado para medicamentos.')

    grupo_de_medicamento = models.BooleanField(
        default=False, verbose_name='Grupo de medicamento?', help_text='Marque para todos os grupos de medicamentos. Recomendado para medicamentos.')

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = '2. Grupos'

    def __str__(self):
        return f'{self.descricao}'


class Classe(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição',
                                 help_text='Descrição da classe. Ex: analgésico, anti hipertensivo, equipos, dispositivos de acessos, etc.')

    class Meta:
        verbose_name = 'Classe'
        verbose_name_plural = '3. Classes'

    def __str__(self):
        return f'{self.descricao}'


class SubClasse(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição',
                                 help_text='Descrição da sub classe. Ex: inibidor, potencializador, equipo em bomba, equipo geral,  etc.')

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Sub Classe'
        verbose_name_plural = '4. Sub Classes'

    def __str__(self):
        return f'{self.descricao} - (Status: {self.status} - Classe: {self.classe})'


class Categoria(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição',
                                 help_text='Descrição da categoria. Ex: Restrito hospitalar, etc. Recomendado para distinguir valores nas tabelas de preços de faturamento.')

    class Meta:
        verbose_name = 'Sub Categoria'
        verbose_name_plural = '5. Categorias'

    def __str__(self):
        return f'{self.descricao}'


class UnidadeMedida(BaseModel):

    unidade_medida = models.CharField(
        max_length=3, verbose_name='Unidade de Medida', help_text='Unidade de medida do produto. Ex: ml, mg, g, etc.')
    descricao = models.CharField(max_length=255, verbose_name='Descrição',
                                 help_text='Descrição da unidade de medida. Ex: mililitro, miligrama, grama, etc.')

    class Meta:
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = '6. Unidades de Medidas'

    def __str__(self):
        return f'{self.unidade_medida}'


class Produto(BaseModel):

    descricao = models.CharField(max_length=32, verbose_name='Descrição')

    unidade_medida = models.ForeignKey(
        UnidadeMedida, on_delete=models.PROTECT, verbose_name='Unidade de Medida')

    via = models.CharField(
        max_length=50, choices=via_administracao_choices, verbose_name='Via Administração')

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        verbose_name='grupo',
    )

    classe = models.ForeignKey(
        Classe, blank=True, null=True,
        on_delete=models.PROTECT,
        verbose_name='Classe',

    )

    subclasse = ChainedForeignKey(
        SubClasse, blank=True, null=True,
        on_delete=models.PROTECT,
        verbose_name='subclasse',
        chained_field="classe",
        chained_model_field="classe",
        show_all=False,
        auto_choose=True,
    )

    principio_ativo = models.BooleanField(
        default=False, help_text='Se marcado, selecione o produto referência para este princípio ativo. Recomendado para medicamentos. Neste sistema tratamos o princípio ativo como o medicamento genérico, o item marcado como princípio ativo será o controlador do estoque')

    produto_referencia = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='produto_referencia_produto',
        help_text='Se o produto for um princípio ativo, vincule o produto de referência aqui. Se o produto for um produto de referência, não vincule nada aqui. Recomendado para medicamentos.',
    )

    categoria = models.ForeignKey(
        Categoria, blank=True, null=True,
        on_delete=models.PROTECT,
    )

    pode_ser_prescrito = models.BooleanField(default=False, verbose_name='Produto pode ser prescrito?',
                                             help_text='Se marcado, o produto poderá ser prescrito em uma prescrição médica. Caso pertença a um grupo marcado como pode ser prescrito, este não precisa ser marcado, ou seja, este campo é apenas para exceçoes do grupo. Recomendado para medicamentos.')

    observacao = models.CharField(blank=True, null=True, max_length=255, verbose_name='Observações gerais',
                                  help_text='Observação sobre o produto. Ex: Produto de uso exclusivo para o setor de enfermagem, etc.')

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = '7. Produtos'

        constraints = [
            models.UniqueConstraint(
                fields=['descricao', 'status'], name='unique_produto_status')
        ]

    def __str__(self):
        produto_referencia = self.produto_referencia if self.produto_referencia else "Sim"
        unidade_medida = self.unidade_medida if self.unidade_medida else " "
        via = self.via if self.via else " "
        return f'{self.descricao} / REF: {produto_referencia} / UM: {unidade_medida} / VIA: {via}'
