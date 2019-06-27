from .models import League, Game, Field, Division, Team, Slot


def generateGames():
    # """ Create a schedule for the teams in the list and return it"""
    # N*(N-1)/2

    # byeTeam = Team("BYE","BYE","BYE","BYE")
    # if len(teams.teams) % 2 == 1: teams.addTeam(byeTeam)

    # matchups = []
    # iterator = 1
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
                # iterator = iterator + 1

    # for team1 in teams.teams:
    #     for team2 in teams.teams[iterator:]:
    #         matchups.append([team1, team2])
    #     iterator = iterator + 1
    # # print(len(matchups))
    # return matchups


# generateGames()

def updateGameScores():
    score = 0
    games = Game.objects.all()
    # slots = Slot.objects.all()
    for game in games:
        score = 0
        # len(Slot.objects.all())
        # number of scheduled games for team 1 * 5
        # number of scheduled games for team 2 * 5

        # score = score + (
        #         len(Slot.objects.all().filter(team1=game.team1)) + \
        #         len(Slot.objects.all().filter(team2=game.team1)) + \
        #         len(Slot.objects.all().filter(team1=game.team2)) + \
        #         len(Slot.objects.all().filter(team2=game.team2)) \
        #     )*5

        # game is interdivisional: -20
        if game.team1.division == game.team2.division:
            score = score - 20

        game.score = score
        game.save()
        # if # games for team 1 < average scheduled for all teams:  - 20
        # if # games for team 2 < average scheduled for all teams:  - 20

    print('')

def scheduleGame(slot,game):
    Compatible = False
    for league in slot.field.league:
        if game.league==league: Compatible=True
    if Compatible:
        slot.game = game
        slot.save()
        return True
    return False

def scheduleGames():
    slots = Slot.objects.all().filter
    # update scores
    for slot in slots:
        updateGameScores()
        # get lowest scoring game
        lowestScoringGames = Game.objects.order_by('score')
        for game in lowestScoringGames:
            if scheduleGame(slot,game):
                break

