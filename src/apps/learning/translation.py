from modeltranslation.translator import TranslationOptions, register

from .models import Lesson, Section, Subject, Topic


@register(Subject)
class SubjectTranslation(TranslationOptions):
    fields = ("name", "description")


@register(Section)
class SectionTranslation(TranslationOptions):
    fields = ("name",)


@register(Topic)
class TopicTranslation(TranslationOptions):
    fields = ("name",)


@register(Lesson)
class LessonTranslation(TranslationOptions):
    fields = ("title", "theory")
