from django.shortcuts import render
from django.http import HttpResponse
from app.user.models import GoodsInfo
# Create your views here.
def test(request):
    return HttpResponse('ok')
def show(request):
    goods=GoodsInfo.objects.get(pk=1)
    context={'goods':goods}
    return render(request,'user/show.html',context)
