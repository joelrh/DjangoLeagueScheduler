from .models import League, Game, Field, Division, Team, Slot
import time
from django.db.models import Q
import pandas as pd
from django.db import connection
from Leagues.gameGenerator_df import *
import tablib
from import_export import resources
from Leagues.admin import TeamResource

def importData():
    # ORDER MATTERS HERE

    # IMPORT LEAGUES
    League.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name', 'abbreviation', 'description'])
    my_dataset.xlsx = open('data\League-2019-07-26.xlsx', 'rb').read()
    print(my_dataset)
    division_resource = resources.modelresource_factory(model=League)()
    division_resource.import_data(my_dataset, dry_run=False)

    # IMPORT DIVISIONS
    Division.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name', 'abbreviation', 'description','league'])
    my_dataset.xlsx = open('data\Division-2019-07-26.xlsx', 'rb').read()
    print(my_dataset)
    division_resource = resources.modelresource_factory(model=Division)()
    division_resource.import_data(my_dataset, dry_run=False)

    # IMPORT TEAMS
    Team.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name','description','league','division'])
    my_dataset.xlsx = open('data\Team-2019-07-26.xlsx', 'rb').read()
    print(my_dataset)
    team_resource = resources.modelresource_factory(model=Team)()
    team_resource.import_data(my_dataset, dry_run=False)

    # IMPORT FIELDS
    Field.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name','description','league'])
    my_dataset.xlsx = open('data\Field-2019-07-26.xlsx', 'rb').read()
    print(my_dataset)
    field_resource = resources.modelresource_factory(model=Field)()
    field_resource.import_data(my_dataset, dry_run=False)

    # IMPORT SLOTS
    Slot.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'field', 'game', 'time'])
    my_dataset.xlsx = open('data\Slot-2019-07-26.xlsx', 'rb').read()
    print(my_dataset)
    slot_resource = resources.modelresource_factory(model=Slot)()
    slot_resource.import_data(my_dataset, dry_run=False)

    generateGames()

def generateGames():
    print('GENERATING GAMES')
    leagues = League.objects.all()
    for league in leagues:
        teams = Team.objects.all().filter(league=league).order_by('?')
        for team1 in teams:
            for team2 in teams:
                checkTeam1 = Game.objects.all().filter(team1=team1, team2=team2)
                checkTeam2 = Game.objects.all().filter(team1=team2, team2=team1)
                if (len(checkTeam1) + len(checkTeam2) == 0) and team1 != team2:
                    game = Game(team1=team1, team2=team2, league=team1.league)
                    game.save()
                    print('ADDING: ' + game.__str__())

def removeSchedule():
    slots = Slot.objects.all().filter(~Q(game = None))
    for slot in slots:
        print('UNSCHEDULING' + slot.__str__())
        slot.game = None
        slot.save()

def scheduleGames():

    GG = gameGenerator_df()
    GG.scheduleGames_df()

def displayStats():

    teams = Team.objects.all().order_by('league')
    team_names = []
    column_names = ['description', 'numScheduled', 'numUnscheduled', 'numDivisionalScheduled', 'numTotalDivisional',
                    'numLateGames']
    for team in teams:
        team_names.append(team.__str__())
    matrix = []
    df = pd.DataFrame(matrix, columns=column_names, index=team_names)

    totalScore = 0

    for team in teams:
        teamName = team.__str__()
        numScheduled = len(Slot.objects.all().filter(Q(game__team1=team) | Q(game__team2=team)))
        # numUnscheduled = len(Game.objects.all().filter(Q(team1=team) | Q(team2=team), isScheduled=False))
        numUnscheduled = len(Game.objects.all().filter(Q(team1=team) | Q(team2=team))) - numScheduled
        numDivisionalScheduled = len(Slot.objects.all().filter(Q(game__team1=team) | Q(game__team2=team),
                                                               game__team1__division=team.division,
                                                               game__team2__division=team.division,
                                                               game__team1__league=team.league))
        numTotalDivisional = len(Game.objects.all().filter(Q(team1=team) | Q(team2=team),
                                                           team1__division=team.division,
                                                           team2__division=team.division,
                                                           team1__league=team.league))
        numLateGames = len(Slot.objects.all().filter(Q(game__team1=team) | Q(game__team2=team), time__hour__gt=18))
        df.at[teamName, 'description'] = team.__str__()
        df.at[teamName, 'numScheduled'] = numScheduled
        df.at[teamName, 'numUnscheduled'] = numUnscheduled
        df.at[teamName, 'numDivisionalScheduled'] = numDivisionalScheduled
        df.at[teamName, 'numTotalDivisional'] = numTotalDivisional
        df.at[teamName, 'numLateGames'] = numLateGames
        # TODO : add average time between games to the stats table
        # TODO : add min and max days between games to the stats table

        totalScore = totalScore + numScheduled + numDivisionalScheduled - numUnscheduled - numLateGames

    print('---------------------------------------------------')
    print('NUMBER GAMES UNSCHEDULED: ' + str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None))))
    print('NUMBER SLOTS UNSCHEDULED: ' + str(len(Slot.objects.all().filter(game=None))))
    print('---------------------------------------------------')

    numGamesUnscheduled = str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None)))
    numSlotsUnscheduled = len(Slot.objects.all().filter(game=None))

    return df, numGamesUnscheduled, numSlotsUnscheduled, totalScore
