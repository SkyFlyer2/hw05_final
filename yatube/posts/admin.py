from django.contrib import admin
from .models import Post, Group, Comment, Follow


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group',)
    list_editable = ('group',)
    search_fields = ('text', 'group',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'slug', 'description',)
    list_editable = ('title', 'slug', 'description',)
    search_fields = ('title', 'slug',)
    list_filter = ('slug',)
    empty_value_display = '-пусто-'


class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'post', 'author', 'text',)
    list_editable = ('text',)
    search_fields = ('post', 'author', 'text',)
    list_filter = ('author',)
    empty_value_display = '-пусто-'


class FollowAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'author',)
    list_editable = ('user', 'author')
    search_fields = ('user', 'author',)
    list_filter = ('user',)


admin.site.register(Post, PostAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
