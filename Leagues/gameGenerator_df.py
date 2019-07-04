from .models import League, Game, Field, Division, Team, Slot
import time
from django.db.models import Q
import pandas as pd
from django.db import connection
import numpy as np


class gameGenerator_df():
    def __init__(self):
        self.games = pd.read_sql_query(str(Game.objects.all().query), connection)
        # self.games.set_index('id', inplace=True)
        self.slots = pd.read_sql_query(str(Slot.objects.all().query), connection)
        # self.slots.set_index('id', inplace=True)
        self.fields = pd.read_sql_query(str(Field.objects.all().query), connection)
        # self.fields.set_index('id', inplace=True)
        self.teams = pd.read_sql_query(str(Team.objects.all().query), connection)
        self.teams.set_index('id', inplace=True)

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
            slots = self.slots.query('game_id.isnull()')  # .order_by('?')
            # shuffle(slots) TODO:  Need to find a way to shuffle the order
            if numberRetried > 5:
                enforceLateCap = False
            else:
                enforceLateCap = True
            for index, slot in slots.iterrows():

                # This query only gets unscheduled games that are compatible with the field in the slot, and sorts them by score (low -> high)
                gamesSortedByLowestScore = self.games[
                    ~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])].sort_values('score')
                gamesSortedByLowestScore.sort_values('score')
                # for game in gamesSortedByLowestScore:
                #     print(game)
                for index, game in gamesSortedByLowestScore.iterrows():
                    # updateGameScore(game)
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, game, enforceLateCap):
                            print('game scheduled')
                            print(slot)
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
        scheduledGames = self.slots.query('not game_id.isnull()')

        gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
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
        if len(scheduledGamesWithTeams[
                   pd.to_datetime(scheduledGamesWithTeams.time).dt.hour > 18]) > 3 and enforceLateCap:
            Compatible = False
            print('TOO MANY LATE GAMES ALREADY SCHEDULED')
        if Compatible: print('NO LATE GAME CONFLICTS')

        # ENSURE NO MORE THAN 2 GAMES PER WEEK
        # THIS NEEDS IMPLEMENTATION

        if Compatible:
            print('SCHEDULING GAME')
            slot.game_id = game.id
            self.updateGameScores_df()
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
        # games = Game.objects.all()
        # slots = Slot.objects.all()
        unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]
        for index, game in unscheduledGames.iterrows():
            self.updateGameScore_df(game)

        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))

    def updateGameScore_df(self, game):
        score = 0

        # HANDICAP REDUCED AS NUMBER OF GAMES SCHEDULED INCREASES
        scheduledGames = self.slots.query('not game_id.isnull()')
        gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                    self.games[self.games.team1_id == game.team2_id],
                                    self.games[self.games.team2_id == game.team1_id],
                                    self.games[self.games.team2_id == game.team2_id]])
        gameswithteams = gameswithteams[gameswithteams['id'].isin(scheduledGames['game_id'])]
        scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams['id'])]
        score = score + (len(scheduledGamesWithTeams) * 100)

        # INTERDIVISIONAL GAMES HAVE A HIGHER HANDICAP TO ENSURE THEY ARE SCHEDULED FIRST
        if self.teams.loc[game.team1_id]['division_id'] == self.teams.loc[game.team2_id]['division_id']:
            score = score - 80


        # GAMES WITH LOWER THAN AVERAGE NUMBER OF GAMES ARE FURTHER HANDICAPPED - PER LEAGUE
        # THE LOGIC HERE IS WRONG - NEED TO GET NUM GAMES PER TEAM
        teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
        numTeamsInLeague = len(teamsinLeague)
        gamesinLeague = self.games[self.games['league_id'] == game.league_id]
        scheduledGamesInLeague = scheduledGames[scheduledGames['game_id'].isin(gamesinLeague['id'])]
        numScheduledGamesInLeague = len(scheduledGamesInLeague)
        averageScheduledGamesInLeague = numScheduledGamesInLeague / numTeamsInLeague
        # teamsInLeague = League.objects.all().filter(league = league)
        if len(scheduledGamesWithTeams)<averageScheduledGamesInLeague:
            score = score - ((averageScheduledGamesInLeague - len(scheduledGamesWithTeams)) * 100)
        game.score = score

    def transferScheduleFromDfToObject(self):
        print('')
