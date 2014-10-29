from django.conf.urls import patterns, include, url
from django.contrib import admin
import sheetmusictabs.views

urlpatterns = patterns('',
    #url(r'^$', 'sheetmusictabs.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^$', sheetmusictabs.views.tab_list),
    #0/bands/B/Bob+Seger+tabs/185010/Turn+The+Page+Tab.html
    url(r'^bands/[A-Z0-9]/[^/]+/([0-9]+)/[^/]+$', sheetmusictabs.views.tab_page)
)
