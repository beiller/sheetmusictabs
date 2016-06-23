import difflib
import json
from django.db.models import F
from django.template.defaultfilters import striptags, register
from sheetmusictabs.models import Tabs, Comment, TabsFulltext, BandInfo, ExtendedInfo
from django.http import Http404, JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
import zlib
import settings
import re
from django import forms
from captcha.fields import ReCaptchaField
from django.core import serializers


class CommentForm(forms.Form):
    name = forms.CharField(max_length=20, required=True)
    email = forms.EmailField(max_length=50, required=True)
    website = forms.URLField(max_length=50, required=False)
    comment = forms.CharField(max_length=250, required=True)
    captcha = ReCaptchaField()


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


def tab_list(request):
    latest_tabs = Tabs.objects.defer("tab", "gzip_tab").order_by('-id')[:25]
    discussed_tabs = Comment.objects.filter(spam=0).select_related().order_by('-id')[:10]
    highest_rated = Tabs.objects.defer("tab", "gzip_tab").filter(vote_yes__gt=F('vote_no')).filter(vote_yes__gte=5)[:10]
    most_viewed = Tabs.objects.defer("tab", "gzip_tab").order_by('-hit_count')[:10]

    return render(request, 'tablist.html', {
        'latest_tabs': latest_tabs,
        'discussed_tabs': discussed_tabs,
        'highest_rated': highest_rated,
        'most_viewed': most_viewed,
        'site_globals': settings.SITE_GLOBALS
    })


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
    text_output = []
    chord_expression = (
        '(([A-G])([#b])?\s?(5|6|7|maj7|9|maj9|11|13|maj13|min6|min7|'
        'min9|min11|min13|sus2|sus4|dim|aug|6/9|7sus4|7b5|7b9|9sus4|add9|aug9|min|maj|m|dim)?)'
    )
    text_input = text_input.replace("\r\nfcf\r\n", '').replace('\r\n1000\r\n', '')
    for line in text_input.split("\n"):
        likely_contains_notes = len(re.findall("[A-G]([#b]|(m|maj|min)|[5679])", line)) > 0
        likely_contains_notes = likely_contains_notes or re.match("^[A-G\s]+$", line) is not None
        if not likely_contains_notes:
            text_output.append(line)
        else:
            text_output.append(
                re.sub(
                    chord_expression,
                    r"""<a href="#" class="show_diagram_link">\g<0></a>""",
                    line
                )
            )
    return "\n".join(text_output)


def detect_spam_by_ip(ip_address):
    return len(Comment.objects.filter(ip=ip_address)[:20]) > 10


def detect_spam_by_content(content):
    try:
        content.decode('ascii')
    except UnicodeDecodeError:
        return True
    to_test = content.lower()
    words = ['ugg', 'http', 'href', 'viagra', 'preteen', 'online', 'cialis', 'pharmacy', 'prescription', 'lolita', 'nude', 'url', 'buy']
    for word in words:
        if word in to_test:
            return True
    return False


@register.filter(name='info_split')
def info_split(value):
    return value.split(',')


def inject_adsense(tab, ad_code, insert_after=3):
    """
    This function will inject adsense ad in between lines
    of the tab. Returns the string

    Keyword arguments:
    tab -- string representing the tab
    """
    occur = 0
    output = ''
    done = False
    for line in tab.split('\n'):
        if done is False and line.strip() == '':
            occur += 1

        if done is False and occur > insert_after:
            output += ad_code + "\n"
            done = True
        output += line + "\n"
    return output


def band_letter_page(request, band_letter):
    bands = Tabs.objects.raw("""
        SELECT DISTINCT tabs.id, tabs.band
        FROM tabs
        WHERE tabs.band LIKE %s
    """, band_letter + "%")
    data = []
    band_set = set()
    for band in bands:
        if band.band not in band_set:
            band_set.add(band.band)
            data.append({'url': '/bands/'+band_letter+'/'+band.band.replace(' ', '+')+'/', 'band': band.band})

    return render(request, 'bands_by_letter.html', {
        'band_letter': band_letter,
        'bands': data,
        'site_globals': settings.SITE_GLOBALS
    })


def comment_moderation_page(request):
    comments = Comment.objects.filter(spam=0).order_by('-id')[:5000]

    return render(request, 'comment_moderation.html', {
        'comments': comments,
        'site_globals': settings.SITE_GLOBALS
    })


def band_page(request, band_name):
    band_name = band_name.replace('+', ' ')
    bands = Tabs.objects.raw("""
        SELECT DISTINCT tabs.id, tabs.band, tabs.name
        FROM tabs
        WHERE tabs.band LIKE %s
    """, band_name)

    return render(request, 'band_page.html', {
        'band_name': band_name,
        'bands': bands,
        'site_globals': settings.SITE_GLOBALS
    })


def tab_data(tab_id):
    tab = Tabs.objects.get(pk=tab_id)
    tab.hit_count += 1
    tab.save()
    comments = Comment.objects.filter(tab_id=tab_id).filter(spam=0)
    band_info = BandInfo.objects.filter(band_name=tab.band).first()

    if tab.tab is None:
        tab.tab = zlib.decompress(tab.gzip_tab)
    #tab.chords = parse_chords_list(tab.tab)
    tab.band = re.sub(' tabs$', '', tab.band, re.IGNORECASE)
    tab.name = re.sub('\s+(Tab|Tabs|Chord|Chords)$', '', tab.name, re.IGNORECASE)
    tab.tab = annotate_chords(striptags(tab.tab))
    ad_code = """
<ins class="adsbygoogle"
     style="display:inline-block;width:468px;height:15px"
     data-ad-client="ca-pub-9811013802250997"
     data-ad-slot="8553994049"></ins>
<script>
(adsbygoogle = window.adsbygoogle || []).push({});
</script>
    """
    tab.tab = inject_adsense(tab.tab, ad_code, insert_after=1)
    tab.tab = inject_adsense(tab.tab, ad_code, insert_after=6)
    tab.tab = tab.tab.strip()

    suggested_tabs_search = tab.name + ' ' + tab.band
    suggested_tabs = Tabs.objects.raw("""
        SELECT tabs.*
        FROM tabs_fulltext
        JOIN tabs ON tabs.id = tabs_fulltext.id
        WHERE match (tabs_fulltext.name, tabs_fulltext.band) AGAINST ( %s ) AND tabs.id != %s LIMIT 20
    """, [suggested_tabs_search, tab.id])

    ei = ExtendedInfo.objects.filter(tab=tab.id)
    extended_info = None
    if ei:
        try:
            extended_info = json.loads(ei.first().info)
            if extended_info is not None and extended_info['albums'] is not None and len(extended_info['albums']) > 3:
                extended_info['albums'] = extended_info['albums'][0:3]
        except TypeError:
            pass

    return {
        'tab': tab,
        'suggested_tabs': suggested_tabs,
        'comments': comments,
        'band_info': band_info,
        'extended_info': extended_info,
        'site_globals': settings.SITE_GLOBALS
    }


def vote_tab(request):
    if request.method == 'POST' and 'method' in request.POST and request.POST['method'] == 'vote':
        tab = Tabs.objects.get(id=request.POST['tabid'])
        if request.POST['submit'] == 'votedown':
            tab.vote_no += 1
            tab.save()
        elif request.POST['submit'] == 'voteup':
            tab.vote_yes += 1
            tab.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


def add_comment(request):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            is_spam = detect_spam_by_ip(request.META.get('REMOTE_ADDR'))
            if detect_spam_by_content(form.cleaned_data['comment']):
                is_spam = True
            if not is_spam:
                c = Comment(
                    name=form.cleaned_data['name'],
                    ip=request.META.get('REMOTE_ADDR'),
                    comment=form.cleaned_data['comment'],
                    tab_id=form.cleaned_data['tabid'],
                    spam=0
                )
                c.save()
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})


def tab_page(request, tab_id):
    try:
        tab_id = int(tab_id)
    except ValueError:
        raise Http404()

    form = CommentForm()
    scroll_to = False
    if request.method == 'POST' and 'method' in request.POST and request.POST['method'] == 'vote':
        tab = Tabs.objects.get(id=request.POST['tabid'])
        if request.POST['submit'] == 'votedown':
            tab.vote_no += 1
            tab.save()
        elif request.POST['submit'] == 'voteup':
            tab.vote_yes += 1
            tab.save()
            return JsonResponse({'success': True})
    elif request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            is_spam = detect_spam_by_ip(request.META.get('REMOTE_ADDR'))
            if detect_spam_by_content(form.cleaned_data['comment']):
                is_spam = True
            if not is_spam:
                c = Comment(
                    name=form.cleaned_data['name'],
                    ip=request.META.get('REMOTE_ADDR'),
                    comment=form.cleaned_data['comment'],
                    tab_id=tab_id,
                    spam=0
                )
                c.save()
                scroll_to = '$(document).height()'
        else:
            scroll_to = '$("#errors").offset().top'
    data = tab_data(tab_id)
    data['comments_form'] = form
    data['scroll_to'] = scroll_to
    return render(request, 'tab.html', data)


def tab_page_json(request, tab_id):
    def jsonify_url(url):
        return """javascript:loadTemplate('./mobile_tab.html', '%s')""" % url.replace('.html', '.json')
    database_data = tab_data(tab_id)
    form = CommentForm()
    return_data = {
        'tab': {
            'id': database_data['tab'].id,
            'name': database_data['tab'].name,
            'band': database_data['tab'].band,
            'tab': database_data['tab'].tab,
            'hit_count': database_data['tab'].hit_count,
            'vote_yes': database_data['tab'].vote_yes,
            'vote_no': database_data['tab'].vote_no
        },
        'suggested_tabs': [{'id': t.id, 'name': t.name, 'band': t.band, 'url': jsonify_url(t.url), 'vote_yes': t.vote_yes, 'vote_no': t.vote_no} for t in database_data['suggested_tabs']],
        'comments': [{'id': t.id, 'tab': t.tab, 'name': t.name, 'comment': t.comment, 'spam': t.spam} for t in database_data['comments']],
        'band_info': {
            'band_name': database_data['band_info'].band_name,
            'genres': database_data['band_info'].genres,
            'origin': database_data['band_info'].origin,
            'years_active': database_data['band_info'].years_active,
            'members': database_data['band_info'].members
        },
        'extended_info': database_data['extended_info'],
        'comments_form': {'captcha': form.captcha, 'name': form.name.value, 'email': form.email.value, 'website': form.website.value, 'comment': form.comment.value}
    }
    return JsonResponse(return_data, content_type='application/json; encoding=utf-8', safe=False)


def similar(seq1, seq2):
    return difflib.SequenceMatcher(a=seq1.lower(), b=seq2.lower()).ratio()


def filter_search_results(tabs, search_string):
    match_map = []
    for tab in tabs:
        score = similar(tab.name, search_string) + similar(tab.band, search_string)
        if search_string in tab.name.lower():
            score += 1
        if search_string in tab.band.lower():
            score += 1
        match_map.append((score, tab))
    return sorted(match_map, key=lambda t: t[0], reverse=True)[:15]   # sort by score

SITEMAP_SIZE = 10000


def sitemap_index(request):
    #tlist = Tabs.objects.defer("tab").defer("gzip_tab").order_by('-id')[:49990]
    tcount = Tabs.objects.count()
    num_sitemaps = tcount / SITEMAP_SIZE
    urls = []
    for i in range(num_sitemaps):
        urls.append('https://www.sheet-music-tabs.com/sitemap%s.xml' % (i+1))

    return render(
        request,
        'sitemap_index.xml',
        {'urls': urls},
        content_type="text/xml"
    )


def sitemap(request, pagenum):
    tlist = Tabs.objects.defer("tab").defer("gzip_tab").order_by('-id')[(int(pagenum)-1)*SITEMAP_SIZE:int(pagenum)*SITEMAP_SIZE]
    return render(
        request,
        'sitemap.xml',
        {'urls': [t.url for t in tlist]},
        content_type="text/xml"
    )


def search(request):
    search_string = request.GET.get('q')


    #tabs = TabsFulltext.objects.filter(Q(name__search="+"+search_string) | Q(band__search="+"+search_string))[:20]
    tabs = TabsFulltext.objects.raw("""
        SELECT tabs.id, tabs.name, tabs.band
        FROM tabs_fulltext
        JOIN tabs ON tabs.id = tabs_fulltext.id
        WHERE
            MATCH(tabs_fulltext.band, tabs_fulltext.name) AGAINST ( %s IN BOOLEAN MODE )

    """, [search_string + '*'])
    tabs = filter_search_results(tabs, search_string)
    response = []
    for t in tabs:
        response.append({'name': t[1].name, 'band': t[1].band, 'url': url_from_tab(t[1]), 'score': t[0]})
    return JsonResponse(response, safe=False)
