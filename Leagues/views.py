from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Min, Avg, Max
from django_tables2 import RequestConfig
from django.http import Http404
from Leagues.admin import TeamResource
from tablib import Dataset
from .forms import NewLeagueForm, NewTeamForm, NewFieldForm, NewDivisionForm, NewSlotForm, NewCoachForm, SettingsForm
from django.http import HttpResponse
from Leagues.models import League, Team, Division, Field, Game, Slot, Coach, SiteConfiguration
from Leagues.gameGenerator import generateGames, scheduleGames, removeSchedule, displayStats, importData
from .tables import GamesTable, SlotsTable
import pandas as pd
import numpy as np
from django.db.models import Q
import numpy as np
from Leagues.tools import convertDatetimeToString
import datetime


# Create your views here.
def index1(request):
    fields = Field.objects.all()
    slots = Slot.objects.all()
    slot_names = []
    field_names = []
    for slot in slots:

        if slot.time.strftime("%Y-%m-%d %H:%M") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d %H:%M"))
    for field in fields:
        field_names.append(field.name)
    matrix = []
    df = pd.DataFrame(matrix, columns=field_names, index=slot_names)

    for slot in slots:
        df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = True

    table = df

    table = SlotsTable(Slot.objects.all())
    RequestConfig(request).configure(table)
    fields = Field.objects.all()
    slots = Slot.objects.all()
    slot_names = []
    field_names = []
    for slot in slots:

        if slot.time.strftime("%Y-%m-%d %H:%M") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d %H:%M"))
    for field in fields:
        field_names.append(field.name)
    matrix = []
    df = pd.DataFrame(matrix, columns=field_names, index=slot_names)

    for slot in slots:
        if not slot.game == None:
            df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = slot.game.shortstr()

    # return render(request, 'allfields.html', {'fields': fields, 'slots': slots, 'table': df.to_html(justify='center')})
    return render(request, 'index2.html', {'fields': fields, 'table': df})


def home(request):
    config = get_object_or_404(SiteConfiguration, pk=1)
    # teams = Team.objects.all().filter(league=league)

    # instance = get_object_or_404(MyModel, id=id)
    form = SettingsForm(request.POST or None, instance=config)
    if form.is_valid():
        form.save()
        return redirect('home')

    # config = SiteConfiguration.objects.all().first()
    # # get_object_or_404(League, pk=pk)
    # if request.method == 'POST':
    #     form = SettingsForm(request.POST or None, instance=config)
    #     if form.is_valid():
    #         config = form.save()
    #         return redirect('home')  # , pk=league.pk)  # TODO: redirect to the created topic page
    # else:
    #     form = SettingsForm()
    # return render(request, 'settings.html', {'config': config, 'form': form}
    df, df_slots, numGamesUnscheduled, numSlotsUnscheduled, totalScore = displayStats()
    return render(request, 'home.html',
                  {'df': df.to_html(justify='center'), 'df_slots': df_slots.to_html(justify='center'),
                   'numGamesUnscheduled': numGamesUnscheduled,
                   'numSlotsUnscheduled': numSlotsUnscheduled,
                   'totalScore': totalScore,
                   'config': config, 'form': form})


def gen_games(request):
    generateGames()
    # updateGameScores()
    return home(request)


def import_all(request):
    importData()
    return home(request)


def schedule_games(request):
    scheduleGames()
    return home(request)


def reset_games(request):
    removeSchedule()
    return home(request)


def leagues(request, pk):
    league = get_object_or_404(League, pk=pk)
    teams = Team.objects.all().filter(league=league)

    # instance = get_object_or_404(MyModel, id=id)
    form = NewLeagueForm(request.POST or None, instance=league)
    if form.is_valid():
        form.save()
        return redirect('allleagues')

    return render(request, 'leagues.html', {'league': league, 'teams': teams, 'form': form})


def teams(request, pk):
    team = get_object_or_404(Team, pk=pk)
    games = Game.objects.all().filter(team1=team) | Game.objects.all().filter(team2=team)
    fields = Field.objects.all().filter(league=team.league)
    slots = Slot.objects.all().order_by('time')  # TODO: get slots only of compatible fields

    game_names = []
    slot_names = []
    field_names = []

    for game in games:
        game_names.append(game.shortstr())

    data = []

    for game in games:
        try:
            data.append([game.shortstr(), Slot.objects.get(game=game)])
        except Slot.DoesNotExist:
            data.append([game.shortstr(), 'NOT SCHEDULED'])

    table = SlotsTable(Slot.objects.all().filter(Q(game__team1=team) | Q(game__team2=team)))
    RequestConfig(request).configure(table)

    # CREATES SLOT TABLE WITH ONLY GAMES FOR THIS TEAM
    for slot in slots:
        if slot.time.strftime("%Y-%m-%d %H:%M") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d %H:%M"))
    for field in fields:
        field_names.append(field.name)
    matrix = []
    df = pd.DataFrame(matrix, columns=field_names, index=slot_names)

    for slot in slots:
        if not slot.game == None:
            if ((slot.game.team1 == team) | (slot.game.team2 == team)):
                df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = slot.game.shortstr()
            # else:
            #     df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = ""

    return render(request, 'teams.html', {'team': team, 'games': games, 'slots': df.to_html, 'table': table,
                                          'table2': df.to_html(justify='center')})


def fields(request, pk):
    field = get_object_or_404(Field, pk=pk)
    return render(request, 'fields.html', {'field': field})


def divisions(request, pk):
    division = get_object_or_404(Division, pk=pk)
    teams = Team.objects.all().filter(division=division)
    return render(request, 'divisions.html', {'division': division, 'teams': teams})


def coaches(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    games = Game.objects.all().filter(team1__coach=coach) | Game.objects.all().filter(team2__coach=coach)
    teams = Team.objects.all().filter(coach=coach)
    game_names = []
    for game in games:
        game_names.append(game.shortstr())

    data = []
    for game in games:
        try:
            data.append([game.shortstr(), Slot.objects.get(game=game)])
        except Slot.DoesNotExist:
            data.append([game.shortstr(), 'NOT SCHEDULED'])

    a = Slot.objects.all().filter(Q(game__team1__coach=coach) | Q(game__team2__coach=coach))
    table = SlotsTable(Slot.objects.all().filter(Q(game__team1__coach=coach) | Q(game__team2__coach=coach)))
    RequestConfig(request).configure(table)
    return render(request, 'coaches.html', {'coach': coach, 'teams': teams, 'table': table})


def allfields(request):
    fields = Field.objects.all()
    slots = Slot.objects.all()
    slot_names = []
    field_names = []
    for slot in slots:

        if slot.time.strftime("%Y-%m-%d %H:%M") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d %H:%M"))
    for field in fields:
        field_names.append(field.name)
    matrix = []
    df = pd.DataFrame(matrix, columns=field_names, index=slot_names)

    for slot in slots:
        df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = True

    table = df

    return render(request, 'allfields.html', {'fields': fields, 'slots': slots, 'table': df.to_html(justify='center')})


def allleagues(request):
    leagues = League.objects.all()
    return render(request, 'allleagues.html', {'leagues': leagues})


def allteams(request):
    teams = Team.objects.all()
    return render(request, 'allteams.html', {'teams': teams})


def alldivisions(request):
    divisions = Division.objects.all()
    return render(request, 'alldivisions.html', {'divisions': divisions})


def allgames(request):
    table = GamesTable(Game.objects.all())
    RequestConfig(request).configure(table)
    return render(request, 'allgames.html', {'table': table})  # , 'leagues': leagues})


def allcoaches(request):
    coaches = Coach.objects.all()
    return render(request, 'allcoaches.html', {'coaches': coaches})


def allslots(request):
    table = SlotsTable(Slot.objects.all())
    RequestConfig(request).configure(table)
    fields = Field.objects.all()
    slots = Slot.objects.all().order_by('time')
    slot_names = []
    field_names = []
    slot_days = []

    for slot in slots:
        if slot.time.strftime("%Y-%m-%d %H:%M") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d %H:%M"))
    field_names.append('Day')
    for field in fields:
        field_names.append(field.name)
    field_names.append('Utilization')
    matrix = []
    df = pd.DataFrame(matrix, columns=field_names, index=slot_names)

    for slot in slots:
        if slot.time.strftime("%Y-%m-%d") not in slot_days:
            slot_days.append(slot.time.strftime("%Y-%m-%d"))

    df_2 = pd.DataFrame(matrix, columns=field_names, index=slot_days)
    for slot in slots:
        # print(str(df_2.loc[slot.time.strftime("%Y-%m-%d")][slot.field.name]))
        df_2.at[slot.time.strftime("%Y-%m-%d"), 'Day'] = slot.time.strftime("%A")
        if df_2.loc[slot.time.strftime("%Y-%m-%d")][slot.field.name] is np.nan:#.isnull():# == "nan":#is None:
            df_2.at[slot.time.strftime("%Y-%m-%d"), slot.field.name]=''

        if slot.game is not None:
            # a = slot.game.league.abbreviation
            df_2.at[slot.time.strftime("%Y-%m-%d"), slot.field.name] = str(
                str(df_2.loc[slot.time.strftime("%Y-%m-%d")][slot.field.name]) + slot.game.league.abbreviation + ' ')

        else:
            df_2.at[slot.time.strftime("%Y-%m-%d"), slot.field.name] = str(
                str(df_2.loc[slot.time.strftime("%Y-%m-%d")][slot.field.name]) + '-- ')
        # else:
        #     df_2.at[slot.time.strftime("%Y-%m-%d"), slot.field.name]=''
        # df_2.iloc[slot.time.strftime("%Y-%m-%d")][slot.field.name]

    for slot in slots:
        if slot.time.strftime("%Y-%m-%d") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d"))
            num_slots_on_day =  len(Slot.objects.all().filter(time__date=slot.time.date()))
            num_scheduled_slots_on_day = len(Slot.objects.all().filter(Q(time__date=slot.time.date()),~Q(game=None)))
            # df_2.at[slot.time.strftime("%Y-%m-%d"), 'num_slots_on_day'] = Utilization
            # df_2.at[slot.time.strftime("%Y-%m-%d"), 'num_scheduled_slots_on_day'] = num_scheduled_slots_on_day
            df_2.at[slot.time.strftime("%Y-%m-%d"), 'Utilization'] = str(num_scheduled_slots_on_day) + " of " + str(num_slots_on_day) + " = " + str(round((num_scheduled_slots_on_day/num_slots_on_day)*100,2))


    for col in df.columns:
        df[col].values[:] = ''

    for slot in slots:

        if not slot.game == None:
            df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = slot.game.shortstr()
            if slot.game.league_id in [1, 2, 3, 4, 5, 6, 7]:
                df.at[(slot.time + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
                df.at[(slot.time + datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
                df.at[(slot.time + datetime.timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
                df.at[(slot.time + datetime.timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
            if slot.game.league_id in [1, 2, 3, 4, 5]:
                df.at[(slot.time + datetime.timedelta(minutes=75)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
            if slot.game.league_id in [1, 2, 3, 4, 5]:
                df.at[(slot.time + datetime.timedelta(minutes=90)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
            if slot.game.league_id in [1, 2, 3, 4]:
                df.at[(slot.time + datetime.timedelta(minutes=105)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
            if slot.game.league_id in [1, 2]:
                df.at[(slot.time + datetime.timedelta(minutes=120)).strftime("%Y-%m-%d %H:%M"), slot.field.name] = "[]"
        else:
            df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = "UNSCHEDULED"
        # df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = slot.game.shortstr()
        # df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = slot.game.shortstr()
        # else:
        #     df.at[slot.time.strftime("%Y-%m-%d %H:%M"), slot.field.name] = "A"
        df.at[slot.time.strftime("%Y-%m-%d %H:%M"), 'Day'] = slot.time.strftime("%A")
    df = df.sort_index()
    return render(request, 'allslots.html',
                  {'table': table, 'table2': df.to_html(justify='center'), 'table3': df_2.to_html(justify='center')})


def stats(request):
    df, numGamesUnscheduled, numSlotsUnscheduled, totalScore = displayStats()
    return render(request, 'stats.html', {'df': df.to_html(justify='center'),
                                          'numGamesUnscheduled': numGamesUnscheduled,
                                          'numSlotsUnscheduled': numSlotsUnscheduled,
                                          'totalScore': totalScore})


def settings(request):  # , pk):
    config = SiteConfiguration()
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            config = form.save()
            return redirect('allteams')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = SettingsForm()
    return render(request, 'settings.html', {'config': config, 'form': form})


def simple_upload(request):
    if request.method == 'POST':
        person_resource = TeamResource()
        dataset = Dataset()
        new_persons = request.FILES['myfile']

        imported_data = dataset.load(new_persons.read())
        result = person_resource.import_data(dataset, dry_run=True)  # Test the data import

        if not result.has_errors():
            person_resource.import_data(dataset, dry_run=False)  # Actually import now

    return render(request, 'core/simple_upload.html')


def new_league(request):  # , pk):
    league = League()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewLeagueForm(request.POST)
        if form.is_valid():
            league = form.save()
            return redirect('allleagues')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewLeagueForm()
    return render(request, 'new_league.html', {'league': league, 'form': form})


def new_team(request):  # , pk):
    team = Team()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewTeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            generateGames()
            # updateGameScores()
            return redirect('allteams')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewTeamForm()
    return render(request, 'new_team.html', {'team': team, 'form': form})


def new_field(request):  # , pk):
    field = Field()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewFieldForm(request.POST)
        if form.is_valid():
            field = form.save()
            return redirect('allfields')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewFieldForm()
    return render(request, 'new_field.html', {'field': field, 'form': form})


def new_slot(request):  # , pk):
    slot = Slot()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewSlotForm(request.POST)
        if form.is_valid():
            slot = form.save()
            return redirect('allslots')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewSlotForm()
    return render(request, 'new_slot.html', {'slot': slot, 'form': form})


def new_division(request):  # , pk):
    division = Division()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewDivisionForm(request.POST)
        if form.is_valid():
            division = form.save()
            return redirect('alldivisions')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewDivisionForm()
    return render(request, 'new_division.html', {'division': division, 'form': form})


def new_coach(request):  # , pk):
    coach = Coach()  # get_object_or_404(League, pk=pk)
    if request.method == 'POST':
        form = NewCoachForm(request.POST)
        if form.is_valid():
            coach = form.save()
            return redirect('allcoaches')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewCoachForm()
    return render(request, 'new_coach.html', {'coach': coach, 'form': form})
