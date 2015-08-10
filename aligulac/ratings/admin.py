# {{{ Imports
from datetime import datetime

from django.contrib import admin
from django.contrib.admin import (
    AllValuesFieldListFilter,
    DateFieldListFilter,
)
from django.db.models import (
    Q,
    F,
)
from django import forms

from tastypie.models import ApiKey as TPApiKey

from ratings.models import (
    Alias,
    APIKey,
    Earnings,
    Event,
    EventAdjacency,
    Group,
    Match,
    Message,
    Period,
    Player,
    PreMatch,
    PreMatchGroup,
    Rating,
    Story,
)

from countries import transformations
# }}}

def player_country(p):
    try:
        return transformations.cca_to_cn(p.country)
    except:
        return ''
player_country.short_description = 'Country'

def player_team(p):
    try:
        return Group.objects.get(active=True, groupmembership__player=p, groupmembership__current=True)
    except:
        return ''
player_team.short_description = 'Team'

class MembersInline(admin.TabularInline):
    raw_id_fields = ('player',)
    model = Group.members.through

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "group":
            kwargs["queryset"] = Group.objects.order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class AliasesInline(admin.TabularInline):
    model = Alias
    fields = ['name']

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['type', 'message', 'params']

    def clean(self):
        params = {}
        for p in self.cleaned_data['params'].splitlines():
            l, _, r = p.partition(':')
            params[l.strip()] = r.strip()
        for key in ['race', 'racea', 'raceb']:
            if key in params and params[key] not in 'PTZRS':
                raise forms.ValidationError('Invalid parameters. Did you choose P, T, Z, R or S for race?')
        return self.cleaned_data

class MessagesInline(admin.StackedInline):
    model = Message
    fields = ['type', 'message', 'params']
    extra = 0
    form = MessageForm
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(MessagesInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'params':
            formfield.widget = forms.Textarea(attrs={'size': 15})
        return formfield

class EarningsInline(admin.TabularInline):
    model = Earnings

class StoriesForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['date', 'message', 'params']

    def clean(self):
        params = {}
        for p in self.cleaned_data['params'].splitlines():
            l, _, r = p.partition(':')
            params[l.strip()] = r.strip()
        for key in ['race', 'racea', 'raceb']:
            if key in params and params[key] not in 'PTZRS':
                raise forms.ValidationError('Invalid parameters. Did you choose P, T, Z, R or S for race?')
        return self.cleaned_data

class StoriesInline(admin.StackedInline):
    extra = 0
    model = Story
    fields = ['date', 'message', 'params']
    form = StoriesForm
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(StoriesInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'params':
            formfield.widget = forms.Textarea(attrs={'size': 15})
        return formfield

class PlayerAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,          {'fields': ['tag','race']}),
        ('Optional',    {'fields': ['name','romanized_name','birthday','country']}),
        ('External',    {'fields': ['tlpd_id','lp_name','sc2e_id']})
    ]
    inlines = [MembersInline, AliasesInline, StoriesInline, MessagesInline]
    search_fields = ['tag']
    list_display = ('tag', 'race', player_team, player_country, 'name')

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'shortname', 'is_team', 'is_manual', 'active')
    fields = ['name', 'shortname', 'founded', 'disbanded', 'lp_name', 'homepage', 'active',
              'is_team', 'is_manual']
    inlines = [MembersInline, AliasesInline, MessagesInline]
    search_fields = ['name']

def match_period(m):
    return str(m.period.id)
match_period.short_description = 'Period'

class MatchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MatchForm, self).__init__(*args, **kwargs)
        ids = Event.objects.filter(closed=False).exclude(downlink__distance__gt=0)
        q = Q(id__in=ids)
        if self.instance.eventobj != None:
            q = q | Q(id=self.instance.eventobj.id)
        self.fields['eventobj'].queryset = Event.objects.filter(q).order_by('fullname')

    def commit(self, request):
        super().commit(request)

        self.cleaned_data['period'].update(needs_recompute=True)

def match_delete_wrapper(f):
    def wrapper(self, request, objlist):
        result = f(self, request, objlist)
        for obj in objlist:
            obj.period.needs_recompute = True
            obj.period.save()
        return result
    return wrapper

class MatchAdmin(admin.ModelAdmin):
    list_display = ('date', 'get_res', match_period, 'treated', 'offline', 'game', 'eventobj', 'submitter')
    inlines = [MessagesInline]
    exclude = ('rta', 'rtb', 'period')
    list_filter = [
        ('date', DateFieldListFilter),
        ('game', AllValuesFieldListFilter),
    ]
    raw_id_fields = ('pla', 'plb')
    form = MatchForm

    def get_actions(self, request):
        actions = super().get_actions(request)

        if 'delete_selected' in actions:
            fun, name, desc = actions['delete_selected']
            actions['delete_selected'] = (match_delete_wrapper(fun), name, desc)

        return actions

    def get_res(self, obj):
        return '%s %i-%i %s' % (str(obj.pla), obj.sca, obj.scb, str(obj.plb))
    get_res.short_description = 'Result'

    def has_add_permission(self, request):
        return False

class PeriodAdmin(admin.ModelAdmin):
    list_display = ('id', 'start', 'end', 'computed', 'needs_recompute')
    list_filter = ('computed', 'needs_recompute')

    actions = ['recompute']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def get_queryset(self, request):
        return Period.objects.filter(start__lte=datetime.today())

    def get_actions(self, request):
        actions = super().get_actions(request)

        if 'delete_selected' in actions:
            del actions['delete_selected']

        return actions

    def has_add_permission(self, request):
        return False

    def recompute(self, request, queryset):
        queryset.update(needs_recompute=True)
    recompute.short_description = "Recompute selected"

class EventAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'closed', 'big', 'noprint', 'type',)
    inlines = [MessagesInline]
    exclude = ('lft', 'rgt', 'idx', 'tlpd_db')
    readonly_fields = (
        'parent', 'prizepool', 'earliest', 'latest', 'type', 'name', 'fullname', 'idx')
    search_fields = ['fullname']
    actions = ['open_event_action', 'close_event_action']


    def open_event_action(self, request, queryset):
        count = 0
        for event in queryset:
            objects = EventAdjacency.objects.filter(child=event, parent__closed=True).select_related()
            for rel in objects:
                rel.parent.closed = False
                rel.parent.save()
                count += 1
        self.message_user(request, "Successfully opened {} event{}.".format(count, "" if count == 1 else "s"))

    open_event_action.short_description = "Open event supertree"

    def close_event_action(self, request, queryset):
        count = 0
        for event in queryset:
            objects = EventAdjacency.objects.filter(parent=event, child__closed=False).select_related()
            for rel in objects:
                closed = rel.child.closed
                rel.child.closed = True
                rel.child.save()
                if not closed:
                    count += 1
        self.message_user(request, "Successfully closed {} event{}.".format(count, "" if count == 1 else "s"))

    close_event_action.short_description = "Close event subtree"

    def has_add_permission(self, request):
        return False

class PreMatchGroupAdmin(admin.ModelAdmin):
    list_display = ('date', 'event')

    def has_add_permission(self, request):
        return False

class PreMatchAdmin(admin.ModelAdmin):
    list_display = ('date', 'get_res', 'get_event')
    readonly_fields = ('group',)

    def has_add_permission(self, request):
        return False

    def get_res(self, obj):
        s = obj.pla_string if obj.pla is None else str(obj.pla)
        s += ' %i-%i ' % (obj.sca, obj.scb)
        s += obj.plb_string if obj.plb is None else str(obj.plb)
        return s
    get_res.short_description = 'Result'

    def get_event(self, obj):
        return obj.group.event
    get_event.short_description = 'Event'

class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('date_opened', 'organization', 'contact', 'requests')
    readonly_fields = ('date_opened', 'key', 'requests')

    def has_add_permission(self, request):
        return False

admin.site.register(Player, PlayerAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(PreMatchGroup, PreMatchGroupAdmin)
admin.site.register(PreMatch, PreMatchAdmin)
admin.site.register(APIKey, APIKeyAdmin)

admin.site.unregister(TPApiKey)
