from django import template

from assistant.formatting import assistant_reply_html

register = template.Library()


@register.filter(name="assistant_bubble_html")
def assistant_bubble_html(value):
    if not value:
        return ""
    return assistant_reply_html(str(value))
