from django.shortcuts import render,redirect
from django.views.generic import View
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from datetime import datetime
from django.db import transaction
from utils.mixin import LoginRequireMixin
from user.models import Address
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
from alipay import AliPay
from django.conf import settings
import os
# Create your views here.
class OrderPlacceView(LoginRequireMixin,View):
    def post(self,request):
        user=request.user
        sku_ids = request.POST.getlist('sku_ids')
        if not sku_ids:
            return redirect(reverse('cart:show'))
        addrs=Address.objects.filter(user=user)
        conn=get_redis_connection('default')
        cart_key="cart_%d"%user.id
        total_count=0
        total_price=0
        skus=[]
        for sku_id in sku_ids:
            sku=GoodsSKU.objects.get(id=sku_id)
            count=conn.hget(cart_key,sku_id)
            amount=sku.price*int(count)
            sku.amount = amount
            sku.count = count
            skus.append(sku)
            total_count +=int(count)
            total_price += amount
        transit_price = 10
        total_pay = total_price+transit_price
        sku_ids=",".join(sku_ids)
        context={'skus':skus,"addrs":addrs,"total_count":total_count
                 ,"total_price":total_price,"total_pay":total_pay,
                 "transit_price":transit_price,"sku_ids":sku_ids}
        return render(request,"order/place_order.html",context)
#mysql事务：一组sql操作要么成功要么全部失败
#高并发：防止用户下单重复
class OrderCommitView1(View):
    @transaction.atomic
    def post(self,request):
        """提交订单"""
        #获取登录用户
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({"res":0,"errmsg":"用户未登录"})
        # 接受数据
        addr_id=request.POST.get("addr_id")
        pay_method = request.POST.get("pay_method")
        sku_ids=request.POST.get('sku_ids')
        print("addr_id:",addr_id,"pay_method",pay_method,sku_ids)
        #校验数据
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res':1,"errmsg":"数据不完整"})
        #验证支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({"res":2,"errmsg":"非法的支付方法"})
        print(pay_method)
        #校验地址
        try:
            addr=Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({"res":3,"errmsg":"地址信息错误"})
        #业务处理，组织订单数据，订单id格式：20171124151720+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        transit_price=10
        total_count=0
        total_price=0
        #设置保存点
        save_id=transaction.savepoint()
        try:
            order=OrderInfo.objects.create(order_id=order_id,user=user,addr=addr,pay_method=pay_method,
                                           total_count=total_count,total_price=total_price,transit_price=transit_price)
            #向订单商品表中添加信息时，用户买了几件商品，需要添加几笔记录
            conn=get_redis_connection('default')
            cart_key="cart_%d"%user.id
            sku_ids=sku_ids.split(',')
            for sku_id in sku_ids:
                #根据商品的id获取商品信息
                try:
                    #select * form df_order_goods where id=17 for update
                    sku=GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    #商品不存在
                    return JsonResponse({"res":4,"errmsg":"商品不存在"})
                #从redis中获取用户要购买商品的数目
                count=conn.hget(cart_key,sku_id)
                if int(count) > sku.count:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"res":6,"errmsg":"商品库存不足"})
                #向商品订单中添加一条记录
                OrderGoods.objects.create(order=order,sku=sku,count=count,price=sku.price)
                #更新对应商品的库存及销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                #更新计算订单中商品的总数和总金额
                total_count += int(count)
                amount=sku.price*int(count)
                total_price +=amount
            #累加计算订单中对应的商品及总件数和总金额数
            order.total_count=total_count
            order.total_price=total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({"res":7,"errmsg":"下单失败"})
        transaction.savepoint_commit(save_id)
        #删除用户购物车中的相应记录
        conn.hdel(cart_key,*sku_ids)

        return JsonResponse({"res":5,"message":"订单创建成功"})

class OrderCommitView(View):
    @transaction.atomic
    def post(self,request):
        """订单创建"""
        #判断用户是否登录
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({"res":0,"errmsg":"用户未登录"})
        #接收数据
        addr_id = request.POST.get("addr_id")
        pay_method=request.POST.get("pay_method")
        sku_ids=request.POST.get("sku_ids")
        print(1)
        #校验数据
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({"res":1,"errmsg":"数据不完整"})
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({"res":2,"errmsg":"非法支付方式"})
        try:
            addr=Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({"res":3,"errmsg":"地址信息错误"})
        #业务处理：，组织订单信息 订单id格式：20171124160223+用户id
        order_id=datetime.now().strftime("%Y%m%d%H%M%S")+str(user.id)
        #运费
        transit_price = 10
        #总金额和总数目
        total_price=0
        total_count=0
        #设置保存点
        save_id = transaction.savepoint()
        try:
            order=OrderInfo.objects.create(order_id=order_id,addr=addr,user=user,
                                           pay_method=pay_method,total_count=total_count,
                                           total_price=total_price,transit_price=transit_price)
            conn=get_redis_connection('default')
            cart_key="cart_%d"%user.id
            sku_ids=sku_ids.split(",")
            for sku_id in  sku_ids:
                for i in range(3):
                    try:
                        sku=GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({"res":4,"errmsg":"商品不存在"})
                    #从redis中获取用户要购买的商品的数数量
                    count=conn.hget(cart_key,sku_id)

                    #更新时做出判断，判断过呢更新时和之前那查到的库存数据是否一致

                    #更新对应商品的库存和销量
                    origin_stock = sku.stock
                    news_stock = origin_stock-int(count)
                    news_sales = sku.sales+int(count)
                    print("user:%d stock:%d"%(user.id,origin_stock))
                    import time
                    time.sleep(1)
                    #判断商品的库存
                    if int(count)>sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({"res":6,"errmsg":"商品库存不足"})
                    #返回受影响的函数
                    #update df_order_goods set stock=new_stock and sales=newsales
                    #where id=sku_id and stock=origin_stock;
                    res=GoodsSKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=news_stock,
                                                                                     sales=news_sales)
                    if res ==0:
                        if i==2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({"res":7,"errmsg":"下单失败"})
                        continue
                    #向订单商品中添加一条记录、
                    OrderGoods.objects.create(order=order,sku=sku,count=count,price=sku.price)
                    #向订单表中添加商品的总数目和总金额
                    total_count+=int(count)
                    amount=sku.price*int(count)
                    total_price+=amount
                    break
            #更新订单信息中对应商品的总件数和总金额
            order.total_count=total_count
            order.total_price=total_price
            order.save()
        except Exception as e:
            print(e)
            transaction.savepoint_rollback(save_id)
            return JsonResponse({"res":7,"errmsg":"下单失败"})
        transaction.savepoint_commit(save_id)
        #删除用户购物车中的相应记录

        conn.hdel(cart_key,*sku_ids)
        return JsonResponse({"res":5,"messsage":"订单创建成功"})


class OrderPayView(View):
    def post(self,request):
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,"errmsg":"用户未登录"})
        order_id=request.POST.get('order_id')
        if not order_id:
            return JsonResponse({"res":1,"errmsg":"数据不完整"})
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user,pay_method=3,order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({"res":2,"errmsg":"订单id出错"})
        alipay=AliPay(
            appid="2016082600312909",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'app/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'app/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        total_pay=order.total_price + order.transit_price
        order_string=alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject="天天生鲜%s"%order_id,
            return_url=None,
            notify_url=None
        )
        pay_url="https://openapi.alipaydev.com/gateway.do?"+order_string
        return JsonResponse({'res':3,'pay_url':pay_url})


class CheckPayView(View):
    def post(self,request):
        user=request.user
        if not user.is_authenticated():
            return JsonResponse({"res":0,"errmsg":"用户未登录"})

        order_id=request.POST.get('order_id')
        if not order_id:
            return JsonResponse({"res":1,"errmsg":"订购id为空"})
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user,
                                        pay_method=3,
                                        order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({"res":2,"errmsg":"订单id出错"})
        alipay=AliPay(
            appid="2016082600312909",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'app/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'app/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            # {
            #         "trade_no": "2017032121001004070200176844", # 支付宝交易号
            #         "code": "10000", # 接口调用是否成功
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #             {
            #                 "amount": "20.00",
            #                 "fund_channel": "ALIPAYACCOUNT"
            #             }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS", # 支付状态
            #         "total_amount": "20.00"
            #    }
            code=response.get("code")
            if code =="10000" and response.get("trade_status")=="TRADE_SUCCESS":
                trade_no=response.get('trade_no')
                order.trade_no=trade_no
                order.order_status=4
                order.save()
            elif code == "40004" or (code=="10000" and response.get('trade_status')=="WAIT_BUYER_PAY"):
                import time
                time.sleep(5)
                continue
            else:
                return JsonResponse({"res":4,"errmsg":"支付出错"})


class CommentView(LoginRequireMixin,View):
    def get(self,request,order_id):
        print(order_id)
        user=request.user
        if not order_id:
            return redirect(reverse("user:order",kwargs={"page":1}))
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order",kwargs={"page":1}))
        order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
        order_skus=OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount=order_sku.price*order_sku.count
            order_sku.amount=amount
        order.order_skus=order_skus
        context={"order":order}
        return render(request,"order/order_comment.html",context)
    def post(self,request,order_id):
        user=request.user
        if not order_id:
            return redirect(reverse("user:order",kwargs={"page":1}))
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order",kwargs={"page":1}))
        total_count=request.POST.get("total_count")
        total_count=int(total_count)

        for i in range(1,total_count+1):
            sku_id=request.POST.get("sku_%d"%i)
            content=request.POST.get("content_%d"%i,"")
            try:
                order_goods=OrderGoods.objects.get(order=order,sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment=content
            order_goods.save()
        order.status=5
        order.save()
        return redirect(reverse("user:order",kwargs={"page":1}))










