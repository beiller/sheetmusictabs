from django.template.defaultfilters import striptags
from sheetmusictabs.models import Tabs, Comment, TabsFulltext
from django.http import Http404, HttpResponse, JsonResponse
from django.db.models import Q
from urllib import urlencode
from django.shortcuts import render
import zlib
import settings
import re


def tab_list(request):
    tabs = Tabs.objects.order_by('-id')[:5]
    for tab in tabs:
        if tab.tab is None :
            tab.tab = zlib.decompress(tab.gzip_tab)
    return render(request, 'tablist.html', {'tabs': tabs, 'site_globals': settings.SITE_GLOBALS})


def parse_chords_list(text_input):
    chord_expression = (
        '\s([a-g])([#b])?\s?(min|maj|m|dim|5|6|7|maj7|9|maj9|11|13|maj13|min6|min7|'
        'min9|min11|min13|sus2|sus4|dim|aug|6/9|7sus4|7b5|7b9|9sus4|add9|aug9)?\s'
    )
    result = re.findall(chord_expression, text_input, re.IGNORECASE)
    chords = set()
    for line in result:
        if len(line) == 3:
            #format chord
            modifier = line[2]
            if modifier == 'm':
                modifier = 'min'
            chord = (line[0].upper() + line[1] + " " + modifier.lower()).strip()
            chords.add(chord)
    return chords


def annotate_chords(text_input):
    chord_expression = (
        '(\s)(([a-g])([#b])?\s?(min|maj|m|dim|5|6|7|maj7|9|maj9|11|13|maj13|min6|min7|'
        'min9|min11|min13|sus2|sus4|dim|aug|6/9|7sus4|7b5|7b9|9sus4|add9|aug9)?)'
        '(,|\s\s)'
    )
    return re.sub(
        chord_expression,
        r"""\g<1><a href="#" class="show_diagram_link">\g<2></a>\g<6>""",
        text_input,
        count=0,
        flags=re.IGNORECASE
    )


def tab_page(request, tab_id):
    try:
        tab_id = int(tab_id)
    except ValueError:
        raise Http404()

    tab = Tabs.objects.get(pk=tab_id)
    comments = Comment.objects.filter(tab_id=tab_id).filter(spam=0)
    if tab.tab is None:
        tab.tab = zlib.decompress(tab.gzip_tab)
    #tab.chords = parse_chords_list(tab.tab)
    tab.band = re.sub(' tabs$', '', tab.band, re.IGNORECASE)
    tab.name = re.sub('\s+(Tab|Tabs|Chord|Chords)$', '', tab.name, re.IGNORECASE)
    tab.tab = annotate_chords(striptags(tab.tab))

    return render(request, 'tab.html', {
        'tab': tab,
        'comments': comments,
        'site_globals': settings.SITE_GLOBALS
    })


def url_from_id(tab_id):
    tab = Tabs.objects.get(pk=tab_id)
    if tab is not None:
        return url_from_tab(tab)
    else:
        return None


def url_from_tab(tab):
    url = '/bands/' + tab.band[0].upper() + '/'
    url += tab.band.replace(' ', '+')
    url += '/' + str(tab.id) + '/'
    url += tab.name.replace(' ', '+') + '.html'
    return url


def search(request):
    search_string = request.GET.get('q')

    #tabs = TabsFulltext.objects.filter(Q(name__search="+"+search_string) | Q(band__search="+"+search_string))[:20]
    tabs = TabsFulltext.objects.raw("""
        SELECT tabs.id, tabs.name, tabs.band
        FROM tabs_fulltext
        JOIN tabs ON tabs.id = tabs_fulltext.id
        WHERE match (tabs_fulltext.name,tabs_fulltext.band) against (%s) LIMIT 20
    """, [search_string])
    response = {}
    for tab in tabs:
        response[tab.id] = {'name': tab.name, 'band': tab.band, 'url': url_from_tab(tab)}
    return JsonResponse(response)
