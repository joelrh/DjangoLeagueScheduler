from .models import League, Game, Field, Division, Team, Slot, Coach
import time
from django.db.models import Q
import pandas as pd
from django.db import connection
from Leagues.gameGenerator_df import *
import tablib
from import_export import resources
from Leagues.admin import TeamResource
import datetime


def round_minutes(dt, direction, resolution):
    new_minute = (dt.minute // resolution + (1 if direction == 'up' else 0)) * resolution
    return dt + datetime.timedelta(minutes=new_minute - dt.minute)


def importData():
    # ORDER MATTERS HERE

    # IMPORT COACHES
    Coach.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'firstName', 'lastName'])
    my_dataset.xlsx = open('data\9-29-19_data\Coach-2019-09-29.xlsx', 'rb').read()
    print(my_dataset)
    slot_resource = resources.modelresource_factory(model=Coach)()
    slot_resource.import_data(my_dataset, dry_run=False)

    # IMPORT LEAGUES
    League.objects.all().delete()
    my_dataset = tablib.Dataset(
        headers=['id', 'name', 'abbreviation', 'description', 'maxLateGames', 'maxGames', 'gameDuration','daysBetween'])
    my_dataset.xlsx = open('data\9-29-19_data\League-2019-09-29-mod.xlsx', 'rb').read()
    print(my_dataset)
    division_resource = resources.modelresource_factory(model=League)()
    division_resource.import_data(my_dataset, dry_run=False)

    # IMPORT DIVISIONS
    Division.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name', 'abbreviation', 'description', 'league'])
    my_dataset.xlsx = open('data\9-29-19_data\Division-2019-09-29-mod.xlsx', 'rb').read()
    print(my_dataset)
    division_resource = resources.modelresource_factory(model=Division)()
    division_resource.import_data(my_dataset, dry_run=False)

    # IMPORT TEAMS
    Team.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name', 'description', 'league', 'division', 'coach'])
    my_dataset.xlsx = open('data\9-29-19_data\Team-2019-09-29-mod.xlsx', 'rb').read()
    print(my_dataset)
    team_resource = resources.modelresource_factory(model=Team)()
    team_resource.import_data(my_dataset, dry_run=False)

    # IMPORT FIELDS
    Field.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'name', 'description', 'league'])
    my_dataset.xlsx = open('data\9-29-19_data\Field-2019-09-29-mod.xlsx', 'rb').read()
    print(my_dataset)
    field_resource = resources.modelresource_factory(model=Field)()
    field_resource.import_data(my_dataset, dry_run=False)

    # IMPORT SLOTS
    slots = Slot.objects.all().delete()
    my_dataset = tablib.Dataset(headers=['id', 'field', 'primaryLeague', 'secondaryLeague', 'game', 'time', 'duration'])
    my_dataset.xlsx = open('data\9-29-19_data\Slot-2019-09-29-mod.xlsx', 'rb').read()
    print(my_dataset)
    slot_resource = resources.modelresource_factory(model=Slot)()
    slot_resource.import_data(my_dataset, dry_run=False)
    # Round slot times to nearest minute
    slots = Slot.objects.all()

    for slot in slots:
        slot.time = round_minutes(slot.time + timedelta(minutes=1), 'down', 15)

        slot.time = datetime.datetime(slot.time.year, slot.time.month, slot.time.day, slot.time.hour, slot.time.minute)
        slot.save()
    # TODO : Still seeing small number differences in seconds - may try implementing the "replace" function below
    # from datetime import datetime
    # new_time = datetime.utcfromtimestamp(1508265552).replace(minute=0, second=0, microsecond=0)

    # Generate all possible games
    generateGames()


def generateGames():
    print('GENERATING GAMES')
    leagues = League.objects.all()

    for league in leagues:
        teams = Team.objects.all().filter(league=league).order_by('?')

        # if there are fewer teams than maxGames - double up
        print('Number of teams in league')
        print(len(Team.objects.all().filter(league=league.id)))
        print('Max Games set for league')
        print(league.maxGames)
        doubleUp = False
        if len(Team.objects.all().filter(league=league.id)) <= league.maxGames+1:

            doubleUp = True

        for team1 in teams:
            for team2 in teams:
                checkTeam1 = Game.objects.all().filter(team1=team1, team2=team2)
                checkTeam2 = Game.objects.all().filter(team1=team2, team2=team1)
                if (len(checkTeam1) + len(checkTeam2) == 0) and team1 != team2:
                    game = Game(team1=team1, team2=team2, league=team1.league)
                    game.save()
                    print('ADDING: ' + game.__str__())
                    if doubleUp:
                        game = Game(team1=team1, team2=team2, league=team1.league, handicap=500)
                        game.save()
                        print('ADDING: ' + game.__str__())
        print('Num Games generated for league')
        print(len(Game.objects.all().filter(league=league.id)))
        print('Num Games generated for all leagues')
        print(len(Game.objects.all()))


def removeSchedule():
    slots = Slot.objects.all().filter(~Q(game=None))
    for slot in slots:
        print('UNSCHEDULING' + slot.__str__())
        slot.game = None
        slot.save()


def scheduleGames():
    GG = gameGenerator_df()
    GG.scheduleGames_df()


def displayStats():
    # TODO:  Add slot performance table (# of # scheduled per day)

    slots = Slot.objects.all().order_by('time')
    slot_names = []
    num_slots_on_day = []
    num_scheduled_slots_on_day=[]
    matrix=[]
    df_slots = pd.DataFrame(matrix,columns=['day','num_slots_on_day','num_scheduled_slots_on_day','percent'])

    for slot in slots:
        if slot.time.strftime("%Y-%m-%d") not in slot_names:
            slot_names.append(slot.time.strftime("%Y-%m-%d"))
            num_slots_on_day =  len(Slot.objects.all().filter(time__date=slot.time.date()))
            num_scheduled_slots_on_day = len(Slot.objects.all().filter(Q(time__date=slot.time.date()),~Q(game=None)))
            df_slots.at[slot.time.strftime("%Y-%m-%d"), 'day'] = slot.time.strftime("%A")
            df_slots.at[slot.time.strftime("%Y-%m-%d"), 'num_slots_on_day'] = num_slots_on_day
            df_slots.at[slot.time.strftime("%Y-%m-%d"), 'num_scheduled_slots_on_day'] = num_scheduled_slots_on_day
            df_slots.at[slot.time.strftime("%Y-%m-%d"), 'percent'] = (num_scheduled_slots_on_day/num_slots_on_day)*100

    # df_slots = pd.DataFrame(matrix, columns=['num_slots_on_day','num_scheduled_slots_on_day'], index=slot_names)



    teams = Team.objects.all().order_by('league')
    team_names = []
    # column_names = ['description', 'numScheduled', 'numUnscheduled', 'numDivisionalScheduled', 'numTotalDivisional',
    #                 'numLateGames']
    for team in teams:
        team_names.append(team.__str__())
    matrix = []
    df = pd.DataFrame(matrix, index=team_names)

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
        gamesWithTeam = Game.objects.all().filter(Q(team1=team) | Q(team2=team))

        # slotsWithTeam = []
        slotsWithTeam = Slot.objects.all().filter(game__in=gamesWithTeam).order_by('time')
        # for game in gamesWithTeam:
        #     slotsWithTeam.append(Slot.objects.all().filter(game=game))
        earliestGame=None
        latestGame=None
        numberOfGames=None
        timeBeteenGames=None
        minTimeBetweenGames=None
        maxTimeBetweenGames=None
        avgTimeBetweenGames=None


        if len(slotsWithTeam)>0:
            earliestGame = slotsWithTeam.earliest()
            latestGame = slotsWithTeam.latest()
            numberOfGames = len(slotsWithTeam)
            timeBeteenGames = []
            for slotIndex in range(numberOfGames-1,1,-1):
                diff = slotsWithTeam[slotIndex].time - slotsWithTeam[slotIndex-1].time

                timeBeteenGames.append(slotsWithTeam[slotIndex].time - slotsWithTeam[slotIndex-1].time)
            minTimeBetweenGames = min(timeBeteenGames)
            maxTimeBetweenGames = max(timeBeteenGames)
            avgTimeBetweenGames = (latestGame.time-earliestGame.time)/numberOfGames

            earliestGame = datetime.datetime(earliestGame.time.year, earliestGame.time.month, earliestGame.time.day,
                                             earliestGame.time.hour, earliestGame.time.minute)
            latestGame = datetime.datetime(latestGame.time.year, latestGame.time.month, latestGame.time.day,
                                             latestGame.time.hour, latestGame.time.minute)

        # df.at[teamName, 'description'] = team.__str__()
        df.at[teamName, 'Scheduled'] = numScheduled
        df.at[teamName, 'Unscheduled'] = numUnscheduled
        df.at[teamName, 'Divisional'] = numDivisionalScheduled
        df.at[teamName, 'TotalDivisional'] = numTotalDivisional
        df.at[teamName, 'LateGames'] = numLateGames
        df.at[teamName, 'first'] = earliestGame
        df.at[teamName, 'last'] = latestGame
        df.at[teamName, 'minTimeBetweenGames'] = minTimeBetweenGames
        df.at[teamName, 'maxTimeBetweenGames'] = maxTimeBetweenGames
        df.at[teamName, 'avgTimeBetweenGames'] = avgTimeBetweenGames

        # TODO: add average time between games to the stats table
        # TODO: add min and max days between games to the stats table
        # TODO: add games per day / total slots per day

        totalScore = totalScore + numScheduled + numDivisionalScheduled - numUnscheduled - numLateGames

    print('---------------------------------------------------')
    print('NUMBER GAMES UNSCHEDULED: ' + str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None))))
    print('NUMBER SLOTS UNSCHEDULED: ' + str(len(Slot.objects.all().filter(game=None))))
    print('---------------------------------------------------')

    numGamesUnscheduled = str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None)))
    numSlotsUnscheduled = len(Slot.objects.all().filter(game=None))



    return df, df_slots, numGamesUnscheduled, numSlotsUnscheduled, totalScore
