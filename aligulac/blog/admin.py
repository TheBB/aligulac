from blog.models import Post
from django.contrib import admin

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date')

admin.site.register(Post, PostAdmin)
