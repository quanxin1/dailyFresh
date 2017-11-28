from django.conf.urls import url
from order import views
urlpatterns=[
    url(r'^place/$',views.OrderPlacceView.as_view(),name='place'),
    url(r'^commit$',views.OrderCommitView.as_view(),name='commit'),
    url(r'^pay$',views.OrderPayView.as_view(),name='pay'),
    url(r"^check$",views.CheckPayView.as_view(),name="check"),
    url(r"^comment/(?P<order_id>.+)$",views.CommentView.as_view(),name="comment")
]