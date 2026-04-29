from django.contrib import admin

from .models import SalesNote, StatusChangeLog


@admin.register(SalesNote)
class SalesNoteAdmin(admin.ModelAdmin):
    list_display = ("student", "manager", "created_at")
    autocomplete_fields = ("student", "manager")
    date_hierarchy = "created_at"


@admin.register(StatusChangeLog)
class StatusChangeLogAdmin(admin.ModelAdmin):
    list_display = ("student", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status",)
    autocomplete_fields = ("student", "changed_by")
    date_hierarchy = "created_at"
