from .models import League, Game, Field, Division, Team


def generateGames():
    # """ Create a schedule for the teams in the list and return it"""
    # N*(N-1)/2

    # byeTeam = Team("BYE","BYE","BYE","BYE")
    # if len(teams.teams) % 2 == 1: teams.addTeam(byeTeam)

    # matchups = []
    iterator = 1
    leagues = League.objects.all()
    for league in leagues:
        teams = Team.objects.all().filter(league=league)
        for team1 in teams:
            for team2 in teams:
                checkTeam1 = Game.objects.all().filter(team1=team1, team2=team2)
                checkTeam2 = Game.objects.all().filter(team1=team2, team2=team1)
                if (len(checkTeam1) + len(checkTeam2) == 0) and team1 != team2:
                    game = Game(team1=team1, team2=team2)
                    game.save()
                iterator = iterator + 1

    # for team1 in teams.teams:
    #     for team2 in teams.teams[iterator:]:
    #         matchups.append([team1, team2])
    #     iterator = iterator + 1
    # # print(len(matchups))
    # return matchups

# generateGames()
