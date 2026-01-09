from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    """Tách chuỗi dựa trên ký tự phân cách (VD: "," )"""
    return value.split(key)