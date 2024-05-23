from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name='getattribute')
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    return getattr(value, str(arg))


@register.filter(name='multiply')
def multiply(value, arg):
    return value * arg
