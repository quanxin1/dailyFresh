from django.conf.urls import url
from goods import views
urlpatterns=[
    url(r'^index$',views.Index.as_view(),name='index'),
    url(r'^goods/(?P<sku_id>\d+)$',views.DetailView.as_view(),name='detail'),
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$',views.ListView.as_view(),name='list'),
]