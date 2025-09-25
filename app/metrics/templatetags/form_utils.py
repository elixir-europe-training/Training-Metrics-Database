from django import template

register = template.Library()

@register.filter
def use_list(item):
    return (
        item
        if isinstance(item, list)
        else [item]
    )
