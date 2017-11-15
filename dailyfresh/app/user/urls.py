from django.conf.urls import url
from user import views
urlpatterns=[
    url(r'^test/$',views.test),
    url(r'^show/$',views.show),
    url(r'^register/$',views.Register.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$',views.ActiveView.as_view(),name='active'),
    url(r'^login/$',views.LoginView.as_view(),name='login'),
]