from .models import League, Game, Field, Division, Team, Slot
import time
from django.db.models import Q


def generateGames():
    print('GENERATING GAMES')
    leagues = League.objects.all()
    for league in leagues:
        teams = Team.objects.all().filter(league=league)
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
    gameswithteam = Game.objects.all().filter(Q(team1=game.team1) |
                                              Q(team1=game.team2) |
                                              Q(team2=game.team1) |
                                              Q(team2=game.team2),
                                              isScheduled=True)
    score = score + len(gameswithteam) * 5
    # game is interdivisional: -20
    if game.team1.division == game.team2.division:
        score = score - 20

    game.score = score
    game.save()
    # if # games for team 1 < average scheduled for all teams:  - 20
    # if # games for team 2 < average scheduled for all teams:  - 20

def updateGameScores():
    # generateGames()
    print('UPDATING SCORES')
    t = time.time()
    score = 0
    games = Game.objects.all().filter(isScheduled=False)
    # slots = Slot.objects.all()
    for game in games:
        updateGameScore(game)

    elapsed_time = time.time()-t
    print('ELAPSED TIME:' + str(elapsed_time))

def removeSchedule():
    games = Game.objects.all().filter(isScheduled=True)
    for game in games:
        print('UNSCHEDULING' + game.__str__())
        game.isScheduled=False
        game.save()
    slots = Slot.objects.all()
    for slot in slots:
        print('UNSCHEDULING' + slot.__str__())
        slot.game = None
        slot.save()

def scheduleGame(slot, game):
    print('ATTEMPTING TO SCHEDULE GAME:  ' + game.__str__())
    print('SLOT' + slot.__str__())
    Compatible = False
    leagues = League.objects.all().filter(field=slot.field)
    for league in leagues:
        if game.league == league: Compatible = True
    if Compatible:
        print('SCHEDULING GAME')
        slot.game = game
        game.isScheduled = True
        # updateGameScore(game)
        game.save()
        # slot.isScheduled = True
        slot.save()
        updateGameScores()
        return True
    else: print('GAME NOT COMPATIBLE')
    return False


def scheduleGames():
    # generateGames()
    t = time.time()
    updateGameScores()
    print('SCHEDULING ALL GAMES')
    slots = Slot.objects.all().order_by('?')
    # need to only get slots that are not already scheduled
    # update scores
    for slot in slots:
        print(slot)

    # slots.objects.order_by('?')

    while len(Game.objects.all().filter(isScheduled=False)) >0 and len(Slot.objects.all().filter(game=None)) >0:
        for slot in slots:
            # updateGameScores()
            # get lowest scoring game
            # updateGameScores()
            # gamesSortedByLowestScore = Game.objects.order_by('score').filter(isScheduled = False)
            # This query only gets unscheduled games that are compatible with the field in the slot
            gamesSortedByLowestScore = Game.objects.order_by('score').filter(isScheduled=False, league__in=slot.field.league.all())
            # TODO: improve filter to only retrieve games that are compatible with the field
            # for game in gamesSortedByLowestScore:
            #     print(game)
            for game in gamesSortedByLowestScore:
                # updateGameScore(game)
                if len(Slot.objects.all().filter(game=game)) == 0:
                    if scheduleGame(slot, game):
                        print('game scheduled')
                        print(slot)
                        print(slot.game)
                        break
            print('---------------------------------------------------')
            print('NUMBER GAMES UNSCHEDULED: ' + str(len(Game.objects.all().filter(isScheduled=False))))
            print('NUMBER SLOTS UNSCHEDULED: ' + str(len(Slot.objects.all().filter(game=None))))
            print('---------------------------------------------------')
        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))

#     TODO: NEED TO ADD SOME SORT OF PERFORMANCE GRADE
# num games in conference
# num games per team
# num games scheduled
# num slot remaining
