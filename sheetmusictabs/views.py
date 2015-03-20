import difflib
from django.template.defaultfilters import striptags, register
from sheetmusictabs.models import Tabs, Comment, TabsFulltext, BandInfo
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
import zlib
import settings
import re
from django import forms


class CommentForm(forms.Form):
    name = forms.CharField(max_length=20, required=True)
    email = forms.EmailField(max_length=50, required=True)
    website = forms.URLField(max_length=50, required=False)
    comment = forms.CharField(max_length=250, required=True)


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
    template_data = {
        "latest_tabs": [],
        "latest_comments": []
    }
    tabs = Tabs.objects.order_by('-id')[:10]
    for tab in tabs:
        template_data["latest_tabs"].append({
            "url": url_from_tab(tab),
            "name": tab.name,
            "band": tab.band
        })

    discussed = Comment.objects.filter(spam=0).select_related()[:10]
    for tab in discussed:
        template_data["latest_comments"].append({
            "url": url_from_tab(tab.tab),
            "name": tab.tab.name,
            "band": tab.tab.band
        })

    return render(request, 'tablist.html', {'tabs': template_data, 'site_globals': settings.SITE_GLOBALS})


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
    return len(Comment.objects.filter(ip=ip_address).filter(spam=1)[:3]) > 3


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


def tab_page(request, tab_id):
    #TODO vote up/down?
    #TODO add to hit counter?

    try:
        tab_id = int(tab_id)
    except ValueError:
        raise Http404()

    form = CommentForm()
    scroll_to = False
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            is_spam = detect_spam_by_ip(request.META.get('REMOTE_ADDR'))
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


    tab = Tabs.objects.get(pk=tab_id)
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
    suggested_tabs = TabsFulltext.objects.raw("""
        SELECT tabs.id, tabs.name, tabs.band
        FROM tabs_fulltext
        JOIN tabs ON tabs.id = tabs_fulltext.id
        WHERE match (tabs_fulltext.name, tabs_fulltext.band) AGAINST ( %s ) LIMIT 10
    """, [suggested_tabs_search])
    for suggested_tab in suggested_tabs:
        suggested_tab.url = url_from_tab(suggested_tab)

    return render(request, 'tab.html', {
        'tab': tab,
        'suggested_tabs': [{'url': url_from_tab(t), 'name': t.name, 'band': t.band} for t in suggested_tabs],
        'comments': comments,
        'band_info': band_info,
        'comments_form': form,
        'scroll_to': scroll_to,
        'site_globals': settings.SITE_GLOBALS
    })


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
    return sorted(match_map, key=lambda t: t[0], reverse=True)   # sort by score


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
