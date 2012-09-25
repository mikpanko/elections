# -*- coding:utf-8 -*-
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models

from elements.participants.models import EntityParticipant
from elements.models import BaseEntityManager, BaseEntityModel, ENTITIES_MODELS, \
        entity_class, HTMLField
from locations.models import Location

class ProfileManager(BaseEntityManager):
    def get_info(self, data, ids):
        # TODO: add info on non-profile entities followed by the user

        # Get contacts
        contacts = EntityParticipant.objects.participant_in('follower', ids, Profile)
        contacts_ids = set(c_id for id in ids for c_id in contacts[id]['ids'])
        contacts_by_id = Profile.objects.only('id', 'first_name', 'last_name', 'rating') \
                .in_bulk(contacts_ids)

        for id in ids:
            data[id]['contacts'] = {
                'count': contacts[id]['count'],
                'entities': [contacts_by_id[c_id].display_info() for c_id in contacts[id]['ids']],
            }

        # Get data for related entities
        participants_data = list(EntityParticipant.objects.filter(person__in=ids) \
                .values_list('content_type', 'entity_id', 'role', 'person'))

        # TODO: use ratings to sort entities

        """
        for entity_name in ('ideas', 'projects', 'questions'):
            model = ENTITIES_MODELS[entity_name]

            for id in ids:
                data[id][entity_name] = dict((role, {'ids': []}) for role in model.roles)

            model_ct_id = ContentType.objects.get_for_model(model).id
            for ct_id, e_id, role, id in filter(lambda p: p[0]==model_ct_id, participants_data):
                data[id][entity_name][role]['ids'].append(e_id)

            for id in ids:
                for role in model.roles:
                    data[id][entity_name][role]['count'] = len(data[id][entity_name][role]['ids'])
        """

    def get_related_info(self, data, ids):
        """
        for entity_name in ('ideas', 'tasks', 'projects', 'questions'):
            model = ENTITIES_MODELS[entity_name]

            entities_ids = set(e_id for id in ids for role in model.roles \
                    for e_id in data[id][entity_name][role]['ids'])
            entities_info = model.objects.info_for(entities_ids, related=False)

            for id in ids:
                for role in model.roles:
                    data[id][entity_name][role]['entities'] = [entities_info[e_id] \
                            for e_id in data[id][entity_name][role]['ids']]
        """
        pass

@entity_class(['locations', 'participants'])
class Profile(BaseEntityModel):
    user = models.OneToOneField(User)

    first_name = models.CharField(u'Имя', max_length=40, help_text=u'на русском языке')
    last_name = models.CharField(u'Фамилия', max_length=40, help_text=u'на русском языке')

    about = HTMLField(u'О себе', default='', blank=True)

    objects = ProfileManager()

    entity_name = 'participants'
    entity_title = u'Участники'
    cache_prefix = 'user_info/'
    editable_fields = ['first_name', 'last_name', 'about']

    roles = ['follower']

    follow_button = {
        'role': 'follower',
        'cancel_msg': u'Вы хотите удалить этого пользователя из списка контактов?',
        'cancel_btn': u'Удалить',
        'cancel_btn_long': u'Удалить из контактов',
        'confirm_msg': u'Вы хотите добавить этого пользователя в список контактов?',
        'confirm_btn': u'Добавить',
        'confirm_btn_long': u'Добавить в контакты',
    }

    def info_data(self):
        data = super(Profile, self).info_data()
        data['full_name'] = unicode(self)
        return data

    def display_info(self):
        res = {
            'id': self.id,
            'url': self.get_absolute_url(),
            'full_name': unicode(self),
        }
        return res

    def calc_rating(self):
        info = self.info()
        rating = 0

        if self.about:
            rating += 0.1

        # TODO: take into account provided comments and contacts

        return rating

    def has_contact(self, profile):
        return EntityParticipant.objects.is_participant(profile, self, 'follower')

    @models.permalink
    def get_absolute_url(self):
        return ('profile', [self.user_id])

    def __unicode__(self):
        return self.first_name + u' ' + self.last_name

def create_profile(sender, **kwargs):
    if kwargs.get('created', False):
        profile = Profile()
        profile.user = kwargs['instance']
        profile.save()

models.signals.post_save.connect(create_profile, sender=User)

class Message(models.Model):
    sender = models.ForeignKey(Profile, verbose_name=u'Отправитель', related_name='sent_messages')
    receiver = models.ForeignKey(Profile, verbose_name=u'Получатель', related_name='received_messages')
    title = models.CharField(u'Тема', max_length=100)
    body = models.TextField(u'Сообщение')
    show_email = models.BooleanField(u'Показать email получателю', default=True)
    time = models.DateTimeField(auto_now=True)

MEMBER_CHOICES = (
    ('chairman', u'Председатель'),
    ('vice', u'Заместитель председателя'),
    ('secretary', u'Секретарь'),
    ('prg', u'Член с правом решающего голоса'),
    ('psg', u'Член с правом совещательного голоса'),
    ('other', u'Другое'),
)

PARTY_CHOICES = (
    ('ER', u'Единая Россия'),
    ('KPRF', u'КПРФ'),
    ('LDPR', u'ЛДПР'),
    ('SR', u'Справедливая Россия'),
    ('Prohorov', u'Штаб Прохорова'),
    ('Yabloko', u'Яблоко'),
    ('other', u'Другое'),
)

class CommissionMember(models.Model):
    last_name = models.CharField(u'Фамилия', max_length=50)
    first_name = models.CharField(u'Имя', max_length=50)
    middle_name = models.CharField(u'Отчество', max_length=50, blank=True)
    role = models.CharField(u'Должность', max_length=100, choices=MEMBER_CHOICES)
    party = models.CharField(u'Кем выдвинут', max_length=100, choices=PARTY_CHOICES)
    job = models.CharField(u'Место работы', max_length=100, blank=True)

    user = models.ForeignKey(Profile)
    location = models.ForeignKey(Location)
    time = models.DateTimeField(auto_now=True)

class WebObserver(models.Model):
    start_time = models.IntegerField(u'Начало наблюдения', help_text=u'Местное время')
    end_time = models.IntegerField(u'Окончание наблюдения')
    capture_video = models.BooleanField(u'Будет ли производиться захват видео', default=False)
    url = models.URLField(u'Ссылка на видео', blank=True)

    user = models.ForeignKey(Profile)
    location = models.ForeignKey(Location)
    time = models.DateTimeField(auto_now=True)
