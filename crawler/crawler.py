import random

__author__ = 'itbxh'
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sheetmusictabs.settings")
import django
django.setup()

import urllib2
from bs4 import BeautifulSoup
from StringIO import StringIO
import gzip
import re
import pickle
import time
from sheetmusictabs.models import Tabs, TabsFulltext
import zlib

db = {}
try:
    fh = open('html_database', 'rb')
    if fh:
        db = pickle.load(fh)
    fh.close()
except IOError:
    pass


def database_add(url, html):
    if db:
        db[url] = html
        fh = open('html_database', 'wb')
        pickle.dump(db, fh)
        fh.close()


def get_url(url, headers):
    if db and url in db:
        return db[url]

    req = urllib2.Request(url, data=None, headers=headers)
    response = urllib2.urlopen(req)
    if 'charset' in response.headers['Content-Type']:
        encoding = response.headers['Content-Type'].split('charset=')[-1]
    else:
        encoding = ''

    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = response.read()
    if encoding != '':
        html_data = unicode(data, encoding)
    else:
        html_data = unicode(data, 'utf-8')
    database_add(url, html_data)
    return html_data


def find_similar(tab):
    rows = Tabs.objects.filter(name=tab.name, band=tab.band).order_by('-id').all()
    exact_match_ids = []
    normalized_match_ids = []
    for row in rows:
        if row.tab is None:
                row.tab = zlib.decompress(row.gzip_tab)
        if row.tab == tab.tab:
            print 'exact match: ', tab.tab[0:50], row.id
            exact_match_ids.append(row.id)
            continue

        t1 = re.sub('[\s]', '', tab.tab).strip()
        t2 = re.sub('[\s]', '', row.tab).strip()
        if t1 == t2:
            print 'normalized match: ', tab.tab[0:50], row.id
            normalized_match_ids.append(row.id)
            continue
        print 'no match: ', tab.tab[0:50]
    if len(exact_match_ids) > 0 or len(normalized_match_ids) > 0:
        return True

    return False


def do_crawl():
    html = {}

    url = 'http://www.ultimate-guitar.com/'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-GB,en-US;q=0.8,en;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.ultimate-guitar.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.google.ca/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
    }

    html[url] = get_url(url, headers)

    time.sleep(2)

    headers['Referer'] = 'http://www.ultimate-guitar.com/'
    url = 'http://www.ultimate-guitar.com/tabs/'
    html[url] = get_url(url, headers)
    urls = set()
    soup = BeautifulSoup(html[url])
    links = soup.find_all('a')
    for link in links:
        if re.search('^.*?/[\w]/[\w]+/[\w]+\.htm', link['href']) and 'guitar_pro' not in link['href']:
            urls.add(link['href'])
    urls = list(urls)[8:]
    time.sleep(2)

    for url in urls:
        print url
        headers['Referer'] = 'http://www.ultimate-guitar.com/tabs/'
        html[url] = get_url(url, headers)
        soup = BeautifulSoup(html[url])
        tab = str(soup.find_all('pre')[-1])

        song_title = soup.find_all('div', class_='t_title')[-1].h1.get_text()
        artist_title = soup.find_all('div', class_='t_autor')[-1].a.get_text()

        print song_title + ' by ' + artist_title
        #print tab
        t = Tabs(name=song_title, band=artist_title, tab=tab, hit_count=0, vote_yes=0, vote_no=0)
        if not find_similar(t):
            t.save()
            tft = TabsFulltext(id=t.id, name=song_title, band=artist_title)
            tft.save()
        else:
            print 'found similar, skipping!'

        time.sleep(30 + random.randint(0, 30))


def admin_do_stuff():
    Tabs.objects.get(pk=374741).delete()


do_crawl()