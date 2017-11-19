from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
from django.template import loader,RequestContext
from django_redis import get_redis_connection
import time,os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()
from goods.models import GoodsType,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner

app=Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/3')

@app.task
def send_register_active_email(to_email,username,token):
    subject='天天生鲜欢迎信息'
    message=''
    sender=settings.EMAIL_FROM
    receiver=[to_email]
    html_msg='<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
    username, token, token)
    send_mail(subject,message,sender,receiver,html_message=html_msg)
    time.sleep(5)
@app.task
def generate_static_index_html():
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
        context={'types':types,'goodsbanner':goodsbanner,'promotionbanner':promotionbanner,'cart_count':cart_count}
        temp=loader.get_template('goods/static_index.html')
        static_html=temp.render(context)
        save_path = os.path.join(settings.BASE_DIR,'static/index.html')
        with open(save_path) as f:
            f.write(static_html)
