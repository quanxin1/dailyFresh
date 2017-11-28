from django.shortcuts import render
from django.views.generic import View
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from django.http import JsonResponse
from utils.mixin import LoginRequireMixin
# Create your views here.
class CartAddView(View):
    def post(self,request):
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'未登录请先登录'})
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')
        if not all([sku_id,count]):
            return JsonResponse({'res':1,"errmsg":"数据不完整"})
        try:
            count=int(count)
        except Exception as e:
            return JsonResponse({'res':2,"errmsg":"商品数据类型错误"})
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':3,'errmsg':"商品不存在"})

        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        sku_count=conn.hget(cart_key,sku_id)
        if sku_count:
            count+=int(sku_count)
        if count > sku.stock:
            return JsonResponse({'res': 4, "errmsg": "商品库存不足"})
        conn.hset(cart_key,sku_id,count)
        cart_count=conn.hlen(cart_key)
        return JsonResponse({"res":5,"message":"添加成功",'cart_count':cart_count})

class CartInfoView(LoginRequireMixin,View):
    def get(self,request):
        user=request.user
        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        cart_dict=conn.hgetall(cart_key)
        skus=[]
        total_count=0
        total_price=0
        for sku_id,count in cart_dict.items():
            sku=GoodsSKU.objects.get(id=sku_id)
            amount=sku.price*int(count)
            sku.amount=amount
            sku.count=count
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        context={'total_count':total_count,
                 'total_price':total_price,
                 'skus':skus}
        return render(request,'cart/cart.html',context)
class CartUpdateView(View):
    def post(self,request):
        print(1)
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,"errmsg":"请先登录"})
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')
        if not all([sku_id,count]):
            return JsonResponse({'res':1,"errmsg":"数据不完整"})
        try:
            count=int(count)
        except Exception as e:
            return JsonResponse({'res':2,"errmsg":"商品数据类型错误"})
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':3,'errmsg':"商品不存在"})
        conn=get_redis_connection('default')
        cart_key="cart_%d"%user.id
        if count > sku.stock:
            return JsonResponse({'res':4,'errmsg':"商品库存不足"})
        conn.hset(cart_key,sku_id,count)
        total_count=0
        vals=conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        return JsonResponse({'res':5,"total_count":total_count,'message':"更新成功"})

class CartDeleteView(View):
    def post(self,request):
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请先登录'})
        sku_id=request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res':1,'errmsg':'参数不完整'})
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':2,"errmsg":"商品不存在"})
        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        conn.hdel(cart_key,sku_id)

        total_count=0
        vals=conn.hvals(cart_key)
        for val in vals:
            total_count+=int(val)
        return JsonResponse({'res':3,'total_count':total_count,'message':'删除成功'})









