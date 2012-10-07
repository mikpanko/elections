# -*- coding:utf-8 -*-
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response
from django.template import loader, RequestContext
from django.views.generic.base import TemplateView

from elements.locations.utils import breadcrumbs_context, subregion_list
from locations.models import Location
from locations.utils import get_roles_counters
from navigation.forms import FeedbackForm
from services.cache import cache_function

@cache_function('main_page', 30)
def main_page_context():
    total_counter = User.objects.filter(is_active=True).count()

    sub_regions = subregion_list()
    return {
        'counters': get_roles_counters(country), # TODO: country must be used
        'sub_regions': sub_regions,
        'total_counter': total_counter,
    }

class BaseMainView(TemplateView):
    template_name = 'main/base.html'
    tab = '' # 'main' or 'wall'

    def get_context_data(self, **kwargs):
        ctx = super(BaseMainView, self).get_context_data(**kwargs)

        ctx.update(main_page_context())
        ctx.update({'tab': self.tab})

        return ctx

def main1(request):
    if not request.user.is_authenticated():
        html = cache.get('main_html')
        if html:
            return HttpResponse(html)

    ctx = {'tab': 'main'}
    ctx.update(main_page_context())

    tabs = [
        ('main', u'Что делать?', '', 'main/view.html'),
        #('main_news', u'Новости', reverse('main_news'), 'main/news.html'),
        #('wall', u'Сообщения', reverse('wall'), 'projects/wall.html'),
    ]

    html = loader.render_to_string('main/base.html', context_instance=RequestContext(request, ctx))

    if not request.user.is_authenticated():
        cache.set('main_html', html, 300)

    return HttpResponse(html)

def main(request):
    return redirect(reverse('location_info', args=[1]))

class WallView(BaseMainView):
    tab = 'wall'
wall = WallView.as_view()

def static_page(request, **kwargs):
    """ 
    kwargs must contain the following keys: 'tab', 'template', 'tabs'.
    kwargs['tabs']=[(name, url, template, css_class), ...]
    """
    ctx = breadcrumbs_context(Location.objects.country())
    ctx.update(kwargs)
    return render_to_response(kwargs['template'], context_instance=RequestContext(request, ctx))

def sitemap(request):
    context = {
        'locations': Location.objects.filter(region=None).only('id', 'name'),
    }
    return render_to_response('sitemap.html', context_instance=RequestContext(request, context))

def feedback(request, **kwargs):
    if request.method == 'POST':
        form = FeedbackForm(request, request.POST)
        if form.is_valid():
            form.send()
            return redirect('feedback_thanks')
    else:
        form = FeedbackForm(request)

    ctx = {
        'form': form,
        'template': 'feedback/feedback.html',
    }
    ctx.update(kwargs)
    return static_page(request, **ctx)
