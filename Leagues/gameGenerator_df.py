from .models import League, Game, Field, Division, Team, Slot, SiteConfiguration
import time
from datetime import timedelta
from django.db.models import Q
import pandas as pd
import tablib
from django.db import connection
from import_export import resources
import numpy as np


class gameGenerator_df():
    def __init__(self):
        self.games = pd.read_sql_query(str(Game.objects.all().order_by('?').query), connection)
        self.slots = pd.read_sql_query(str(Slot.objects.all().query), connection)
        self.slots.set_index('id', inplace=True)
        self.fields = pd.read_sql_query(str(Field.objects.all().query), connection)
        # TODO: figure out why this doesn't work - it is much clearer to use the id as an index
        self.teams = pd.read_sql_query(str(Team.objects.all().query), connection)
        self.teams.set_index('id', inplace=True)

        self.maxGamesPerDay = 1
        self.enforceLateGameCap = True
        self.maxLateGames = 1
        self.lateTimeThreshold = 18
        self.DEBUG = True
        self.daysBetween = 3

    def scheduleGames_df(self):

        # get settings
        settings = SiteConfiguration.objects.first()
        self.maxLateGames = settings.maxLateGames
        self.enforceLateGameCap = settings.enforceLateGameCap
        self.daysBetween = settings.daysBetweenGames

        t = time.time()
        self.updateGameScores_df()
        if self.DEBUG: print('SCHEDULING ALL GAMES')

        numberRetried = 0
        # lateCap = 2

        SCHEDULINGCOMPLETE = False
        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                numberRetried < 2 and \
                not SCHEDULINGCOMPLETE:

            numberRetried = numberRetried + 1
            # if numberRetried > 1:
            #     self.maxLateGames = min(self.maxLateGames + 1,6)
            #     self.daysBetween = max(self.daysBetween - 1,3)
            # self.transferScheduleFromDfToObject()
            print('-----------------------------------------------------------------------------------')
            print('-----------------------------------------------------------------------------------')
            print('                LOOP #: ' + str(numberRetried))
            print('        Max Late Games: ' + str(self.maxLateGames))
            print('   Late Game Threshold: ' + str(self.lateTimeThreshold))
            print('Min Days Between Games: ' + str(self.daysBetween))
            print('-----------------------------------------------------------------------------------')
            print('-----------------------------------------------------------------------------------')

            # if numGamesUnscheduled == len(self.games) - len(self.slots.query('not game_id.isnull()')):
            #     print('SCHEDULING COMPLETE')
            #     SCHEDULINGCOMPLETE=True
            # numGamesUnscheduled = len(self.games) - len(self.slots.query('not game_id.isnull()'))

            slots = self.slots.query('game_id.isnull()')
            slots['timeofday'] = slots['time'].dt.time
            # filter by times between 9 and 10 and sort by timestamp
            slots = slots.sort_values('time')
            slots = slots.sort_values('timeofday')

            RANDOMIZESLOTS = False
            if RANDOMIZESLOTS:
                slots = slots.sample(frac=1)

            # TODO: Need to update scores based on the slot that is being scheduled
            # TODO: If the scores are updated based on the slot, I can implement a # days between games optimization
            # TODO: Need to find the optimal score based on num slots available for each league - something nice to compare optimization

            # Iterate through every slot and try to schedule the most deserving, compatible game
            for slotIndex, slot in slots.iterrows():

                # This query only gets unscheduled games that are compatible with the field in the slot, randomizes them,
                # and sorts them by score (low -> high).  Randomizing helps prevent duplication between runs.

                # gets all unscheduled games
                unscheduledGames = self.games[
                    ~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

                # finds the leagures that the field is compatible with
                leagues = League.objects.all().filter(field__pk=slot.field_id)
                leagues_str = []
                for league in leagues:
                    leagues_str.append(league.pk)

                # removes games not compatible with the field
                unscheduledGamesInLeague = unscheduledGames[unscheduledGames['league_id'].isin(leagues_str)]

                # randomize the list of games, sorts them by score
                # unscheduledGamesInLeague = unscheduledGamesInLeague.sample(frac=1)
                # unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')

                # To speed things up, how about we only get games with teams that don't have scheduled games within 2 days of this slot
                # This is already checked in the scheduling function, but it would be faster here
                # get all scheduled games that are within 2 days of this slot
                # extract the teams in these games
                # get games that don't have any of these teams in them
                # USECOMPATIBLEGAMESLIST = True
                # if USECOMPATIBLEGAMESLIST:
                # Get all unscheduled slots
                scheduledSlots = self.slots.query('not game_id.isnull()')
                # Get all slots within time bubble
                slotsWithinTimeBubble = scheduledSlots[
                    (scheduledSlots['time'] < slot.time + timedelta(days=self.daysBetween)) & (
                            scheduledSlots['time'] > slot.time - timedelta(days=self.daysBetween))]
                # Get all games from slots within time bubble
                gamesWithinTimeBubble = self.games[
                    self.games['id'].isin(slotsWithinTimeBubble['game_id'])]
                # Get all teams from games withing time bubble
                teamsWithGamesInTimeBubble = pd.concat(
                    [gamesWithinTimeBubble.team1_id, gamesWithinTimeBubble.team2_id])
                # gat all uscheduled games minus the teams with games in time bubble
                gamesWithTeamsWithGamesOutsideTimeBubble = unscheduledGamesInLeague[
                    (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesInTimeBubble)) & (
                        ~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesInTimeBubble))]
                # randomize list of games and sort by score
                unscheduledGamesInLeague = gamesWithTeamsWithGamesOutsideTimeBubble.sample(frac=1)
                unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')

                # TODO: remove games with teams that have max number of games already scheduled

                # unscheduledGamesInLeague
                # currentLeague
                # leageMaxGames =
                # teamsWithUnscheduledGames = pd.concat(
                #     [unscheduledGamesInLeague.team1_id, unscheduledGamesInLeague.team2_id])
                # GamesWithTeamsWithNumUnscheduledGamesUnderMax = unscheduledGamesInLeague[
                #     (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesInTimeBubble)) & (
                #         ~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesInTimeBubble))]

                # if the slot is late, remove games with teams that already have late games
                # scheduledSlots = self.slots.query('not game_id.isnull()')
                # Get all slots with late games
                # slotsWithLateGames = scheduledSlots[pd.to_datetime(
                #         scheduledSlots.time).dt.hour > self.lateTimeThreshold]
                # # Get all games from slots with late games
                # gamesWithLateTimes = self.games[
                #     self.games['id'].isin(slotsWithLateGames['game_id'])]
                # # Get all teams from late games
                # teamsWithLateGames = pd.concat(
                #     [gamesWithLateTimes.team1_id, gamesWithLateTimes.team2_id])
                # teamsWithMaxLageGames =
                # gamesWithTeamsUnderMaxLateGames =
                # # gat all uscheduled games minus the teams with games in time bubble
                # gamesWithTeamsWithGamesOutsideTimeBubble = unscheduledGamesInLeague[
                #     (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesInTimeBubble)) & (
                #         ~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesInTimeBubble))]
                # teamsWithMaxLateGames =
                # gamesWithTeam1 = pd.concat([self.games[self.games.team1_id == game.team1_id],
                #                             self.games[self.games.team2_id == game.team1_id]])
                # scheduledGamesWithTeam1 = scheduledSlots[scheduledSlots['game_id'].isin(gamesWithTeam1['id'])]
                # if len(scheduledGamesWithTeam1[pd.to_datetime(
                #         scheduledGamesWithTeam1.time).dt.hour > self.lateTimeThreshold]) > self.maxLateGames:
                #     if self.DEBUG: print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeam1[
                #                                                                    pd.to_datetime(
                #                                                                        scheduledGamesWithTeam1.time).dt.hour > 18])))
                #     Compatible = False
                #     if self.DEBUG: print('TOO MANY LATE GAMES ALREADY SCHEDULED')
                #     return False

                for gameIndex, game in unscheduledGamesSortedByLowestScore.iterrows():
                    # ensure that the game is not already scheduled - this shouldn't happen but it is good to check
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, slotIndex, game, gameIndex):
                            if self.DEBUG: print('game scheduled')
                            print('-----------------------------------------------------------------------------------')
                            print('NUMBER GAMES UNSCHEDULED: ' + str(
                                len(self.games) - len(self.slots.query('not game_id.isnull()'))))
                            print('NUMBER SLOTS UNSCHEDULED: ' + str(len(self.slots.query('game_id.isnull()'))))
                            print('-----------------------------------------------------------------------------------')
                            break

        elapsed_time = time.time() - t
        if self.DEBUG: print('ELAPSED TIME:' + str(elapsed_time))
        self.transferScheduleFromDfToObject()

    def scheduleGame_df(self, slot, slotIndex, game, gameIndex):

        if self.DEBUG: print('ATTEMPTING TO SCHEDULING GAME ' + str(game.id))
        if self.DEBUG: print(Game.objects.all().filter(pk=game.id)[0])
        if self.DEBUG: print('IN SLOT: ')
        if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])

        ## These are used by many checks
        scheduledSlots = self.slots.query('not game_id.isnull()')

        gameswithteams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                    self.games[self.games.team1_id == game.team2_id],
                                    self.games[self.games.team2_id == game.team1_id],
                                    self.games[self.games.team2_id == game.team2_id]])
        gameswithteams = gameswithteams[
            gameswithteams['id'].isin(scheduledSlots['game_id'])]  ##TODO: I think this is wrong
        scheduledGamesWithTeams = scheduledSlots[scheduledSlots['game_id'].isin(gameswithteams['id'])]
        gamesWithTeam1 = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                    self.games[self.games.team2_id == game.team1_id]])
        scheduledGamesWithTeam1 = scheduledSlots[scheduledSlots['game_id'].isin(gamesWithTeam1['id'])]
        gamesWithTeam2 = pd.concat([self.games[self.games.team1_id == game.team2_id],
                                    self.games[self.games.team2_id == game.team2_id]])
        scheduledGamesWithTeam2 = scheduledSlots[scheduledSlots['game_id'].isin(gamesWithTeam2['id'])]

        Compatible = True

        ## CHECK LEAGUE COMPATIBILITY - THIS IS A LITTLE BIT OF A HACK SINCE MANYTOMANY FIELDS DON'T TRANSLATE TO DF
        ## NEED TO CHECK THE FIELD_ID AGAINST THE DJANGO OBJECT
        ## NOT NECESSARY ANYMORE SINCE ONLY GAMES THAT ARE COMPATIBLE WITH THE FIELD ARE SENT TO THIS FUNCTION
        CHECKLEAGUE = False
        if CHECKLEAGUE:
            leagues = League.objects.all().filter(field__pk=slot.field_id)
            leagues_str = []
            for league in leagues:
                leagues_str.append(league.pk)
                if game.league_id == league.pk:
                    Compatible = True
                    if self.DEBUG: print('SLOT LEAGUE IS COMPATIBLE WITH GAME')
            if not Compatible:
                if self.DEBUG: print(
                    'SLOT LEAGUE IS NOT COMPATIBLE WITH GAME: ' + str(game.league_id) + " not in " + str(leagues_str))
                Compatible = False
                return False

        ## CHECK THAT THESE TEAMS ARE NOT ALREADY SCHEDULED FOR THAT DAY
        CHECKSAMEDAY = False
        if CHECKSAMEDAY:
            if len(scheduledGamesWithTeams[pd.to_datetime(scheduledGamesWithTeams.time).dt.day == pd.to_datetime(
                    slot.time).day]) > self.maxGamesPerDay:
                Compatible = False
                if self.DEBUG: print('A TEAM ALREADY HAS A GAME SCHEDULED FOR THAT DAY')
                return False

            if Compatible:
                if self.DEBUG: print('NO GAMES ALREADY SCHEDULED ON THIS DAY WITH TEAMS')

        ## ENSURE THAT DAYS BETWEEN GAMES IS >2 days
        DISTRIBUTEGAMES = False
        if DISTRIBUTEGAMES:
            for gameIndex, scheduledGame in scheduledGamesWithTeam1.iterrows():
                thisslot = self.slots[self.slots.game_id == scheduledGame.id]
                if abs((pd.to_datetime(thisslot.time).iloc[0] - pd.to_datetime(slot.time)).days) < 2 or abs(
                        (pd.to_datetime(slot.time) - (pd.to_datetime(thisslot.time).iloc[0])).days) < 2:
                    Compatible = False
                    if self.DEBUG: print('GAMES ARE TOO CLOSE TOGETHER')
                    if self.DEBUG: print('SCHEDULED GAME:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=thisslot.index[0])[0])
                    if self.DEBUG: print('SLOT:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
                    return False

            for gameIndex, scheduledGame in scheduledGamesWithTeam2.iterrows():
                thisslot = self.slots[self.slots.game_id == scheduledGame.id]
                if abs((pd.to_datetime(thisslot.time).iloc[0] - pd.to_datetime(slot.time)).days) < 2 or abs(
                        (pd.to_datetime(slot.time) - (pd.to_datetime(thisslot.time).iloc[0])).days) < 2:
                    Compatible = False
                    if self.DEBUG: print('GAMES ARE TOO CLOSE TOGETHER')
                    if self.DEBUG: print('SCHEDULED GAME:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=thisslot.index[0])[0])
                    if self.DEBUG: print('SLOT:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
                    return False

            if Compatible:
                if self.DEBUG: print('NO GAMES SCHEDULED FOR TEAMS WITHIN 2 DAYS')

        ## ENSURE UNDER MAX GAME CAP
        CHECKMAXGAME = False
        if CHECKMAXGAME:
            if League.objects.get(id=game.league_id).maxLateGames is not None:

                if len(scheduledGamesWithTeam1) >= League.objects.get(id=game.league_id).maxLateGames:
                    Compatible = False
                    self.games.ix[gameIndex, 'score'] = 9999999
                    if self.DEBUG: print('TOO MANY GAMES ALREADY SCHEDULED FOR TEAM 1')
                    return False

                if len(scheduledGamesWithTeam2) >= League.objects.get(id=game.league_id).maxLateGames:
                    Compatible = False
                    self.games.ix[gameIndex, 'score'] = 9999999
                    if self.DEBUG: print('TOO MANY GAMES ALREADY SCHEDULED FOR TEAM 2')
                    return False

            if Compatible:
                if self.DEBUG: print('TEAMS UNDER MAX GAME CAP')

        ## ENSURE NOT TOO MANY LATE GAMES
        if self.enforceLateGameCap:
            if len(scheduledGamesWithTeam1[pd.to_datetime(
                    scheduledGamesWithTeam1.time).dt.hour > self.lateTimeThreshold]) > self.maxLateGames:
                if self.DEBUG: print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeam1[
                                                                               pd.to_datetime(
                                                                                   scheduledGamesWithTeam1.time).dt.hour > 18])))
                Compatible = False
                if self.DEBUG: print('TOO MANY LATE GAMES ALREADY SCHEDULED')
                return False

            if len(scheduledGamesWithTeam2[
                       pd.to_datetime(
                           scheduledGamesWithTeam2.time).dt.hour > self.lateTimeThreshold]) > self.maxLateGames:
                if self.DEBUG: print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeam2[
                                                                               pd.to_datetime(
                                                                                   scheduledGamesWithTeam2.time).dt.hour > 18])))
                Compatible = False
                if self.DEBUG: print('TOO MANY LATE GAMES ALREADY SCHEDULED')
                return False

        if Compatible:
            if self.DEBUG: print('NO LATE GAME CONFLICTS')

        # ENSURE NO MORE THAN 2 GAMES PER WEEK
        # THIS NEEDS IMPLEMENTATION

        scheduledSlots = self.slots.query('not game_id.isnull()')
        teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
        numTeamsInLeague = len(teamsinLeague)
        gamesinLeague = self.games[self.games['league_id'] == game.league_id]
        scheduledGamesInLeague = scheduledSlots[scheduledSlots['game_id'].isin(gamesinLeague['id'])]

        if Compatible:
            if self.DEBUG: print('SCHEDULING GAME: ' + str(game.id))
            if self.DEBUG: print(Game.objects.all().filter(pk=game.id)[0])
            if self.DEBUG: print('SLOT: ')
            if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
            self.slots.at[slotIndex, 'game_id'] = game.id
            self.updateGameScores_df(game)
            return True
        else:
            if self.DEBUG: print('GAME NOT COMPATIBLE: ' + str(game.id))
            if self.DEBUG: print(Game.objects.all().filter(pk=game.id)[0])
        return False

    def updateGameScores_df(self, game=[]):

        # generateGames()
        if self.DEBUG: print('UPDATING SCORES')
        t = time.time()
        score = 0
        unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]
        scheduledGames = self.slots.query('not game_id.isnull()')

        # Only update scores of affected games
        if len(game) > 0:
            # if self.DEBUG: print("hello")
            gamesWithTeams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            for gameIndex, game in gamesWithTeams.iterrows():
                gamesWithTeams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                            self.games[self.games.team1_id == game.team2_id],
                                            self.games[self.games.team2_id == game.team1_id],
                                            self.games[self.games.team2_id == game.team2_id]])
                self.updateGameScore_df(gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams)

        # Update scores for all games
        else:
            for gameIndex, game in unscheduledGames.iterrows():
                gamesWithTeams = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                            self.games[self.games.team1_id == game.team2_id],
                                            self.games[self.games.team2_id == game.team1_id],
                                            self.games[self.games.team2_id == game.team2_id]])
                self.updateGameScore_df(gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams)

        elapsed_time = time.time() - t
        if self.DEBUG: print('ELAPSED TIME:' + str(elapsed_time))

    def updateGameScore_df(self, gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams):

        # TODO:the games with teams, scheduled games, etc should be passed to this function and not calculated
        # each time.  This will save computing time

        if self.games.ix[gameIndex, 'score'] == 9999999: return

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
        if self.DEBUG: print('POPULATING GAMES')

        scheduledGames = self.slots.query('not game_id.isnull()')
        for index, slot in scheduledGames.iterrows():
            game = Game.objects.all().filter(pk=slot.game_id)[0]
            dbslot = Slot.objects.all().filter(pk=index)[0]
            dbslot.game = game
            dbslot.save()
