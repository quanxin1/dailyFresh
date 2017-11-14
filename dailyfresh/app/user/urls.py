from django.conf.urls import url
from app.user import views
urlpatterns=[
    url(r'^test/$',views.test),
    url(r'^show/$',views.show)
]