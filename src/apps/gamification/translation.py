from modeltranslation.translator import TranslationOptions, register

from .models import AvatarItem, Challenge


@register(AvatarItem)
class AvatarItemTranslation(TranslationOptions):
    fields = ("name",)


@register(Challenge)
class ChallengeTranslation(TranslationOptions):
    fields = ("title", "description")
