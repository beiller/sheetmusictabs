from django.conf.urls import patterns, include, url
from django.contrib import admin
import sheetmusictabs.views

urlpatterns = patterns('',
    #url(r'^$', 'sheetmusictabs.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^hello/$', sheetmusictabs.views.hello),
    url(r'^time/$', sheetmusictabs.views.current_datetime),
    url(r'^time/plus/(\d{1,2})/$', sheetmusictabs.views.hours_ahead),
)
