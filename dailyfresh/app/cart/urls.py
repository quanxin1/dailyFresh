from django.conf.urls import url
from cart import views
urlpatterns=[
    url(r'^add$',views.CartAddView.as_view(),name='add'),
    url(r'^update$',views.CartUpdateView.as_view(),name='update'),
    url(r'^delete$',views.CartDeleteView.as_view(),name='delete'),
    url(r'^$',views.CartInfoView.as_view(),name='cart'),

]