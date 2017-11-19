from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection
from goods.models import GoodsType,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
# Create your views here.
# def index(request):
#     return render(request,'goods/index.html')
class Index(View):
    def get(self,request):
        types=GoodsType.objects.all()
        goodsbanner=IndexGoodsBanner.objects.all().order_by('index')
        promotionbanner=IndexPromotionBanner.objects.all().order_by('index')
        for typeTemp in types:
            img_banner=IndexTypeGoodsBanner.objects.filter(type=typeTemp,display_type=1).order_by('index')
            title_banner=IndexTypeGoodsBanner.objects.filter(type=typeTemp,display_type=0).order_by('index')
            typeTemp.img_banner=img_banner
            typeTemp.title_banner=title_banner
        cart_count=0
        user=request.user
        if user.is_authenticated():#用户已登录
            conn=get_redis_connection('default')
            cart_key="cart_%d"%user.id
            cart_count=conn.hlen(cart_key)
        print(type(goodsbanner[0].image.url))
        print(type(goodsbanner[0].image))
        context={'types':types,'goodsbanner':goodsbanner,'promotionbanner':promotionbanner,'cart_count':cart_count}
        return render(request,'goods/index.html',context)
