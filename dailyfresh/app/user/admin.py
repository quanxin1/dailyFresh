from django.contrib import admin
from user.models import GoodsInfo
# Register your models here.
class GoodsInfoAdmin(admin.ModelAdmin):
    list_display = ['id']
admin.site.register(GoodsInfo,GoodsInfoAdmin)