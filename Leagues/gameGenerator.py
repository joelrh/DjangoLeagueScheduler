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


def updateGameScore(game):
    score = 0

    # HANDICAP REDUCED AS NUMBER OF GAMES SCHEDULED INCREASES
    numRelatedscheduledGames = len(Slot.objects.all().filter(Q(game__team1=game.team1) |
                                                             Q(game__team1=game.team2) |
                                                             Q(game__team2=game.team1) |
                                                             Q(game__team2=game.team2)))
    score = score + (numRelatedscheduledGames * 100)

    # INTERDIVISIONAL GAMES HAVE A HIGHER HANDICAP TO ENSURE THEY ARE SCHEDULED FIRST
    if game.team1.division == game.team2.division:
        score = score - 80
    teams = [game.team1, game.team2]

    # GAMES WITH LOWER THAN AVERAGE NUMBER OF GAMES ARE FURTHER HANDICAPPED - PER LEAGUE
    leagues = League.objects.all()
    numTeamsInLeague = len(Team.objects.all().filter(league=game.league))
    numScheduledGamesInLeague = len(Slot.objects.all().filter(game__league=game.league))
    averageScheduledGamesInLeague = numScheduledGamesInLeague / numTeamsInLeague
    # teamsInLeague = League.objects.all().filter(league = league)
    for team in teams:
        schduledGamesForTeam = len(Slot.objects.all().filter(Q(game__team1=team) | Q(game__team2=team)))
        if schduledGamesForTeam < averageScheduledGamesInLeague:
            score = score - ((averageScheduledGamesInLeague - schduledGamesForTeam) * 100)

    # GAMES WITH THE MOST RESTRICTIONS SHOULD BE SCHEDULED FIRST

    game.score = score
    game.save()


def updateGameScores():
    # query = str(Team.objects.all().query)
    # df = pd.read_sql_query(query, connection)

    # generateGames()
    print('UPDATING SCORES')
    t = time.time()
    score = 0
    # games = Game.objects.all().filter(isScheduled=False)
    games = Game.objects.all()
    # slots = Slot.objects.all()
    for game in games:
        if len(Slot.objects.all().filter(game=game)) == 0:
            updateGameScore(game)
            game.save()

    elapsed_time = time.time() - t
    print('ELAPSED TIME:' + str(elapsed_time))


def removeSchedule():
    # games = Game.objects.all().filter(isScheduled=True)
    # for game in games:
    #     print('UNSCHEDULING' + game.__str__())
    #     game.isScheduled = False
    #     game.save()
    slots = Slot.objects.all().filter(~Q(game = None))
    for slot in slots:
        print('UNSCHEDULING' + slot.__str__())
        slot.game = None
        slot.save()


def scheduleGame(slot, game, enforceLateCap):
    print('ATTEMPTING TO SCHEDULE GAME:  ' + game.__str__())
    print('SLOT' + slot.__str__())
    Compatible = False

    ## CHECK LEAGUE COMPATIBILITY
    leagues = League.objects.all().filter(field=slot.field)
    for league in leagues:
        if game.league_id == league.pk:
            Compatible = True
            print('SLOT LEAGUE IS COMPATIBLE WITH GAME')
    if not Compatible: print('SLOT LEAGUE IS NOT COMPATIBLE WITH GAME')
    # Find all scheduled games and ensure that this game is not on the same day
    gameswithteams = Slot.objects.all().filter(Q(game__team1=game.team1) |
                                               Q(game__team1=game.team2) |
                                               Q(game__team2=game.team1) |
                                               Q(game__team2=game.team2))
    ## ENSURE NO DOUBLE BOOKING
    # TODO: this does not appear to be working properly
    for game_ in gameswithteams:
        try:
            if slot.time.date() == Slot.objects.get(game=game_).time.date():
                Compatible = False
                print('A TEAM ALREADY HAS A GAME SCHEDULED FOR THAT DAY')
                break
        except:
            pass
    if Compatible: print('NO GAMES ALREADY SCHEDULED ON THIS DAY WITH TEAMS')

    ## ENSURE NO MORE THAN 2 LATE GAMES
    teams = [game.team1, game.team2]
    if slot.time.hour > 18 and enforceLateCap:
        for team_ in teams:
            # numLateGames=0
            # slotswithteams = Slot.objects.all().filter(Q(game__team1=team_) |
            #                                       Q(game__team2=team_))
            # for slot_ in slotswithteams:
            #     if slot_.time.hour > 18: numLateGames=numLateGames+1
            # if numLateGames>=2:
            #     Compatible = False
            #     print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR ', team_.name)
            if len(Slot.objects.all().filter(Q(game__team1=team_) | Q(game__team2=team_), time__hour__gt=18)) >= 2:
                Compatible = False
                print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR ', team_.name)
    if Compatible: print('NO LATE GAME CONFLICTS')

    # ENSURE NO MORE THAN 2 GAMES PER WEEK

    if Compatible:
        print('SCHEDULING GAME')
        slot.game = game
        # game.isScheduled = True
        # game.save()
        slot.save()
        updateGameScores()
        return True
    else:
        print('GAME NOT COMPATIBLE')
    return False


def scheduleGames():
    # generateGames()

    GG = gameGenerator_df()
    GG.scheduleGames_df()

    DBVersion = False
    if DBVersion:
        t = time.time()
        updateGameScores()
        print('SCHEDULING ALL GAMES')

        slots = Slot.objects.all()
        # need to only get slots that are not already scheduled
        # update scores
        for slot in slots:
            print(slot)

        # slots.objects.order_by('?')
        numberRetried = 0
        # while len(Game.objects.all().filter(isScheduled=False)) > 0 and len(
        #         Slot.objects.all().filter(game=None)) > 0 and numberRetried < 10:
        while len(Game.objects.exclude(id__in=Slot.objects.all().exclude(game=None).values_list('game'))) > 0 and \
                len(Slot.objects.all().filter(game=None)) > 0 and \
                numberRetried < 10:
            numberRetried = numberRetried + 1
            slots = Slot.objects.all().filter(game=None).order_by('?')
            if numberRetried > 5:
                enforceLateCap = False
            else:
                enforceLateCap = True
            for slot in slots:

                # This query only gets unscheduled games that are compatible with the field in the slot, and sorts them by score (low -> high)
                gamesSortedByLowestScore = Game.objects.order_by('score'). \
                    exclude(id__in=Slot.objects.all().exclude(game=None).values_list('game')). \
                    filter(league__in=slot.field.league.all())
                # for game in gamesSortedByLowestScore:
                #     print(game)
                for game in gamesSortedByLowestScore:
                    # updateGameScore(game)
                    if len(Slot.objects.all().filter(game=game)) == 0:
                        if scheduleGame(slot, game, enforceLateCap):
                            print('game scheduled')
                            print(slot)
                            print(slot.game)
                            break
                print('---------------------------------------------------')
                print('NUMBER GAMES UNSCHEDULED: ' + str(
                    len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None))))
                print('NUMBER SLOTS UNSCHEDULED: ' + str(len(Slot.objects.all().filter(game=None))))
                print('---------------------------------------------------')
        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))


def displayStats():
    # TODO : add average time between games to the stats table
    teams = Team.objects.all().order_by('league')
    slot_names = []
    team_names = []
    column_names = ['description', 'numScheduled', 'numUnscheduled', 'numDivisionalScheduled', 'numTotalDivisional',
                    'numLateGames']
    for team in teams:
        team_names.append(team.name)
    matrix = []
    df = pd.DataFrame(matrix, columns=column_names, index=team_names)

    totalScore = 0

    for team in teams:
        teamName = team.name
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
        df.at[teamName, 'description'] = team.__str__()# TODO: this is always displaying "Major" as the league
        df.at[teamName, 'numScheduled'] = numScheduled
        df.at[teamName, 'numUnscheduled'] = numUnscheduled
        df.at[teamName, 'numDivisionalScheduled'] = numDivisionalScheduled
        df.at[teamName, 'numTotalDivisional'] = numTotalDivisional
        df.at[teamName, 'numLateGames'] = numLateGames

        totalScore = totalScore + numScheduled + numDivisionalScheduled - numUnscheduled - numLateGames

    print('---------------------------------------------------')
    print('NUMBER GAMES UNSCHEDULED: ' + str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None))))
    print('NUMBER SLOTS UNSCHEDULED: ' + str(len(Slot.objects.all().filter(game=None))))
    print('---------------------------------------------------')

    numGamesUnscheduled = str(len(Game.objects.all()) - len(Slot.objects.all().exclude(game=None)))
    numSlotsUnscheduled = len(Slot.objects.all().filter(game=None))

    return df, numGamesUnscheduled, numSlotsUnscheduled, totalScore
