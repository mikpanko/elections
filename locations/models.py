# -*- coding:utf-8 -*-
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models
from django.db.models import Q

from elements.models import ENTITIES_MODELS, FEATURES_MODELS
from services.cache import cache_function

# Url templates for pages on izbirkom.ru with information about comissions
RESULTS_ROOT_URL = r'http://www.%(region_name)s.vybory.izbirkom.ru/region/%(region_name)s?action=show&global=1&vrn=100100031793505&region=%(region_code)d&prver=0&pronetvd=null'
RESULTS_URL = r'http://www.%(region_name)s.vybory.izbirkom.ru/region/region/%(region_name)s?action=show&root=%(root)d&tvd=%(tvd)d&vrn=100100031793505&region=%(region_code)d&global=true&sub_region=%(region_code)d&prver=0&pronetvd=null&vibid=%(tvd)d&type=226'

INFO_URL = r'http://www.%(region_name)s.vybory.izbirkom.ru/region/%(region_name)s?action=show_komissia&region=%(region_code)d&sub_region=%(region_code)d&type=100&vrnorg=%(vrnorg)d&vrnkomis=%(vrnkomis)d'

class LocationManager(models.Manager):
    @cache_function('location/country', 1000)
    def country(self):
        return self.get(country=None)

    def info_for(self, ids, related=True):
        """
        Return {id: {'location': location, entities_keys: entities_data}}.
        If related is True, return list of entities data, otherwise - only ids.
        """
        cache_prefix = self.model.cache_prefix
        cached_locations = cache.get_many([cache_prefix+str(id) for id in ids])

        cached_ids = []
        res = {}
        for key, entity in cached_locations.iteritems():
            id = int(key[len(cache_prefix):])
            cached_ids.append(id)
            res[id] = entity

        other_ids = set(ids) - set(cached_ids)
        if len(other_ids) > 0:
            other_res = dict((id, {}) for id in other_ids)

            comments_data = FEATURES_MODELS['comments'].objects.get_for(Location, other_ids)

            ct_id = ContentType.objects.get_for_model(self.model).id
            locations = self.filter(id__in=other_ids).select_related()
            participants_ids = []
            for loc in locations:
                # TODO: instance is a dict in all entities
                other_res[loc.id] = {'instance': loc, 'ct': ct_id}

                # TODO: do we need tools data here?
                for name, model in ENTITIES_MODELS.iteritems():
                    if name == 'participants':
                        continue

                    other_res[loc.id][name] = loc.get_entities(name)(
                            limit=settings.LIST_COUNT['tools'])

                # Get participants
                participants_data = loc.get_entities('participants')(limit=settings.LIST_COUNT['participants'])
                participants_ids += participants_data['ids']
                other_res[loc.id]['participants'] = {
                    'count': participants_data['count'],
                    'entities': [{'id': id} for id in participants_data['ids']],
                }

                # Comments
                other_res[loc.id]['comments'] = comments_data[loc.id]

            profiles_by_id = ENTITIES_MODELS['participants'].objects.only('id', 'first_name', 'last_name', 'intro', 'rating') \
                    .in_bulk(set(participants_ids))

            for loc in locations:
                for entity in other_res[loc.id]['participants']['entities']:
                    entity.update(profiles_by_id[entity['id']].display_info())

            res.update(other_res)

            cache_res = dict((cache_prefix+str(id), other_res[id]) for id in other_res)
            cache.set_many(cache_res, 60) # TODO: specify time outside of this method

        if related:
            for name, model in ENTITIES_MODELS.iteritems():
                if name == 'participants':
                        continue

                e_ids = set(e_id for id in ids for e_id in res[id][name]['ids'])
                e_info = model.objects.info_for(e_ids, related=False)

                for id in ids:
                    res[id][name]['entities'] = [e_info[e_id] for e_id in res[id][name]['ids']
                            if e_id in e_info]

        return res

# TODO: add foreign uiks (in other countries)
class Location(models.Model):
    """ The number of non-null values of parent specifies the level of location """
    # keys to the parents of the corresponding level (if present)
    country = models.ForeignKey('self', null=True, blank=True, related_name='country_related')
    region = models.ForeignKey('self', null=True, blank=True, related_name='in_region')
    tik = models.ForeignKey('self', null=True, blank=True, related_name='in_tik')

    name = models.CharField(max_length=150, db_index=True)
    region_name = models.CharField(max_length=20)
    region_code = models.IntegerField()

    postcode = models.IntegerField(blank=True, null=True)
    address = models.CharField(max_length=200, blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=40, blank=True)

    # Ids required to access data from izbirkom.ru
    tvd = models.BigIntegerField()
    root = models.IntegerField()
    vrnorg = models.BigIntegerField(blank=True, null=True)
    vrnkomis = models.BigIntegerField(blank=True, null=True)

    # Coordinates used in Yandex maps
    x_coord = models.FloatField(blank=True, null=True, db_index=True)
    y_coord = models.FloatField(blank=True, null=True, db_index=True)

    data = models.TextField() # keeps counters for cik data and users

    #participants = generic.GenericRelation('participants.EntityParticipant', object_id_field='entity_id')

    objects = LocationManager()

    cache_prefix = 'location_info'

    # A hack to implement participants and comments
    features = ['participants', 'comments']
    roles = ['follower']

    def level(self):
        if self.region_id is None:
            return 2
        elif self.tik_id is None:
            return 3
        else:
            return 4

    def is_country(self):
        return self.country_id is None

    def is_region(self):
        return self.country_id is not None and self.region_id is None

    def is_tik(self):
        return self.region_id is not None and self.tik_id is None

    def is_uik(self):
        return self.tik_id is not None

    def results_url(self):
        """ Link to the page with elections results on izbirkom.ru """
        data = {'region_name': self.region_name, 'region_code': self.region_code}
        if self.tvd != 0:
            data.update({'tvd': self.tvd, 'root': self.root})
            return RESULTS_URL % data
        else:
            return RESULTS_ROOT_URL % data

    def info_url(self):
        """ Link to the page with commission information on izbirkom.ru """
        if self.vrnorg is None:
            return ''

        return INFO_URL % {'region_name': self.region_name, 'region_code': self.region_code,
                'vrnorg': self.vrnorg, 'vrnkomis': self.vrnkomis}

    def path(self):
        # using int() is a hack for mysql to avoid using long int
        if not self.region_id:
            return [int(self.id)]
        elif not self.tik_id:
            return [int(self.region_id), int(self.id)]
        else:
            return [int(self.region_id), int(self.tik_id), int(self.id)]

    def map_data(self):
        """ Return javascript object containing region data """
        js = 'new ElectionCommission(' + str(self.id) + ',' + str(self.level()) + ','
        # TODO: name, address require escape
        js += '"' + self.name + '","' + self.name + '","' + self.address.replace('"', '') + '",'
        js += str(self.x_coord) + ',' + str(self.y_coord) + ','+self.data+')'
        return js

    def __unicode__(self, full_path=False):
        name = self.name
        if self.is_uik():
            name = u'УИК № ' + name

        if full_path:
            if self.tik:
                name = str(self.tik) + u'->' + name
            if self.region:
                name = str(self.region) + u'->' + name
        return name

    def info(self, related=True):
        return Location.objects.info_for([self.id], related)[self.id]

    def cache_key(self):
        return self.cache_prefix + str(self.id)

    def clear_cache(self):
        cache.delete(self.cache_key())

    # TODO: cache count separately?
    # TODO: take is_main into account
    # TODO: cache it (at least for data for side panels) - in Location
    def get_entities(self, entity_type, qfilter=None):
        """ Return {'ids': sorted_entities_ids, 'count': total_count} """
        from elements.locations.models import EntityLocation
        model = ENTITIES_MODELS[entity_type]

        def method(start=0, limit=None, sort_by=('-rating',)):
            entity_query = Q()

            # Filter out unactivated accounts
            # TODO: make queryset a parameter of entity model (?)
            if model.entity_name == 'participants':
                entity_query = Q(user__is_active=True)

            if not self.is_country(): # used to speed up processing
                loc_query = Q(location__id=self.id)

                field = self.children_query_field()
                if field:
                    loc_query |= Q(**{'location__'+field: self.id})

                entity_ids = set(EntityLocation.objects.filter(
                        content_type=ContentType.objects.get_for_model(model)) \
                        .filter(loc_query).values_list('entity_id', flat=True))

                # TODO: what happens when the list of ids is too long (for the next query)? - use subqueries
                entity_query &= Q(id__in=entity_ids)

            if qfilter:
                entity_query &= qfilter

            ids = model.objects.filter(entity_query).order_by(*sort_by).values_list('id', flat=True)
            return {
                'count': ids.count(),
                'ids': ids[slice(start, start+limit if limit else None)],
            }

        return method

    @models.permalink
    def get_absolute_url(self):
        return ('location_info', (), {'loc_id': str(self.id)})