from __future__ import unicode_literals

# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [app_label]'
# into your database.

from django.db import models


class BandInfo(models.Model):
    band_name = models.CharField(primary_key=True, max_length=100)
    genres = models.CharField(max_length=200, blank=True)
    origin = models.CharField(max_length=50, blank=True)
    years_active = models.CharField(max_length=50, blank=True)
    members = models.CharField(max_length=200, blank=True)

    class Meta:
        managed = False
        db_table = 'band_info'


class ExtendedInfo(models.Model):
    tab = models.IntegerField(primary_key=True)
    info = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'extended_info'


class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    tab = models.ForeignKey("Tabs")
    #tab_id = models.IntegerField() #this is created by the foreign key apparently
    name = models.CharField(max_length=25)
    comment = models.CharField(max_length=600)
    ip = models.CharField(max_length=15)
    spam = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comment'


class CrawlUrls(models.Model):
    url = models.CharField(primary_key=True, max_length=128)
    done = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'crawl_urls'


class DjangoMigrations(models.Model):
    id = models.IntegerField(primary_key=True)  # AutoField?
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class Heatmap(models.Model):
    pageid = models.IntegerField()
    x = models.IntegerField()
    y = models.IntegerField()
    counter = models.IntegerField()
    clicks = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'heatmap'


class Tabs(models.Model):
    id = models.AutoField(primary_key=True)  # AutoField?
    name = models.CharField(max_length=300)
    band = models.CharField(max_length=300)
    tab = models.TextField(blank=True)
    hit_count = models.IntegerField()
    vote_yes = models.IntegerField()
    vote_no = models.IntegerField()
    gzip_tab = models.TextField(blank=True)

    @property
    def url(self):
        url = '/bands/' + self.band[0].upper() + '/'
        url += self.band.replace(' ', '+')
        url += '/' + str(self.id) + '/'
        url += self.name.replace(' ', '+') + '.html'
        return url

    class Meta:
        managed = False
        db_table = 'tabs'


class TabsFulltext(models.Model):
    id = models.IntegerField(primary_key=True)  # AutoField?
    name = models.CharField(max_length=300)
    band = models.CharField(max_length=300)

    class Meta:
        managed = False
        db_table = 'tabs_fulltext'