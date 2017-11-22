from django.shortcuts import render,redirect
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator
from django_redis import get_redis_connection
from django.core.urlresolvers import reverse
from order.models import OrderGoods
from goods.models import GoodsSKU,GoodsType,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
# Create your views here.
# def index(request):
#     return render(request,'goods/index.html')
class Index(View):
    def get(self,request):
        context=cache.get('index_page_data')
        if context is None:
            types=GoodsType.objects.all()
            goodsbanner=IndexGoodsBanner.objects.all().order_by('index')
            promotionbanner=IndexPromotionBanner.objects.all().order_by('index')
            for typeTemp in types:
                img_banner=IndexTypeGoodsBanner.objects.filter(type=typeTemp,display_type=1).order_by('index')
                title_banner=IndexTypeGoodsBanner.objects.filter(type=typeTemp,display_type=0).order_by('index')
                typeTemp.img_banner=img_banner
                typeTemp.title_banner=title_banner
            context={''}
        cart_count=0
        user=request.user
        if user.is_authenticated():#用户已登录
            conn=get_redis_connection('default')
            cart_key="cart_%d"%user.id
            cart_count=conn.hlen(cart_key)
        # print(type(goodsbanner[0].image.url))
        # print(type(goodsbanner[0].image))
        context={'types':types,'goodsbanner':goodsbanner,'promotionbanner':promotionbanner,'cart_count':cart_count}
        return render(request,'goods/index.html',context)
class DetailView(View):
    def get(self,request,sku_id):
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExit:
            return redirect(reverse('goods:index'))
        types=GoodsType.objects.all()
        sku_orders=OrderGoods.objects.filter(sku=sku).exclude(comment='')[:30]
        new_skus=GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        same_spu_skus=GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)
        cart_count=0
        user=request.user
        if user.is_authenticated():
            conn=get_redis_connection('default')
            cart_key='cart_%d'%user.id
            cart_count=conn.hlen(cart_key)

            conn=get_redis_connection('default')
            history_key="history_%d"%user.id
            conn.lrem(history_key,0,sku_id)
            conn.lpush(history_key,sku_id)
            conn.ltrim(history_key,0,4)

        context={'sku':sku,'types':types,
                 'sku_orders':sku_orders,
                 'new_skus':new_skus,
                 'same_spu_skus':same_spu_skus,
                 'cart_count':cart_count}
        return render(request,'goods/detail.html',context)


class ListView(View):
    def get(self,request,type_id,page):
        try:
            type=GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExit:
            return redirect(reverse('goods:index'))
        sort=request.GET.get('sort')
        types=GoodsType.objects.all()
        if sort =='price':
            skus=GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort =='hot':
            skus=GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort='default'
            skus=GoodsSKU.objects.filter(type=type).order_by('-id')
        paginator = Paginator(skus,1)
        try:
            page=int(page)
        except Exception as e:
            page=1
        if page > paginator.num_pages:
            page=1
        skus_page = paginator.page(page)

        num_pages=paginator.num_pages
        if num_pages<=5:
            pages=range(1,num_pages+1)
        elif page<=3:
            pages=range(1,6)
        elif num_pages-page<=2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page+3)

        new_skus=GoodsSKU.objects.filter(type=type).order_by('-create_time')[:3]

        cart_count=0
        user=request.user
        if user.is_authenticated():
            conn=get_redis_connection('default')
            cart_key="cart_%d"%user.id
            cart_count=conn.hlen(cart_key)

        context={'type':type,'types':types,
                 'skus_page':skus_page,
                 'new_skus':new_skus,
                 'cart_count':cart_count,
                 'sort':sort,'pages':pages}

        return render(request,'goods/list.html',context)













