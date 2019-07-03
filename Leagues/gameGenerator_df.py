from .models import League, Game, Field, Division, Team, Slot
import time
from django.db.models import Q
import pandas as pd
from django.db import connection
import numpy as np

class gameGenerator_df():
    def __init__(self):
        self.games = pd.read_sql_query(str(Game.objects.all().query), connection)
        self.slots = pd.read_sql_query(str(Slot.objects.all().query), connection)
        self.fields = pd.read_sql_query(str(Field.objects.all().query), connection)

    def scheduleGames_df(self):
        # generateGames()

        t = time.time()
        self.updateGameScores_df()
        print('SCHEDULING ALL GAMES')

        numberRetried = 0

        unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                numberRetried < 10:
            numberRetried = numberRetried + 1
            slots = self.slots.query('game_id.isnull()')#.order_by('?')
            # shuffle(slots) TODO:  Need to find a way to shuffle the order
            if numberRetried > 5:
                enforceLateCap = False
            else:
                enforceLateCap = True
            for index, slot in slots.iterrows():

                # This query only gets unscheduled games that are compatible with the field in the slot, and sorts them by score (low -> high)
                print('')

                # gamesSortedByLowestScore = Game.objects.order_by('score'). \
                #     exclude(id__in=Slot.objects.all().exclude(game=None).values_list('game')). \
                #     filter(league__in=slot.field.league.all())
                gamesSortedByLowestScore = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])].sort_values('score')
                gamesSortedByLowestScore.sort_values('score')
                # for game in gamesSortedByLowestScore:
                #     print(game)
                for index, game in gamesSortedByLowestScore.iterrows():
                    # updateGameScore(game)
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, game, enforceLateCap):
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


    def scheduleGame_df(self, slot, game, enforceLateCap):
        print('ATTEMPTING TO SCHEDULE GAME:  ' + game.__str__())
        print('SLOT' + slot.__str__())
        Compatible = False

        ## CHECK LEAGUE COMPATIBILITY - THIS IS A LITTLE BIT OF A HACK SINCE MANYTOMANY FIELDS DON'T TRANSLATE TO DF
        ## NEED TO CHECK THE FIELD_ID AGAINST THE DJANGO OBJECT
        leagues = League.objects.all().filter(field__pk=slot.field_id)
        for league in leagues:
            if game.league_id == league.pk:
                Compatible = True
                print('SLOT LEAGUE IS COMPATIBLE WITH GAME')
        if not Compatible: print('SLOT LEAGUE IS NOT COMPATIBLE WITH GAME')
        # Find all scheduled games and ensure that this game is not on the same day
        # get all games
        # loop through all games to get teams that match teams in this game


        scheduledGames = self.slots.query('not game_id.isnull()')

        gameswithteams=pd.concat([self.games[self.games.team1_id == game.team1_id],
                                  self.games[self.games.team1_id == game.team2_id],
                                  self.games[self.games.team2_id == game.team1_id],
                                  self.games[self.games.team2_id == game.team2_id]])
        gameswithteams = gameswithteams[gameswithteams['id'].isin(scheduledGames['game_id'])]
        scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams['id'])]
        if len(scheduledGamesWithTeams[scheduledGamesWithTeams.time == slot.time]) > 0:
            Compatible = False
            print('A TEAM ALREADY HAS A GAME SCHEDULED FOR THAT DAY')
        if Compatible: print('NO GAMES ALREADY SCHEDULED ON THIS DAY WITH TEAMS')

        ## ENSURE NO MORE THAN 2 LATE GAMES
        if len(scheduledGamesWithTeams[pd.to_datetime(scheduledGamesWithTeams.time).dt.hour > 18]) > 3:
            Compatible = False
            print('TOO MANY LATE GAMES ALREADY SCHEDULED')
        if Compatible: print('NO LATE GAME CONFLICTS')

        # teams = [game.team1, game.team2]
        # if slot.time.hour > 18 and enforceLateCap:
        #     for team_ in teams:
        #         # numLateGames=0
        #         # slotswithteams = Slot.objects.all().filter(Q(game__team1=team_) |
        #         #                                       Q(game__team2=team_))
        #         # for slot_ in slotswithteams:
        #         #     if slot_.time.hour > 18: numLateGames=numLateGames+1
        #         # if numLateGames>=2:
        #         #     Compatible = False
        #         #     print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR ', team_.name)
        #         if len(Slot.objects.all().filter(Q(game__team1=team_) | Q(game__team2=team_), time__hour__gt=18)) >= 2:
        #             Compatible = False
        #             print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR ', team_.name)
        # if Compatible: print('NO LATE GAME CONFLICTS')

        # ENSURE NO MORE THAN 2 GAMES PER WEEK

        if Compatible:
            print('SCHEDULING GAME')
            slot.game = game
            # game.isScheduled = True
            # game.save()
            slot.save()
            updateGameScores_df()
            return True
        else:
            print('GAME NOT COMPATIBLE')
        return False


    def updateGameScores_df(self):

        # generateGames()
        print('UPDATING SCORES')
        t = time.time()
        score = 0
        # games = Game.objects.all().filter(isScheduled=False)
        games = Game.objects.all()
        # slots = Slot.objects.all()
        for game in games:
            if len(Slot.objects.all().filter(game=game)) == 0:
                self.updateGameScore_df(game)
                game.save()

        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))


    def updateGameScore_df(self,game):
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


    def transferScheduleFromDfToObject(self):
        print('')
