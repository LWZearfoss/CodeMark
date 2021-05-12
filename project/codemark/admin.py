from django.contrib import admin

from django.contrib import admin

from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Department, Course, Class, File, Fixture, Text, FileSchema, Step, RunStep, TestStep, Level, Assignment, Submission, StepOutput, RunStepOutput, TestStepOutput, LevelOutput, Result

admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Class)
admin.site.register(File)
admin.site.register(Fixture)
admin.site.register(Text)
admin.site.register(FileSchema)
admin.site.register(Step)
admin.site.register(RunStep)
admin.site.register(TestStep)
admin.site.register(Level)
admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(StepOutput)
admin.site.register(RunStepOutput)
admin.site.register(TestStepOutput)
admin.site.register(LevelOutput)
admin.site.register(Result)


class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (None, {
            'fields': ('nickname', 'phone_number', 'school_id'),
        }),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {
            'fields': ('first_name', 'last_name', 'email', 'nickname', 'phone_number', 'school_id', 'groups'),
        }),
    )


UserAdmin.list_display += ('nickname', 'phone_number', 'school_id')

admin.site.register(User, UserAdmin)
