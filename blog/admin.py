from django.contrib import admin
from .models import *
# Register your models here.


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'posted')

    change_form_template = 'admin_post_change.html'


class PostImageAdmin(admin.ModelAdmin):
    list_display = ('title',)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author')
        
admin.site.register(Post, PostAdmin)
admin.site.register(PostImage, PostImageAdmin)
admin.site.register(Comment, CommentAdmin)