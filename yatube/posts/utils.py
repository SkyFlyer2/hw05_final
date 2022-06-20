from django.core.paginator import Paginator
from django.conf import settings


def page_list(post_list, request):
    paginator = Paginator(post_list, settings.COUNT_INDEX_POSTS)
    return paginator.get_page(request.GET.get('page'))
