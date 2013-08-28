from faq.models import Post
from django.contrib import admin

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'index')

admin.site.register(Post, PostAdmin)
