from .models import League, Game, Field, Division, Team, Slot
import time
from django.db.models import Q
import pandas as pd
from django.db import connection
import numpy as np


class gameGenerator_df():
    def __init__(self):
        self.games = pd.read_sql_query(str(Game.objects.all().order_by('?').query), connection)
        # self.games.set_index('id', inplace=True)
        # self.slots = pd.read_sql_query(str(Slot.objects.all().order_by('?').query), connection)
        self.slots = pd.read_sql_query(str(Slot.objects.all().query), connection)
        self.slots.set_index('id', inplace=True)
        self.fields = pd.read_sql_query(str(Field.objects.all().query), connection)
        # self.fields.set_index('id', inplace=True)
        # TODO: figure out why this doesn't work - it is much clearer to use the id as an index
        self.teams = pd.read_sql_query(str(Team.objects.all().query), connection)
        self.teams.set_index('id', inplace=True)

    def scheduleGames_df(self):
        # generateGames()

        t = time.time()
        self.updateGameScores_df()
        print('SCHEDULING ALL GAMES')

        numberRetried = 0
        lateCap = 2

        # unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                numberRetried < 10:
            numberRetried = numberRetried + 1
            slots = self.slots.query('game_id.isnull()')
            shuffledSlots = slots.sample(frac=1)
            # TODO:  NEED TO RANK SLOTS BASED ON TIME/DAY.  THIS WILL HELP ENSURE MOST IMPORTANT GAMES ARE SCHEDULED ON THE BEST SLOTS

            # TODO: make the late cap increase gradually to prevent over scheduling one team to late slots

            if numberRetried > 5:
                lateCap = lateCap + 1

            print('LATE CAP: ', str(lateCap))
            for slotIndex, slot in shuffledSlots.iterrows():

                # This query only gets unscheduled games that are compatible with the field in the slot, randomizes them,
                # and sorts them by score (low -> high)
                unscheduledGames = self.games[
                    ~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

                leagues = League.objects.all().filter(field__pk=slot.field_id)
                leagues_str = []
                for league in leagues:
                    leagues_str.append(league.pk)
                unscheduledGamesInLeague = unscheduledGames[
                    unscheduledGames['league_id'].isin(leagues_str)]
                unscheduledGamesInLeague = unscheduledGamesInLeague.sample(frac=1)
                unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')
                # print(unscheduledGamesSortedByLowestScore)

                for gameIndex, game in unscheduledGamesSortedByLowestScore.iterrows():
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, slotIndex, game, lateCap):
                            print('game scheduled')
                            break
                print('---------------------------------------------------')
                print('NUMBER GAMES UNSCHEDULED: ' + str(
                    len(self.games) - len(self.slots.query('not game_id.isnull()'))))
                print('NUMBER SLOTS UNSCHEDULED: ' + str(len(self.slots.query('game_id.isnull()'))))
                print('---------------------------------------------------')
        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))
        self.transferScheduleFromDfToObject()

    def scheduleGame_df(self, slot, slotIndex, game, lateCap):
        Compatible = False

        ## CHECK LEAGUE COMPATIBILITY - THIS IS A LITTLE BIT OF A HACK SINCE MANYTOMANY FIELDS DON'T TRANSLATE TO DF
        ## NEED TO CHECK THE FIELD_ID AGAINST THE DJANGO OBJECT
        ## NOT NECESSARY ANYMORE SINCE ONLY GAMES THAT ARE COMPATIBLE WITH THE FIELD ARE SENT TO THIS FUNCTION
        leagues = League.objects.all().filter(field__pk=slot.field_id)
        leagues_str = []
        for league in leagues:
            leagues_str.append(league.pk)
            if game.league_id == league.pk:
                Compatible = True
                print('SLOT LEAGUE IS COMPATIBLE WITH GAME')
        if not Compatible:
            print('SLOT LEAGUE IS NOT COMPATIBLE WITH GAME: ' + str(game.league_id) + " not in " + str(leagues_str))

        # Find all scheduled games and ensure that this game is not on the same day
        scheduledSlots = self.slots.query('not game_id.isnull()')

        gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                    self.games[self.games.team1_id == game.team2_id],
                                    self.games[self.games.team2_id == game.team1_id],
                                    self.games[self.games.team2_id == game.team2_id]])
        gameswithteams = gameswithteams[
            gameswithteams['id'].isin(scheduledSlots['game_id'])]  ##TODO: I think this is wrong
        scheduledGamesWithTeams = scheduledSlots[scheduledSlots['game_id'].isin(gameswithteams['id'])]
        if len(scheduledGamesWithTeams[scheduledGamesWithTeams.time == slot.time]) > 0:
            Compatible = False
            print('A TEAM ALREADY HAS A GAME SCHEDULED FOR THAT DAY')
        if Compatible: print('NO GAMES ALREADY SCHEDULED ON THIS DAY WITH TEAMS')

        ## ENSURE NO MORE THAN 2 LATE GAMES
        if len(scheduledGamesWithTeams[
                   pd.to_datetime(scheduledGamesWithTeams.time).dt.hour > 18]) > lateCap * 2:
            print('Cumulative limit: ' + str(lateCap * 2))
            print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeams[
                                                            pd.to_datetime(
                                                                scheduledGamesWithTeams.time).dt.hour > 18])))
            Compatible = False
            print('TOO MANY LATE GAMES ALREADY SCHEDULED')
        if Compatible: print('NO LATE GAME CONFLICTS')

        # ENSURE NO MORE THAN 2 GAMES PER WEEK
        # THIS NEEDS IMPLEMENTATION

        # ENSURE THAT GAME IS NOT SCHEDULED IF THE LOWEST NUMBER OF GAMES SCHEDULED FOR A TEAM IS > 1 GREATER
        # THIS SHOULD BE ON THE SCORING SIDE
        # minNumberScheduledInLeague = 999
        # teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
        # for indexTeam, team in teamsinLeague.iterrows():
        #     gameswithteam = pd.concat([self.games[self.games.team1_id == indexTeam],
        #                                 self.games[self.games.team2_id == indexTeam]]) #Would like to use team.id
        #     scheduledGamesWithTeam = gameswithteam[gameswithteam['id'].isin(scheduledSlots['game_id'])]
        #     if len(scheduledGamesWithTeam)<minNumberScheduledInLeague:
        #         minNumberScheduledInLeague=len(scheduledGamesWithTeam)
        # gameswithteam1 = pd.concat([self.games[self.games.team1_id == game.team1_id],
        #                            self.games[self.games.team2_id == game.team1_id]])
        # scheduledGamesWithTeam1 = gameswithteam1[gameswithteam1['id'].isin(scheduledSlots['game_id'])]
        # gameswithteam2 = pd.concat([self.games[self.games.team1_id == game.team2_id],
        #                             self.games[self.games.team2_id == game.team2_id]])
        # scheduledGamesWithTeam2 = gameswithteam2[gameswithteam2['id'].isin(scheduledSlots['game_id'])]
        # if len(scheduledGamesWithTeam1) - minNumberScheduledInLeague > 1 and len(scheduledGamesWithTeam2) - minNumberScheduledInLeague > 1:
        #     print('scheduled games with team1: '+str(len(scheduledGamesWithTeam1)))
        #     print('scheduled games with team2: ' + str(len(scheduledGamesWithTeam2)))
        #     print('minimum num scheduled games for a team in this league: '+str(minNumberScheduledInLeague))
        #     Compatible=False
        #     print('Team already has too many scheduled games relative to other teams in league')

        scheduledSlots = self.slots.query('not game_id.isnull()')
        teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
        numTeamsInLeague = len(teamsinLeague)
        gamesinLeague = self.games[self.games['league_id'] == game.league_id]
        scheduledGamesInLeague = scheduledSlots[scheduledSlots['game_id'].isin(gamesinLeague['id'])]

        if Compatible:
            print('SCHEDULING GAME ' + str(game.id))
            print(Game.objects.all().filter(pk=game.id)[0])
            print('SLOT: ')
            print(Slot.objects.all().filter(pk=slotIndex)[0])
            self.slots.at[slotIndex, 'game_id'] = game.id
            self.updateGameScores_df()
            return True
        else:
            print('GAME NOT COMPATIBLE: ' + str(game.id))
            print(Game.objects.all().filter(pk=game.id)[0])
        return False

    def updateGameScores_df(self):

        # generateGames()
        print('UPDATING SCORES')
        t = time.time()
        score = 0
        unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]
        for gameIndex, game in unscheduledGames.iterrows():
            self.updateGameScore_df(gameIndex, game)

        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))

    def updateGameScore_df(self, gameIndex, game):

        # if game.team1_id == 2 or game.team2_id == 2:
        #     print('yankees')

        SCHEDULEDGAMEPENALTY = True
        UNCHEDULEDGAMEHANDICAP = True
        MORETHANMINIMUMLEAGUESCHEDULEPENALTY = True
        INTERDIVISIONALHANDICAP = True
        LOWERTHANAVERAGESCHEDULEPENALTY = True

        score = 0

        # HANDICAP REDUCED AS NUMBER OF GAMES SCHEDULED INCREASES
        if SCHEDULEDGAMEPENALTY:
            scheduledGames = self.slots.query('not game_id.isnull()')
            gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            gameswithteams = gameswithteams[gameswithteams['id'].isin(scheduledGames['game_id'])]
            scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams['id'])]
            score = score + (len(scheduledGamesWithTeams) * 100)

        # HANDICAP REDUCED AS NUMBER OF UNSCHEDULED GAMES DECREASES
        if UNCHEDULEDGAMEHANDICAP:
            unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]
            gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            unscheduledgameswithteams = gameswithteams[gameswithteams['id'].isin(unscheduledGames['id'])]
            # unscheduledGamesWithTeams = unscheduledGames[unscheduledGames['game_id'].isin(gameswithteams['id'])]
            score = score - (len(unscheduledgameswithteams) * 200)

        # ENSURE THAT GAME IS NOT SCHEDULED IF THE LOWEST NUMBER OF GAMES SCHEDULED FOR A TEAM IS > 1 GREATER
        if MORETHANMINIMUMLEAGUESCHEDULEPENALTY:
            scheduledSlots = self.slots.query('not game_id.isnull()')
            minNumberScheduledInLeague = 999
            teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
            for indexTeam, team in teamsinLeague.iterrows():
                gameswithteam = pd.concat([self.games[self.games.team1_id == indexTeam],
                                           self.games[self.games.team2_id == indexTeam]])  # Would like to use team.id
                scheduledGamesWithTeam = gameswithteam[gameswithteam['id'].isin(scheduledSlots['game_id'])]
                if len(scheduledGamesWithTeam) < minNumberScheduledInLeague:
                    minNumberScheduledInLeague = len(scheduledGamesWithTeam)
            gameswithteam1 = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team1_id]])
            scheduledGamesWithTeam1 = gameswithteam1[gameswithteam1['id'].isin(scheduledSlots['game_id'])]
            gameswithteam2 = pd.concat([self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            scheduledGamesWithTeam2 = gameswithteam2[gameswithteam2['id'].isin(scheduledSlots['game_id'])]
            if len(scheduledGamesWithTeam1) - minNumberScheduledInLeague > 1 or len(
                    scheduledGamesWithTeam2) - minNumberScheduledInLeague > 1:
                score = score + 100

        # INTERDIVISIONAL GAMES HAVE A HIGHER HANDICAP TO ENSURE THEY ARE SCHEDULED FIRST
        if INTERDIVISIONALHANDICAP:
            if self.teams.loc[game.team1_id]['division_id'] == self.teams.loc[game.team2_id]['division_id']:
                score = score - 200

        # GAMES WITH LOWER THAN AVERAGE NUMBER OF GAMES ARE FURTHER HANDICAPPED - PER LEAGUE
        # THE LOGIC HERE IS WRONG - NEED TO GET NUM GAMES PER TEAM
        if LOWERTHANAVERAGESCHEDULEPENALTY:
            teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
            numTeamsInLeague = len(teamsinLeague)
            gamesinLeague = self.games[self.games['league_id'] == game.league_id]
            scheduledGamesInLeague = scheduledGames[scheduledGames['game_id'].isin(gamesinLeague['id'])]
            numScheduledGamesInLeague = len(scheduledGamesInLeague)
            averageScheduledGamesInLeaguePerTeam = numScheduledGamesInLeague * 2 / numTeamsInLeague
            if len(scheduledGamesWithTeams) < averageScheduledGamesInLeaguePerTeam:
                score = score - ((averageScheduledGamesInLeaguePerTeam - len(scheduledGamesWithTeams)) * 100)

        self.games.ix[gameIndex, 'score'] = score

    def transferScheduleFromDfToObject(self):
        print('')

        scheduledGames = self.slots.query('not game_id.isnull()')
        for index, slot in scheduledGames.iterrows():
            game = Game.objects.all().filter(pk=slot.game_id)[0]
            dbslot = Slot.objects.all().filter(pk=index)[0]
            dbslot.game = game
            dbslot.save()
