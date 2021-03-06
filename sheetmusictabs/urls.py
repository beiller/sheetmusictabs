from django.conf.urls import patterns, include, url
from django.contrib import admin
import sheetmusictabs.views

urlpatterns = patterns('',
    url(r'^$', sheetmusictabs.views.tab_list),
    #0/bands/B/Bob+Seger+tabs/185010/Turn+The+Page+Tab.html
    url(r'^bands/[A-Z0-9]/[^/]+/([0-9]+)/[^/]+?\.json$', sheetmusictabs.views.tab_page_json),
    url(r'^bands/[A-Z0-9]/[^/]+/([0-9]+)/[^/]+$', sheetmusictabs.views.tab_page),
    url(r'^bands/([A-Z0-9])/$', sheetmusictabs.views.band_letter_page),
    url(r'^bands/[A-Z0-9]/([^/]+)/$', sheetmusictabs.views.band_page),
    url(r'^sitemap\.xml$', sheetmusictabs.views.sitemap_index),
    url(r'^sitemap([1-9][0-9]*)\.xml$', sheetmusictabs.views.sitemap),
    url(r'^ajax/search.*$', sheetmusictabs.views.search),
    url(r'^ajax/vote.*$', sheetmusictabs.views.vote_tab),
    url(r'^ajax/comment.*$', sheetmusictabs.views.add_comment),
    url(r'^comment_moderation.html$', sheetmusictabs.views.comment_moderation_page),
)
