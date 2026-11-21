from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import HelloJob, User

admin.site.register(User, UserAdmin)


@admin.register(HelloJob)
class HelloJobAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "status", "created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
