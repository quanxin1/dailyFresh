from django.contrib.auth.decorators import login_required
from django.views.generic import View
class LoginRequireMixin(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view=super(LoginRequireMixin, cls).as_view(**initkwargs)
        return login_required(view)