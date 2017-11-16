from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from user import views
urlpatterns=[
    url(r'^test/$',views.test),
    url(r'^show/$',views.show),
    url(r'^/index/$',views.Index,name='index'),
    url(r'^register/$',views.Register.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$',views.ActiveView.as_view(),name='active'),
    url(r'^login/$',views.LoginView.as_view(),name='login'),
    url(r'^user/$',login_required(views.UserInfoView.as_view()),name='user'),
    url(r'^order/$',views.UserOrderView.as_view(),name='order'),
    url(r'^address/$',views.AddressView.as_view(),name='address'),
    url(r'^logout/$',views.Logout.as_view(),name='logout')
]