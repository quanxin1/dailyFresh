from django.shortcuts import render,redirect
from django.http import HttpResponse
from user.models import GoodsInfo,User
from django.views.generic import View
from django.core.urlresolvers import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.contrib.auth import authenticate,login
from django.core.mail import send_mail
from celery_tasks.tasks import send_register_active_email
import re

# Create your views here.
def test(request):
    return HttpResponse('ok')
def show(request):
    goods=GoodsInfo.objects.get(pk=1)
    context={'goods':goods}
    return render(request,'user/show.html',context)
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
                response=redirect(reverse('goods:index'))
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









