from .models import League, Game, Field, Division, Team, Slot
import time
from datetime import timedelta
from django.db.models import Q
import pandas as pd
import tablib
from django.db import connection
from import_export import resources
import numpy as np


# def importData():
#     my_dataset = tablib.Dataset(headers=['id', 'name','description','league','division'])
#     my_dataset.xlsx = open('data\Team-2019-07-26.xlsx', 'rb').read()
#     if self.DEBUG: print(my_dataset)
#     team_resource = resources.modelresource_factory(model=Team)()
#     # dataset = tablib.Dataset(headers=['id', 'name','description','league','division'])
#     result = team_resource.import_data(my_dataset, dry_run=True)
#     if self.DEBUG: print(result.has_errors())
#     result = team_resource.import_data(my_dataset, dry_run=False)

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
        self.maxLateGames = 1
        self.lateTimeThreshold = 18
        self.DEBUG = True
        self.daysBetween = 3

    def scheduleGames_df(self):
        # generateGames()

        t = time.time()
        self.updateGameScores_df()
        if self.DEBUG: print('SCHEDULING ALL GAMES')

        numberRetried = 0
        # lateCap = 2

        # unscheduledGames = self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]
        numGamesUnscheduled = 0
        SCHEDULINGCOMPLETE = False
        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                numberRetried < 10 and \
                not SCHEDULINGCOMPLETE:

            numberRetried = numberRetried + 1
            if numberRetried > 1:
                self.maxLateGames = min(self.maxLateGames + 1,5)
                self.daysBetween = max(self.daysBetween - 1,1)
                # self.transferScheduleFromDfToObject()
            print('-----------------------------------------------------------------------------------')
            print('-----------------------------------------------------------------------------------')
            print('                LOOP #: ' + str(numberRetried))
            print('        Max Late Games: ' + str(self.maxLateGames))
            print('Min Days Between Games: ' + str(self.daysBetween))
            print('-----------------------------------------------------------------------------------')
            print('-----------------------------------------------------------------------------------')

            # if numGamesUnscheduled == len(self.games) - len(self.slots.query('not game_id.isnull()')):
            #     print('SCHEDULING COMPLETE')
            #     SCHEDULINGCOMPLETE=True
            # numGamesUnscheduled = len(self.games) - len(self.slots.query('not game_id.isnull()'))

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



            # if self.DEBUG: print('LATE CAP: ', str(self.lateTimeThreshold))

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
                unscheduledGamesInLeague = unscheduledGamesInLeague.sample(frac=1)
                unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')

                # To speed things up, how about we only get games with teams that don't have scheduled games within 2 days of this slot
                # This is already checked in the scheduling function, but it would be faster here
                # get all scheduled games that are within 2 days of this slot
                # extract the teams in these games
                # get games that don't have any of these teams in them
                USECOMPATIBLEGAMESLIST = True
                if USECOMPATIBLEGAMESLIST:
                    scheduledSlots = self.slots.query('not game_id.isnull()')
                    slotsWithinTimeBubble = scheduledSlots[(scheduledSlots['time'] < slot.time + timedelta(days=self.daysBetween)) & (
                            scheduledSlots['time'] > slot.time - timedelta(days=self.daysBetween))]
                    gamesWithinTimeBubble_REMOVE = self.games[
                        self.games['id'].isin(slotsWithinTimeBubble['game_id'])]
                    gamesWithinTimeBubble = self.games[
                        self.games['id'].isin(slotsWithinTimeBubble['game_id'])]
                    teamsWithGamesInTimeBubble = pd.concat(
                        [gamesWithinTimeBubble.team1_id, gamesWithinTimeBubble.team2_id])
                    gamesWithTeamsWithGamesOutsideTimeBubble = unscheduledGamesInLeague[
                        (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesInTimeBubble)) & (
                            ~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesInTimeBubble))]
                    unscheduledGamesInLeague = gamesWithTeamsWithGamesOutsideTimeBubble.sample(frac=1)
                    unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')

                for gameIndex, game in unscheduledGamesSortedByLowestScore.iterrows():
                    # ensure that the game is not already scheduled - this shouldn't happen but it is good to check
                    if len(self.slots[self.slots.game_id == game.id]) == 0:
                        if self.scheduleGame_df(slot, slotIndex, game):
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

    def scheduleGame_df(self, slot, slotIndex, game):

        if self.DEBUG: print('ATTEMPTING TO SCHEDULING GAME ' + str(game.id))
        if self.DEBUG: print(Game.objects.all().filter(pk=game.id)[0])
        if self.DEBUG: print('IN SLOT: ')
        if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])

        Compatible = True

        ## CHECK LEAGUE COMPATIBILITY - THIS IS A LITTLE BIT OF A HACK SINCE MANYTOMANY FIELDS DON'T TRANSLATE TO DF
        ## NEED TO CHECK THE FIELD_ID AGAINST THE DJANGO OBJECT
        ## NOT NECESSARY ANYMORE SINCE ONLY GAMES THAT ARE COMPATIBLE WITH THE FIELD ARE SENT TO THIS FUNCTION
        CHECKLEAGUE = True
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
        ##TODO: preventing scheduling on same day is not working
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
            GamesWithTeam1 = pd.concat([self.games[self.games.team1_id == game.team1_id],
                                        self.games[self.games.team2_id == game.team1_id]])
            scheduledGamesWithTeam1 = GamesWithTeam1[GamesWithTeam1['id'].isin(scheduledSlots['game_id'])]
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

            GamesWithTeam2 = pd.concat([self.games[self.games.team1_id == game.team2_id],
                                        self.games[self.games.team2_id == game.team2_id]])
            scheduledGamesWithTeam2 = GamesWithTeam2[GamesWithTeam2['id'].isin(scheduledSlots['game_id'])]
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

        ## ENSURE NOT TOO MANY LATE GAMES
        if len(scheduledGamesWithTeams[
                   pd.to_datetime(
                       scheduledGamesWithTeams.time).dt.hour > self.lateTimeThreshold]) > self.maxLateGames * 2:
            if self.DEBUG: print('Cumulative limit: ' + str(self.maxLateGames * 2))
            if self.DEBUG: print('Num scheduled for teams: ' + str(len(scheduledGamesWithTeams[
                                                                           pd.to_datetime(
                                                                               scheduledGamesWithTeams.time).dt.hour > 18])))
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
            # self.updateGameScores_df()
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
                # self.updateGameScore_df(gameIndex, game, unscheduledGames, scheduledGames, gamesWithTeams)
                # gameIndex = self.games.index[self.games['id'] == game.id]
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

        SCHEDULEDGAMEPENALTY = False
        UNCHEDULEDGAMEHANDICAP = True
        MORETHANMINIMUMLEAGUESCHEDULEPENALTY = False
        INTERDIVISIONALHANDICAP = True
        LOWERTHANAVERAGESCHEDULEPENALTY = False
        SPACEBETWEENGAMES = False  # implemented at a higher level

        score = 0

        # HANDICAP REDUCES AS GAMES ARE FURTHER APART
        # if SPACEBETWEENGAMES:
        #
        #     if self.DEBUG: print('')

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
