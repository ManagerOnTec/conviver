import os

from django.forms import BooleanField, CharField
from django import template

register = template.Library()


@register.filter(name='has_perm')
def has_perm(user, permission):
    return user.has_perm(permission)


@register.filter
def get_textarea_fields(form):
    return [field for field in form if 'Textarea' in dir(field.field.widget)]


@register.filter
def get_other_fields(form):
    return [field for field in form if 'BooleanField' not in dir(field.field) and 'Textarea' not in dir(field.field.widget)]


@register.filter(name='is_booleanfield')
def is_booleanfield(field):
    return isinstance(field, BooleanField)


@register.filter(name='is_textarea')
def is_textarea(field):
    return isinstance(field.field, CharField) and field.field.widget.__class__.__name__ == 'Textarea'


@register.filter
def get_boolean_fields(form):
    return [field for field in form if isinstance(field.field, BooleanField)]


@register.filter
def is_image_file(file_field):
    name = getattr(file_field, 'name', '') or str(file_field or '')
    extension = os.path.splitext(name.lower())[1]
    return extension in {'.jpg', '.jpeg', '.png'}


@register.filter
def file_basename(file_field):
    name = getattr(file_field, 'name', '') or str(file_field or '')
    return os.path.basename(name)
