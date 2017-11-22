from django.conf.urls import url
from cart import views
urlpatterns=[
    url(r'^add$',views.CartAddView.as_view(),name='add'),
    url(r'^',views.CartInfoView.as_view(),name='cart')
]