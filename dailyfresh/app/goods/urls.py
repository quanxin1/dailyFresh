from django.conf.urls import url
from goods import views
urlpatterns=[
    url(r'^$',views.Index.as_view(),name='index'),
]