from modeltranslation.translator import TranslationOptions, register

from .models import NotificationTemplate


@register(NotificationTemplate)
class NotificationTemplateTranslation(TranslationOptions):
    fields = ("title", "body")
