from django.contrib import admin
from goods.models import GoodsSKU,GoodsType,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
# Register your models here.
admin.site.register(GoodsType)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexTypeGoodsBanner)
admin.site.register(IndexPromotionBanner)
admin.site.register(GoodsSKU)
