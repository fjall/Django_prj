from django.core.paginator import Paginator


def get_paginator(queryset, items_count, request):
    paginator = Paginator(queryset, items_count)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
