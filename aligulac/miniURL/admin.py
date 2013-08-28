from django.contrib import admin
from miniURL.models import MiniURL
 
class MiniURLAdmin(admin.ModelAdmin):
    list_display   = ('longURL', 'code', 'date', 'submitter','nb_access')
    list_filter    = ('submitter',)
    date_hierarchy = 'date'
    ordering       = ('date',)
    search_fields  = ('longURL',)
 
admin.site.register(MiniURL, MiniURLAdmin)
