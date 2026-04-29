from django.contrib import admin

from .models import CuratorAssignmentHistory, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user_phone",
        "grade",
        "learning_language",
        "sales_status",
        "assigned_curator",
    )
    list_filter = ("grade", "learning_language", "sales_status")
    search_fields = ("name", "user__phone", "parent_phone")
    autocomplete_fields = ("user", "assigned_curator", "region", "city")
    filter_horizontal = ("selected_subjects", "target_universities", "target_specialities")
    raw_id_fields = ()

    @admin.display(description="Телефон", ordering="user__phone")
    def user_phone(self, obj: StudentProfile) -> str:
        return obj.user.phone


@admin.register(CuratorAssignmentHistory)
class CuratorAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "curator", "assigned_at", "unassigned_at")
    list_filter = ("curator",)
    search_fields = ("student__name", "student__user__phone", "curator__phone")
    date_hierarchy = "assigned_at"
    autocomplete_fields = ("student", "curator")
