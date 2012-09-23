# -*- coding:utf-8 -*-
import json

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.views.generic.base import TemplateView

from elements.locations.utils import breadcrumbs_context
from elements.utils import entity_tabs_view
from locations.models import Location
from locations.utils import get_locations_data, get_roles_counters, get_roles_query
from users.forms import CommissionMemberForm, WebObserverForm
from users.models import CommissionMember, WebObserver

# TODO: web_observers tab is not activated for tiks and lead to crush
class BaseLocationView(TemplateView):
    template_name = 'locations/base.html'
    tab = ''

    def update_context(self):
        return {}

    def get_context_data(self, **kwargs):
        ctx = super(BaseLocationView, self).get_context_data(**kwargs)

        loc_id = int(kwargs['loc_id'])
        try:
            self.location = location = Location.objects.select_related().get(id=loc_id)
        except Location.DoesNotExist:
            raise Http404(u'Избирательный округ не найден')

        # TODO: different query generators might be needed for different data types
        self.location_query = get_roles_query(location)

        signed_up_in_uik = False
        #if self.request.user.is_authenticated():
        #    voter_roles = Role.objects.filter(user=self.request.profile, type='voter').select_related('location')
        #    if voter_roles:
        #        signed_up_in_uik = voter_roles[0].location.is_uik()

        self.tabs = [
            #('map', u'Карта', reverse('location_map', args=[location.id]), '', 'locations/map.html'),
            ('wall', u'Комментарии: ', reverse('location_wall', args=[location.id]), 'locations/wall.html'),
            #('participants', u'Участники: %i' % self.info['participants']['count'], reverse('location_participants', args=[location.id]), 'locations/participants.html'),
            ('info', u'Информация', reverse('location_info', args=[location.id]), 'locations/info.html'),
        ]

        self.info = location.info(related=True)

        ctx.update(entity_tabs_view(self))
        ctx.update(breadcrumbs_context(location))

        ctx.update({
            'loc_id': kwargs['loc_id'],

            'signed_up_in_uik': signed_up_in_uik,

            'info': self.info,

            #'counters': get_roles_counters(location),

            'add_commission_member_form': CommissionMemberForm(),
            'become_web_observer_form': WebObserverForm(),
        })

        ctx.update(self.update_context())
        return ctx

class InfoView(BaseLocationView):
    tab = 'info'

    def update_context(self):
        return {'commission_members': CommissionMember.objects.filter(location=self.location)}

class WallView(BaseLocationView):
    tab = 'wall'

    def update_context(self):
        return {}

class ParticipantsView(BaseLocationView):
    def update_context(self):
        role_type = self.request.GET.get('type', '')
        if not role_type in ROLE_TYPES:
            role_type = ''

        role_queryset = Role.objects.filter(self.location_query)
        if role_type:
            role_queryset = role_queryset.filter(type=role_type)
            roles = role_queryset.order_by('user__username').select_related('user', 'organization')[:100]
            context = {'participants': roles}
        else:
            roles = role_queryset.order_by('user__username').select_related('user', 'organization')[:100]
            users = sorted(set(role.user for role in roles), key=lambda user: user.username.lower())
            context = {'users': users}

        context.update({
            'selected_role_type': role_type,
            'ROLE_CHOICES': ROLE_CHOICES,
        })
        return context

# TODO: mark links previously reported by user
class LinksView(BaseLocationView):
    def update_context(self):
        return {
            'view': 'locations/links.html',
            'links': list(Link.objects.filter(location=self.location)),
        }

class WebObserversView(BaseLocationView):
    def update_context(self):
        web_observers = WebObserver.objects.filter(location=self.location).select_related('user__user')
        web_observers_by_time = {}
        for web_observer in web_observers:
            for time in range(web_observer.start_time, web_observer.end_time):
                web_observers_by_time.setdefault(time, []).append(web_observer)

        times = []
        for time in range(7, 24):
            times.append({'start_time': time, 'web_observers': web_observers_by_time.get(time, [])})
            times[-1]['end_time'] = time+1 if time<23 else 0

        return {
            'view': 'locations/web_observers.html',
            'times': times,
        }

def location_supporters(request, loc_id):
    return HttpResponsePermanentRedirect(reverse('location_info', kwargs={'loc_id': loc_id}))

def get_subregions(request):
    if not request.is_ajax():
        return HttpResponse('[]')

    loc_id = request.GET.get('loc_id', '')

    if loc_id:
        try:
            location = Location.objects.get(id=int(loc_id))
        except ValueError, Location.DoesNotExist:
            return HttpResponse('[]')
    else:
        location = None

    return HttpResponse(json.dumps(subregion_list(location), ensure_ascii=False))

# TODO: restructure it and take only one parameter
def goto_location(request):
    tab = request.GET.get('tab', '')
    for name in ('uik', 'tik', 'region'):
        try:
            location_id = int(request.GET.get(name, ''))
        except ValueError:
            continue

        url = reverse('location_info', args=[location_id])
        if tab:
            url += '/' + tab
        return HttpResponseRedirect(url)

    return HttpResponseRedirect(reverse('main'))

def locations_data(request):
    """ level = 2, 3, 4 """
    coords = {}
    for name in ('x1', 'y1', 'x2', 'y2'):
        try:
            coords[name] = float(request.GET.get(name, ''))
        except ValueError:
            return HttpResponse('"error"')

    try:
        level = int(request.GET.get('level', ''))
    except ValueError:
        return HttpResponse('"error"')

    if level not in (2, 3, 4):
        return HttpResponse('"error"')

    queryset = Location.objects.filter(x_coord__gt=coords['x1'], x_coord__lt=coords['x2'],
            y_coord__gt=coords['y1'], y_coord__lt=coords['y2'])

    return get_locations_data(queryset, level)