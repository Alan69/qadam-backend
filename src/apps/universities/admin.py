from django.contrib import admin

from .models import City, Region, Speciality, University


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name", "region__name")
    autocomplete_fields = ("region",)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city__region",)
    search_fields = ("name", "city__name")
    autocomplete_fields = ("city",)


@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "university", "threshold_score")
    list_filter = ("university",)
    search_fields = ("name", "code", "university__name")
    autocomplete_fields = ("university",)
    filter_horizontal = ("required_subjects",)
