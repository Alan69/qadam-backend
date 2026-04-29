from modeltranslation.translator import TranslationOptions, register

from .models import Tariff


@register(Tariff)
class TariffTranslation(TranslationOptions):
    fields = ("name",)
