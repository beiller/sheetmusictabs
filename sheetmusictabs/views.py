from sheetmusictabs.models import Tabs, Comment
from django.http import Http404, HttpResponse
from django.shortcuts import render
import zlib


def tab_list(request):
    tabs = Tabs.objects.order_by('-id')[:5]
    for tab in tabs:
        if tab.tab is None :
            tab.tab = zlib.decompress(tab.gzip_tab)
    return render(request, 'tablist.html', {'tabs': tabs})


def tab_page(request, tab_id):
    try:
        tab_id = int(tab_id)
    except ValueError:
        raise Http404()

    tab = Tabs.objects.get(pk=tab_id)
    comments = Comment.objects.filter(tab_id=tab_id).filter(spam=0)
    if tab.tab is None :
        tab.tab = zlib.decompress(tab.gzip_tab)
    return render(request, 'tab.html', {'tab': tab, 'comments': comments})
