from django.contrib import admin
from bcse_app import models
# Register your models here.

# Register your models here.
admin.site.register(models.EquipmentType)
admin.site.register(models.Equipment)
admin.site.register(models.WorkPlace)
admin.site.register(models.UserProfile)
admin.site.register(models.WorkshopCategory)
admin.site.register(models.Workshop)
admin.site.register(models.ActivityKit)
admin.site.register(models.Activity)
admin.site.register(models.Reservation)
admin.site.register(models.WorkshopRegistrationSetting)
admin.site.register(models.Registration)
admin.site.register(models.Team)
admin.site.register(models.TeacherLeader)
