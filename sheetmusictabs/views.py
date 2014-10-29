from sheetmusictabs.models import Tabs
from django.http import Http404, HttpResponse
from django.shortcuts import render
import zlib


def tab_list(request):
    tabs = Tabs.objects.order_by('id')[:5]
    for tab in tabs:
        if tab.tab == None :
            tab.tab = zlib.decompress(tab.gzip_tab)
    return render(request, 'tablist.html', {'tabs': tabs})


def tab_page(request, tabid):
    try:
        pkid = int(tabid)
    except ValueError:
        raise Http404()

    tabs = [Tabs.objects.get(pk=pkid), ]
    for tab in tabs:
        if tab.tab == None :
            tab.tab = zlib.decompress(tab.gzip_tab)
    return render(request, 'tablist.html', {'tabs': tabs})
