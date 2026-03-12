from django.forms import DateTimeInput


# lidar com entrada data hora no mesmo campo
# esse formato nao é aceito no firefox, apenas google e edge

class DateTimePickerInput(DateTimeInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'datetimepicker',
        })
