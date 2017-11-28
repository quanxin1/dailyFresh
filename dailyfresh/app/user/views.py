from django.shortcuts import render,redirect
from django.http import HttpResponse
from user.models import GoodsInfo,User,Address
from django.views.generic import View
from django.core.urlresolvers import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from django.core.mail import send_mail
from celery_tasks.tasks import send_register_active_email
from utils.mixin import LoginRequireMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
from django.core.paginator import Paginator
import re


# Create your views here.
def test(request):
    return HttpResponse('ok')
def show(request):
    goods=GoodsInfo.objects.get(pk=1)
    context={'goods':goods}
    return render(request,'user/show.html',context)
    # return render(request,'user/user_center_info.html')
    # return render(request,'user/user_center_order.html')
    # return render(request,'user/user_center_site.html')
def Index(request):
    return redirect(reverse('goods:index'))
class Register(View):
    def get(self,request):
        return render(request,'user/register.html')
    def post(self,request):
        username=request.POST.get('user_name')
        password =request.POST.get('pwd')
        email=request.POST.get('email')
        allow=request.POST.get('allow')
        if not all([username,password,email]):
            return render(request,'user/register.html',{'errmsg':"数据不完整"})
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return render(request,'user/register.html',{'errmsg':"邮箱不合法"})
        if allow !='on':
            return render(request,'user/register.html',{'errmsg':"请同意协议"})
        try:
            user=User.objects.get(username=username)
        except User.DoesNotExist:
            user=None
        if user:
            return render(request,'user/register.html',{'errmsg':"用户已存在"})
        user=User.objects.create_user(username,email,password)
        user.is_active=0
        user.save()
        serializer=Serializer(settings.SECRET_KEY,3600)
        info = {'confirm':user.id}
        token=serializer.dumps(info).decode()
        # token=token
        send_register_active_email(email,username,token)
        return redirect(reverse('goods:index'))

class ActiveView(View):
    def get(self,request,token):
        serializer=Serializer(settings.SECRET_KEY,3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已失效')

class LoginView(View):
    def get(self,request):
        if 'username' in request.COOKIES:
            username=request.COOKIES.get('username')
            checked='checked'
        else:
            username=""
            checked=""
        context={'username':username,'checked':checked}
        return render(request,'user/login.html',context)
    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username,password]):
            return render(request,'user/login.html',{'errmsg':'信息不完整'})

        user=authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                login(request,user)
                next_url =request.GET.get('next',reverse('goods:index'))
                response=redirect(next_url)
                remember = request.POST.get('remember')
                if remember =='on':
                    response.set_cookie('username',username)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request,'user/login.html',{'errmsg':'用户未激活'})
        else:
            return render(request,'user/login.html',{'errmsg':'用户名或密码错误'})
class Logout(View):
    def get(self,request):
        logout(request)
        return redirect(reverse('goods:index'))

class UserInfoView(LoginRequireMixin,View):
    def get(self,request):
        user=request.user
        address=Address.objects.get_default_address(user=user)
        conn=get_redis_connection('default')
        list_key='history_%s'%user.id
        sku_ids=conn.lrange(list_key,0,4)
        goods_list=[]
        for id in sku_ids:
            goods=GoodsSKU.objects.get(id=id)
            goods_list.append(goods)
        context={'page':'user','address':address,'goods_list':goods_list}
        return render(request,'user/user_center_info.html',context)
class UserOrderView(LoginRequireMixin,View):
    def get(self,request,page):
        """用户中心订单页"""
        user =request.user
        orders= OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                amount=order_sku.price*order_sku.count
                order_sku.amount=amount
                #动态给order增加一个属性status_name
            order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
            #动态给order增加一个属性order_skus,保存订单信息
            order.order_skus=order_skus
        paginator=Paginator(orders,1)
        try:
            page=int(page)
        except Exception as e:
            page=1
        if page>paginator.num_pages:
            page=1
        order_page=paginator.page(page)

        num_pages=paginator.num_pages
        if num_pages < 5:
            pages=range(1,num_pages+1)
        elif page<=3:
            pages=range(1,6)
        elif num_pages-page<=2:
            pages=range(page-4,num_pages+1)
        else:
            pages=range(page-2,page+3)
        context = {'order_page':order_page,"pages":pages,"page":"order"}
        return render(request,'user/user_center_order.html',context)
class AddressView(LoginRequireMixin,View):
    def get(self,request):
        user = request.user
        address = Address.objects.get_default_address(user=user)
        return render(request,'user/user_center_site.html',{"page":"address",'address':address})
    def post(self,request):
        receiver=request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code=request.POST.get('zip_code')
        phone=request.POST.get('phone')
        if not all([receiver,addr,zip_code,phone]):
            return render(request,'user/user_center_site.html',{'errmsg':'数据不完整'})
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return render(request,'user/user_center_site.html',{'errmsg':'手机号码无效'})
        user=request.user
        address=Address.objects.get_default_address(user=user)
        if address:
            is_default=False
        else:
            is_default=True
        Address.objects.create(user=user,receiver=receiver,addr=addr,zip_code=zip_code,phone=phone,is_default=is_default)
        return redirect(reverse('user:address'))






