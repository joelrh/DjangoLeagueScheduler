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

        self.maxGamesPerDay = 1
        self.maxLateGames = 2
        self.lateTimeThreshold = 18

    def scheduleGames_df(self):
        # generateGames()

        t = time.time()
        self.updateGameScores_df()
        print('SCHEDULING ALL GAMES')

        numberRetried = 0
        # lateCap = 2

        # unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                numberRetried < 10:
            numberRetried = numberRetried + 1
            slots = self.slots.query('game_id.isnull()')
            # shuffledSlots = slots.sample(frac=1)
            # slots2=slots
            # slots['time'] = pd.to_datetime(slots['time'])
            # put the timestamp part of the datetime into a separate column
            slots['timeofday'] = slots['time'].dt.time
            # filter by times between 9 and 10 and sort by timestamp
            slots = slots.sort_values('time')
            slots = slots.sort_values('timeofday')

            # TODO: Need to update scores based on the slot that is being scheduled
            # TODO: If the scores are updated based on the slot, I can implement a # days between games optimization
            # TODO: Need to find the optimal score based on num slots available for each league - something nice to compare optimization

            if numberRetried > 5:
                self.lateTimeThreshold = self.lateTimeThreshold + 1

            print('LATE CAP: ', str(self.lateTimeThreshold))
            for slotIndex, slot in slots.iterrows():

                # This query only gets unscheduled games that are compatible with the field in the slot, randomizes them,
                # and sorts them by score (low -> high)
                unscheduledGames = self.games[
                    ~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

                leagues = League.objects.all().filter(field__pk=slot.field_id)
                leagues_str = []
                for league in leagues:
                    leagues_str.append(league.pk)
                unscheduledGamesInLeague = unscheduledGames[unscheduledGames['league_id'].isin(leagues_str)]
                unscheduledGamesInLeague = unscheduledGamesInLeague.sample(frac=1)
                unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')
                # print(unscheduledGamesSortedByLowestScore)

                for gameIndex, game in unscheduledGamesSortedByLowestScore.iterrows():
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, slotIndex, game):
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

    def scheduleGame_df(self, slot, slotIndex, game):

        print('ATTEMPTING TO SCHEDULING GAME ' + str(game.id))
        print(Game.objects.all().filter(pk=game.id)[0])
        print('IN SLOT: ')
        print(Slot.objects.all().filter(pk=slotIndex)[0])

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
        # if len(scheduledGamesWithTeams[scheduledGamesWithTeams.time == slot.time]) > 0:
        if len(scheduledGamesWithTeams[pd.to_datetime(scheduledGamesWithTeams.time).dt.day == pd.to_datetime(slot.time).day]) > self.maxGamesPerDay:
            Compatible = False
            print('A TEAM ALREADY HAS A GAME SCHEDULED FOR THAT DAY')
        if Compatible: print('NO GAMES ALREADY SCHEDULED ON THIS DAY WITH TEAMS')

        ## ENSURE NOT TOO MANY LATE GAMES
        if len(scheduledGamesWithTeams[
                   pd.to_datetime(scheduledGamesWithTeams.time).dt.hour > self.lateTimeThreshold]) > self.maxLateGames * 2:
            print('Cumulative limit: ' + str(self.maxLateGames * 2))
            print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeams[
                                                            pd.to_datetime(
                                                                scheduledGamesWithTeams.time).dt.hour > 18])))
            Compatible = False
            print('TOO MANY LATE GAMES ALREADY SCHEDULED')
        if Compatible: print('NO LATE GAME CONFLICTS')

        # ENSURE NO MORE THAN 2 GAMES PER WEEK
        # THIS NEEDS IMPLEMENTATION

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
        scheduledGames = self.slots.query('not game_id.isnull()')

        for gameIndex, game in unscheduledGames.iterrows():
            gamesWithTeams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            self.updateGameScore_df(gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams)

        elapsed_time = time.time() - t
        print('ELAPSED TIME:' + str(elapsed_time))

    def updateGameScore_df(self, gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams):

        # TODO:the games with teams, scheduled games, etc should be passed to this function and not calculated
        # each time.  This will save computing time

        SCHEDULEDGAMEPENALTY = False
        UNCHEDULEDGAMEHANDICAP = True
        MORETHANMINIMUMLEAGUESCHEDULEPENALTY = False
        INTERDIVISIONALHANDICAP = True
        LOWERTHANAVERAGESCHEDULEPENALTY = False

        score = 0

        # HANDICAP REDUCED AS NUMBER OF GAMES SCHEDULED INCREASES
        if SCHEDULEDGAMEPENALTY:
            gameswithteams2 = gamesWithTeams[gamesWithTeams['id'].isin(scheduledGames['game_id'])]
            scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams2['id'])]
            score = score + (len(scheduledGamesWithTeams) * 100)

        # HANDICAP REDUCED AS NUMBER OF UNSCHEDULED GAMES DECREASES
        if UNCHEDULEDGAMEHANDICAP:
            unscheduledgameswithteams = gamesWithTeams[gamesWithTeams['id'].isin(unscheduledGames['id'])]
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
            gameswithteams2 = gamesWithTeams[gamesWithTeams['id'].isin(scheduledGames['game_id'])]
            scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams2['id'])]
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
