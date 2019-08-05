"""DjangoLeagueScheduler URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url

from Leagues import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^leagues/(?P<pk>\d+)/$', views.leagues, name='leagues'),
    url(r'^teams/(?P<pk>\d+)/$', views.teams, name='teams'),
    url(r'^fields/(?P<pk>\d+)/$', views.fields, name='fields'),
    url(r'^divisions/(?P<pk>\d+)/$', views.divisions, name='divisions'),
    url(r'^allfields$', views.allfields, name='allfields'),
    url(r'^allleagues$', views.allleagues, name='allleagues'),
    url(r'^allteams$', views.allteams, name='allteams'),
    url(r'^alldivisions$', views.alldivisions, name='alldivisions'),
    url(r'^allgames$', views.allgames, name='allgames'),
    url(r'^allslots$', views.allslots, name='allslots'),
    url(r'^new_league$', views.new_league, name='new_league'),
    url(r'^new_team$', views.new_team, name='new_team'),
    url(r'^new_field$', views.new_field, name='new_field'),
    url(r'^new_division$', views.new_division, name='new_division'),
    url(r'^new_slot$', views.new_slot, name='new_slot'),
    url(r'^schedule_games', views.schedule_games, name='schedule_games'),
    url(r'^reset_games', views.reset_games, name='reset_games'),
    url(r'^gen_games', views.gen_games, name='gen_games'),
    url(r'^stats', views.stats, name='stats'),
    url(r'^import_all', views.import_all, name='import_all'),
    url(r'^index1', views.index1, name='index1'),

    # url(r'^new_division$', views.new_division, name='new_division'),
    # url(r'^leagues/(?P<pk>\d+)/new/$', views.new_league, name='new_league'),
    path('admin/', admin.site.urls),
]
