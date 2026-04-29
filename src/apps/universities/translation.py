from modeltranslation.translator import TranslationOptions, register

from .models import City, Region, Speciality, University


@register(Region)
class RegionTranslation(TranslationOptions):
    fields = ("name",)


@register(City)
class CityTranslation(TranslationOptions):
    fields = ("name",)


@register(University)
class UniversityTranslation(TranslationOptions):
    fields = ("name", "description")


@register(Speciality)
class SpecialityTranslation(TranslationOptions):
    fields = ("name", "description")
