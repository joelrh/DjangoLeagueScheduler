import sys

from .models import League, Game, Field, Division, Team, Slot, BODate, SiteConfiguration
import time
from time import sleep
from progress.bar import IncrementalBar
from progressbar import ProgressBar
from alive_progress import alive_bar
from datetime import timedelta
from tqdm import tqdm
from django.db.models import Q
import pandas as pd
import tablib
from django.db import connection
from import_export import resources
import numpy as np
import math
import enlighten




class gameGenerator_df():
    def __init__(self):
        self.games = pd.read_sql_query(str(Game.objects.all().order_by('?').query), connection) #This randomizes games
        #self.games = pd.read_sql_query(str(Game.objects.all().query), connection)
        self.slots = pd.read_sql_query(str(Slot.objects.all().query), connection)
        self.slots.set_index('id', inplace=True)
        self.fields = pd.read_sql_query(str(Field.objects.all().query), connection)
        # TODO: figure out why this doesn't work - it is much clearer to use the id as an index
        self.BODate = pd.read_sql_query(str(BODate.objects.all().query), connection)
        self.BODate.set_index('id', inplace=True)
        self.teams = pd.read_sql_query(str(Team.objects.all().query), connection)
        self.teams.set_index('id', inplace=True)
        self.leagues = pd.read_sql_query(str(Slot.objects.all().query), connection)
        self.leagues.set_index('id', inplace=True)

        self.maxGamesPerDay = 1
        self.enforceLateGameCap = True
        self.maxLateGames = 1
        self.lateTimeThreshold = 18
        self.DEBUG = False
        self.daysBetween = 0
        self.coachOverlapTime = 0  # in minutes

    def progressBar(self,value, endvalue, bar_length=20):

        percent = float(value) / endvalue
        arrow = '-' * int(round(percent * bar_length) - 1) + '>'
        spaces = ' ' * (bar_length - len(arrow))

        sys.stdout.write("\rPercent: [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
        sys.stdout.flush()
        if value == endvalue:
            print('');
            print('-----------------------------------------------------------------------------------')
            print('NUMBER GAMES UNSCHEDULED: ' + str(
                len(self.games) - len(self.slots.query('not game_id.isnull()'))))
            print('NUMBER SLOTS UNSCHEDULED: ' + str(len(self.slots.query('game_id.isnull()'))))
            print('-----------------------------------------------------------------------------------')

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
        useSecondaryLeague = False
        removeUnderUtilizedSlotDays = False
        # lateCap = 2

        SCHEDULINGCOMPLETE = False
        while len(self.games[~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]) > 0 and \
                len(self.slots.query('game_id.isnull()')) > 0 and \
                not numberRetried == 1 and \
                not SCHEDULINGCOMPLETE:

            numberRetried = numberRetried + 1

            # The first pass uses the max days between and primary league
            # the next pass uses the secondary and reduces days between
            if numberRetried > 1:
                useSecondaryLeague = True
                self.daysBetween = max(self.daysBetween - 1, 0)



            if self.DEBUG: print('-----------------------------------------------------------------------------------')
            if self.DEBUG: print('-----------------------------------------------------------------------------------')
            if self.DEBUG: print('                LOOP #: ' + str(numberRetried))
            if self.DEBUG: print('   Late Game Threshold: ' + str(self.lateTimeThreshold))
            if self.DEBUG: print('-----------------------------------------------------------------------------------')
            if self.DEBUG: print('-----------------------------------------------------------------------------------')

            # The third pass will go through and remove all scheduled games on underutilized days
            scheduledSlots = self.slots.query('not game_id.isnull()')
            unscheduledSlots = self.slots.query('game_id.isnull()')
            removeUnderUtilizedSlotDays=False
            if numberRetried == 3 and removeUnderUtilizedSlotDays:
                for slotIndex, slot in self.slots.iterrows():
                    if self.DEBUG: print(slot)
                    slotsOnSameDay = self.slots[
                        pd.to_datetime(self.slots.time).dt.date == slot.time.date()]
                    scheduledSlotsonSameDay = scheduledSlots[
                        pd.to_datetime(scheduledSlots.time).dt.date == slot.time.date()]
                    unscheduledSlotsonSameDay = unscheduledSlots[
                        pd.to_datetime(unscheduledSlots.time).dt.date == slot.time.date()]
                    # print('slotsOnSameDay scheduledSlotsonSameDay unscheduledSlotsonSameDay')
                    # print(str(len(slotsOnSameDay)) + " " + str(len(scheduledSlotsonSameDay)) + " " + str(
                    #     len(unscheduledSlotsonSameDay)))
                    if len(slotsOnSameDay) > 0:
                        # print('ratio: ' + str(len(scheduledSlotsonSameDay) / len(slotsOnSameDay)))
                        if len(scheduledSlotsonSameDay) / len(slotsOnSameDay) < 0.5:
                            # print('Removing these Slots')
                            # print(self.slots[pd.to_datetime(self.slots.time).dt.date == slot.time.date()])
                            # print(len(self.slots))
                            self.slots = self.slots[pd.to_datetime(self.slots.time).dt.date != slot.time.date()]
                            # print(len(self.slots))
                self.games = self.games.assign(score=0)
                self.updateGameScores_df()
                self.slots = self.slots.assign(game=None)

            slots = self.slots.query('game_id.isnull()')


            RANDOMIZESLOTS = False
            if RANDOMIZESLOTS:
                slots = slots.sample(frac=1)

            # TODO: Need to find the optimal score based on num slots available for each league - something nice to compare optimization
            # TODO: Need to order the slots in a way that favors younger leagues for earlier slots

            # Iterate through every slot and try to schedule the most deserving, compatible game

            s_ind = 0
            USE_SECONDARY = False

            # manager = enlighten.get_manager()
            # pbar = manager.counter(total=len(slots), desc="Checking status", unit='members')
            for slotIndex, slot in slots.iterrows():
                s_ind = s_ind + 1
                # bar()
                if ~self.DEBUG: self.progressBar(s_ind, len(slots))
                # print('-', end="")
                # pbar.update()
                for leaguePreference in ['PRIMARY','SECONDARY']:
                    if slot.game_id == None or math.isnan(slot.game_id):
                        #     print('')


                        # This query only gets unscheduled games that are compatible with the field in the slot, randomizes them,
                        # and sorts them by score (low -> high).  Randomizing helps prevent duplication between runs.

                        # gets all unscheduled games
                        unscheduledGames = self.games[
                            ~self.games['id'].isin(self.slots.query('not game_id.isnull()')['game_id'])]

                        # finds the leagues that the field is compatible with
                        # THIS IS A LITTLE BIT OF A HACK SINCE MANYTOMANY FIELDS DON'T TRANSLATE TO DF
                        # TODO: I don't think this is working
                        # leagues = League.objects.all().filter(field__pk=slot.field_id)
                        leagues_str = []

                        slot_ = Slot.objects.all().filter(pk=slotIndex)

                        if self.DEBUG: print('-----------------------------------------------')
                        if self.DEBUG: print("Scheduling Slot: " + str(s_ind) + " of " + str(len(slots)))
                        if self.DEBUG: print("Scheduling for a: " + slot.time.strftime("%A"))
                        if self.DEBUG: print(slot_[0])


                        teamsWithGamesInTimeBubble = []

                        # Order of preference is not kept when loading the slots - need a "primary" and "secondary" preference field
                        # finds the leagues that the slot is compatible with
                        ## TODO: The approach should be to append the secondary games on top of the primary games in the same check

                        if leaguePreference=='PRIMARY' or not USE_SECONDARY:
                            # leagues = League.objects.all().filter(primaryLeague__pk=slotIndex)
                            leagues_str = []
                            leagues = []
                            if self.DEBUG: print('scheduling with PRIMARY slot league preference')
                            leagues_str.append(slot_[0].primaryLeague.pk)
                            leagues.append(slot_[0].primaryLeague)
                        else:
                            # leagues = League.objects.all().filter(secondaryLeague__pk=slotIndex)
                            leagues_str = []
                            leagues = []
                            if self.DEBUG: print('scheduling with PRIMARY and SECONDARY slot league preference')
                            leagues_str.append(slot_[0].primaryLeague.pk)
                            leagues.append(slot_[0].primaryLeague)
                            for league in slot_[0].secondaryLeague.all():
                                leagues_str.append(league.pk)
                                leagues.append(league)

                        if self.DEBUG: print("leagues:" + str(leagues_str))

                        # removes games not compatible with the slot
                        unscheduledGamesInLeague = unscheduledGames[unscheduledGames['league_id'].isin(leagues_str)]

                        # removes games that can't be scheduled due to MAX games or MAX late games
                        unscheduledGamesInLeague = unscheduledGamesInLeague.loc[(unscheduledGamesInLeague['score'] != 9999999)]

                        if self.DEBUG: print("Unscheduled games compatible with slot:" + str(len(unscheduledGamesInLeague)))
                        if self.DEBUG: print(unscheduledGamesInLeague)



                        # Get all unscheduled slots
                        scheduledSlots = self.slots.query('not game_id.isnull()')

                        # ENFORCE "DAYS BETWEEN" RULE
                        # This will limit the sub-checks by just checking for compatible league days-between limits
                        DAYSBETWEEN = True
                        # leagues = League.objects.all().filter(field__pk=slot.field_id)
                        # TODO: Should loop through compatible leagues instead of find minimum days between so tehre are no double checks
                        minDaysBetween = 9
                        for league in leagues:
                            minDaysBetween = min(league.daysBetween, minDaysBetween)
                        if self.DEBUG: print("min days between games for leagues in this slot: " + str(minDaysBetween))

                        teamsWithGamesInTimeBubble = []
                        teamsWithGamesOnSameDay = []
                        if DAYSBETWEEN and minDaysBetween > 0:
                            # Get all slots within time bubble - these are games within the "days Between" limitation
                            minDate = slot.time - timedelta(days=minDaysBetween) + timedelta(hours=24 - slot.time.hour)
                            maxDate = slot.time + timedelta(days=minDaysBetween) - timedelta(hours=slot.time.hour)
                            if self.DEBUG: print("slot Date:    " + slot.time.strftime("%m/%d/%Y, %H:%M"))
                            if self.DEBUG: print("minimum Date: " + minDate.strftime("%m/%d/%Y, %H:%M"))
                            if self.DEBUG: print("maximum Date: " + maxDate.strftime("%m/%d/%Y, %H:%M"))
                            slotsWithinTimeBubble = scheduledSlots[(scheduledSlots['time'] > minDate) &
                                                                   (scheduledSlots['time'] < maxDate)]

                            if self.DEBUG: print("num slots within time bubble: " + str(len(slotsWithinTimeBubble)))
                            if self.DEBUG: print(slotsWithinTimeBubble)


                            # Get all games from slots within time bubble
                            gamesWithinTimeBubble = self.games[
                                self.games['id'].isin(slotsWithinTimeBubble['game_id'])]
                            if self.DEBUG: print("num games within time bubble: " + str(len(gamesWithinTimeBubble)))
                            if self.DEBUG: print(gamesWithinTimeBubble)

                            # Get all teams from games withing time bubble
                            teamsWithGamesInTimeBubble = pd.concat(
                                [gamesWithinTimeBubble.team1_id, gamesWithinTimeBubble.team2_id])
                            if self.DEBUG: print("num teams within time bubble: " + str(len(teamsWithGamesInTimeBubble)))
                            if self.DEBUG: print(teamsWithGamesInTimeBubble.values)
                        else:
                            if self.DEBUG: print()
                            if self.DEBUG: print()
                            if self.DEBUG: print()
                            # ENFORCE "1 GAME / DAY RULE" RULE
                            # Get all slots within time bubble - these are games within the "days Between" limitation
                            # TODO: Change this to date instead of day all over this function
                            slotsonSameDay = scheduledSlots[pd.to_datetime(scheduledSlots.time).dt.day == slot.time.day]
                            if self.DEBUG: print("num scheduled slots on same day: " + str(len(slotsonSameDay)))
                            if self.DEBUG: print(slotsonSameDay)
                            # Get all games from slots within time bubble
                            gamesOnSameDay = self.games[
                                self.games['id'].isin(slotsonSameDay['game_id'])]
                            if self.DEBUG: print("num games on same day: " + str(len(gamesOnSameDay)))
                            if self.DEBUG: print(gamesOnSameDay)
                            # Get all teams from games withing time bubble
                            teamsWithGamesOnSameDay = pd.concat(
                                [gamesOnSameDay.team1_id, gamesOnSameDay.team2_id])
                            if self.DEBUG: print("num teams on same day: " + str(len(teamsWithGamesOnSameDay)))
                            if self.DEBUG: print(teamsWithGamesOnSameDay.values)

                        # ENFORCE COACH OVERLAP RULE
                        # Get all slots within coach overlap bubble
                        # TODO:  need to fix time before start and time after end - use gameDuration
                        slotsWithinCoachOverlap = scheduledSlots[
                            (scheduledSlots['time'] < slot.time + timedelta(minutes=self.coachOverlapTime + 120)) & (
                                    scheduledSlots['time'] > slot.time - timedelta(minutes=self.coachOverlapTime + 120))]

                        # Get all games from slots coach overlap bubble
                        gamesWithinCoachOverlap = self.games[
                            self.games['id'].isin(slotsWithinCoachOverlap['game_id'])]

                        # Get all teams from games withing coach overlap
                        teamsWithGamesInCoachOverlap = pd.concat(
                            [gamesWithinCoachOverlap.team1_id, gamesWithinCoachOverlap.team2_id])

                        # get all unscheduled games minus the teams with games in time bubble
                        gamesWithTeamsWithGamesOutsideTimeBubble = unscheduledGamesInLeague[
                            (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesInTimeBubble)) &
                            (~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesInTimeBubble)) &
                            (~unscheduledGamesInLeague['team1_id'].isin(teamsWithGamesOnSameDay)) &
                            (~unscheduledGamesInLeague['team2_id'].isin(teamsWithGamesOnSameDay))]
                        if self.DEBUG: print("num games outside restrictions: " + str(len(gamesWithTeamsWithGamesOutsideTimeBubble)))
                        if self.DEBUG: print(gamesWithTeamsWithGamesOutsideTimeBubble)
                        if len(gamesWithTeamsWithGamesOutsideTimeBubble)==0:
                            if self.DEBUG: print('UNABLE TO SCHEDULE GAME - NO COMPATIBLE GAMES')

                        # randomize list of games and sort by score
                        RANDOMIZEGAMES=False
                        if RANDOMIZEGAMES:
                            unscheduledGamesInLeague = gamesWithTeamsWithGamesOutsideTimeBubble.sample(frac=1)
                        else:
                            unscheduledGamesInLeague = gamesWithTeamsWithGamesOutsideTimeBubble
                        unscheduledGamesSortedByLowestScore = unscheduledGamesInLeague.sort_values('score')
                        g_ind = 0
                        for gameIndex, game in unscheduledGamesSortedByLowestScore.iterrows():
                            # ensure that the game is not already scheduled - this shouldn't happen but it is good to check
                            if self.DEBUG: print('---------------------------------------------------')
                            if self.DEBUG: print("Attempting to schedule game " + str(g_ind+1) + " of " + str(
                                len(unscheduledGamesSortedByLowestScore)))
                            g_ind = g_ind + 1
                            if len(self.slots[self.slots.game_id == game.id]) == 0:

                                if self.scheduleGame_df(slot, slotIndex, game, gameIndex, teamsWithGamesInCoachOverlap):
                                    if self.DEBUG: print('***** GAME SCHEDULED *****')
                                    if self.DEBUG: print('-----------------------------------------------------------------------------------')
                                    if self.DEBUG: print('NUMBER GAMES UNSCHEDULED: ' + str(
                                        len(self.games) - len(self.slots.query('not game_id.isnull()'))))
                                    if self.DEBUG: print('NUMBER SLOTS UNSCHEDULED: ' + str(len(self.slots.query('game_id.isnull()'))))
                                    if self.DEBUG: print('-----------------------------------------------------------------------------------')
                                    slot.game_id=0
                                    break
                                else:
                                    if self.DEBUG: print('UNABLE TO SCHEDULE GAME - FAILED COMPATIBILITY CHECK')

        elapsed_time = time.time() - t
        if self.DEBUG: print('ELAPSED TIME:' + str(elapsed_time))
        self.transferScheduleFromDfToObject()

    def scheduleGame_df(self, slot, slotIndex, game, gameIndex, teamsWithGamesInCoachOverlap):

        if self.DEBUG: print('CHECKING COMPATIBILITY OF GAME: ' + str(game.id))
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

        ## Need to check that no team gets more than one total extra game scheduled more than the minimum in the league
        ## This should prevent an uneven number of games for teams in the same league
        CHECKMINGAMEDELTA = False

        ## Need to check that each team has the same number of rest days since last game - Majors Only
        CHECKRESTDAYS = True
        restDayThreshold = 1
        ## TODO: This only works if the slots are scheduled in chronological order
        if CHECKRESTDAYS and (game.league_id == 1 or game.league_id == 2 or game.league_id == 3) :
            ## find the latest previously scheduled game
            earlierGamesTeam1 = scheduledGamesWithTeam1[scheduledGamesWithTeam1.time < slot.time].sort_values('time')
            laterGamesTeam1 = scheduledGamesWithTeam1[scheduledGamesWithTeam1.time > slot.time].sort_values('time')
            if self.DEBUG:print(earlierGamesTeam1)
            if self.DEBUG:print(laterGamesTeam1)
            if len(earlierGamesTeam1)>0:
                team1MostRecentGame = earlierGamesTeam1.iloc[len(earlierGamesTeam1)-1]
                team1RestTime = slot.time - team1MostRecentGame.time
            else:
                team1RestTime = timedelta(days=10)

            earlierGamesTeam2 = scheduledGamesWithTeam2[scheduledGamesWithTeam2.time < slot.time].sort_values('time')
            laterGamesTeam2 = scheduledGamesWithTeam2[scheduledGamesWithTeam2.time > slot.time].sort_values('time')
            if self.DEBUG:print(earlierGamesTeam2)
            if self.DEBUG:print(laterGamesTeam2)
            if len(earlierGamesTeam2) > 0:
                team2MostRecentGame = earlierGamesTeam2.iloc[len(earlierGamesTeam2) - 1]
                team2RestTime = slot.time - team2MostRecentGame.time
            else:
                team2RestTime = timedelta(days=10)

            if (team1RestTime.days >= restDayThreshold and team2RestTime.days >=restDayThreshold) or (team1RestTime.days <= restDayThreshold and team2RestTime.days <=restDayThreshold):
                Compatible = True
                if self.DEBUG:print('Teams have equal rest time: ' + str(team1RestTime) + ' ' + str(team2RestTime))
            else:
                if self.DEBUG:print('Teams do not have equal rest time: ' + str(team1RestTime) + ' ' + str(team2RestTime))
                Compatible = False
                return False

        ## CHECK THAT A GAME IS NOT BEING SCHEDULED WHEN THERE IS A TEAM >= 1 LESS GAME - TO HELP LEVEL THINGS OUT
        ## NEEDS IMPLEMENTATION
        ## CAN GET AROUND THIS BY MANUALLY GENERATING THE GAMES THAT I WANT SCHEDULED - MUCH EASIER
        CHECKLEAGUEGAMEDELTA=True
        if CHECKLEAGUEGAMEDELTA:
            if self.DEBUG:print('test')


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

        ## ENSURE THAT DAYS BETWEEN GAMES ADHERES TO LEAGUE SETTING
        DISTRIBUTEGAMES = True
        league = League.objects.all().filter(pk=game.league_id)
        daysBetween = league[0].daysBetween
        if DISTRIBUTEGAMES and daysBetween > 0:
            for gameIndex, scheduledGame in scheduledGamesWithTeam1.iterrows():
                thisslot = self.slots[self.slots.game_id == scheduledGame.game_id]

                minDate = thisslot.time - timedelta(days=daysBetween) + timedelta(
                    hours=24 - pd.to_datetime(thisslot.time).iloc[0].hour)
                maxDate = thisslot.time + timedelta(days=daysBetween) - timedelta(
                    hours=pd.to_datetime(thisslot.time).iloc[0].hour)

                if slot.time > minDate.iloc[0] and slot.time < maxDate.iloc[0]:

                    # if abs((pd.to_datetime(thisslot.time).iloc[0] - pd.to_datetime(slot.time)).days) < daysBetween or abs(
                    #         (pd.to_datetime(slot.time) - (pd.to_datetime(thisslot.time).iloc[0])).days) < daysBetween:
                    Compatible = False
                    if self.DEBUG: print('GAMES ARE TOO CLOSE TOGETHER')
                    if self.DEBUG: print('CONFLICTING GAME:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=thisslot.index[0])[0])
                    if self.DEBUG: print('SLOT:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
                    return False

            for gameIndex, scheduledGame in scheduledGamesWithTeam2.iterrows():
                thisslot = self.slots[self.slots.game_id == scheduledGame.game_id]
                minDate = thisslot.time - timedelta(days=daysBetween) + timedelta(
                    hours=24 - pd.to_datetime(thisslot.time).iloc[0].hour)
                maxDate = thisslot.time + timedelta(days=daysBetween) - timedelta(
                    hours=pd.to_datetime(thisslot.time).iloc[0].hour)

                if slot.time > minDate.iloc[0] and slot.time < maxDate.iloc[0]:
                    # if abs((pd.to_datetime(thisslot.time).iloc[0] - pd.to_datetime(slot.time)).days) < daysBetween or abs(
                    #         (pd.to_datetime(slot.time) - (pd.to_datetime(thisslot.time).iloc[0])).days) < daysBetween:
                    Compatible = False
                    if self.DEBUG: print('GAMES ARE TOO CLOSE TOGETHER - MUST BE ' + str(daysBetween) + ' DAYS APART')
                    if self.DEBUG: print('CONFLICTING GAME:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=thisslot.index[0])[0])
                    if self.DEBUG: print('SLOT:')
                    if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
                    return False

            if Compatible:
                if self.DEBUG: print('NO GAMES SCHEDULED FOR TEAMS WITHIN TIME BUBBLE')

        ## ENSURE UNDER MAX GAME CAP
        CHECKMAXGAME = True
        if CHECKMAXGAME:
            if League.objects.get(id=game.league_id).maxGames is not None:

                if len(scheduledGamesWithTeam1) >= League.objects.get(id=game.league_id).maxGames:
                    Compatible = False
                    self.games.ix[gameIndex, 'score'] = 9999999
                    self.games.loc[self.games.team1_id == game.team1_id, 'score'] = 9999999
                    self.games.loc[self.games.team2_id == game.team1_id, 'score'] = 9999999

                    if self.DEBUG: print('TOO MANY GAMES ALREADY SCHEDULED FOR TEAM 1')
                    return False

                if len(scheduledGamesWithTeam2) >= League.objects.get(id=game.league_id).maxGames:
                    Compatible = False
                    self.games.ix[gameIndex, 'score'] = 9999999
                    self.games.loc[self.games.team1_id == game.team2_id, 'score'] = 9999999
                    self.games.loc[self.games.team2_id == game.team2_id, 'score'] = 9999999

                    if self.DEBUG: print('TOO MANY GAMES ALREADY SCHEDULED FOR TEAM 2')
                    return False

            if Compatible:
                if self.DEBUG: print('TEAMS UNDER MAX GAME CAP')

        ## ENSURE NOT TOO MANY LATE GAMES
        if self.enforceLateGameCap:
            lateAdder = 0
            if slot.time.hour > self.lateTimeThreshold: lateAdder = 1

            if len(scheduledGamesWithTeam1[pd.to_datetime(
                    scheduledGamesWithTeam1.time).dt.hour > self.lateTimeThreshold]) + lateAdder > League.objects.get(
                id=game.league_id).maxLateGames:
                if self.DEBUG: print('Num late scheduled for team1: ' + str(len(scheduledGamesWithTeam1[
                                                                                    pd.to_datetime(
                                                                                        scheduledGamesWithTeam1.time).dt.hour > self.lateTimeThreshold])))
                Compatible = False
                if self.DEBUG: print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR TEAM 1')
                self.games.loc[self.games.team1_id == game.team1_id, 'score'] = 9999999
                self.games.loc[self.games.team2_id == game.team1_id, 'score'] = 9999999
                self.games.ix[gameIndex, 'score'] = 9999999
                return False

            if len(scheduledGamesWithTeam2[pd.to_datetime(
                    scheduledGamesWithTeam2.time).dt.hour > self.lateTimeThreshold]) + lateAdder > League.objects.get(
                id=game.league_id).maxLateGames:
                if self.DEBUG: print('Num late scheduled for team2: ' + str(len(scheduledGamesWithTeam2[
                                                                                    pd.to_datetime(
                                                                                        scheduledGamesWithTeam2.time).dt.hour > self.lateTimeThreshold])))
                Compatible = False
                if self.DEBUG: print('TOO MANY LATE GAMES ALREADY SCHEDULED FOR TEAM 2')
                self.games.loc[self.games.team1_id == game.team2_id, 'score'] = 9999999
                self.games.loc[self.games.team2_id == game.team2_id, 'score'] = 9999999
                self.games.ix[gameIndex, 'score'] = 9999999
                return False

        if Compatible:
            if self.DEBUG: print('NO LATE GAME CONFLICTS')

        ## MAX OF GAMES PER WEEK
        CHECKMAXGAMESPERWEEK = True
        maxGamesPerWeek = 3
        if CHECKMAXGAMESPERWEEK:
            weekStart = slot.time - timedelta(days=slot.time.weekday(), hours=slot.time.hour, minutes=slot.time.minute)
            weekEnd = weekStart + timedelta(days=7)
            GamesThisWeekforTeam1 = scheduledGamesWithTeam1[
                (scheduledGamesWithTeam1['time'] >= weekStart) & (scheduledGamesWithTeam1['time'] <= weekEnd)]
            GamesThisWeekforTeam2 = scheduledGamesWithTeam2[
                (scheduledGamesWithTeam2['time'] >= weekStart) & (scheduledGamesWithTeam2['time'] <= weekEnd)]
            if len(GamesThisWeekforTeam1) >= maxGamesPerWeek or len(GamesThisWeekforTeam2) >= maxGamesPerWeek:
                Compatible = False
                if self.DEBUG: print(
                    'Team over weekly max game limit of '+ str(maxGamesPerWeek) + ' : ' + str(len(GamesThisWeekforTeam1)) + " " + str(
                        len(GamesThisWeekforTeam2)))
                return False
            if self.DEBUG: print(
                'Both teams under weekly max game limit of ' + str(maxGamesPerWeek) + ' : ' + str(len(GamesThisWeekforTeam1)) + " " + str(
                    len(GamesThisWeekforTeam2)))

        ## ENSURE THAT EITHER COACH OF GAME DOESN'T HAVE A GAME WITHIN 45 MIN OF START OR END TIME
        CHECKCOACHOVERLAP = True
        if CHECKCOACHOVERLAP and teamsWithGamesInCoachOverlap.size > 0:
            team1_coach = self.teams.ix[game.team1_id].coach_id
            team2_coach = self.teams.ix[game.team2_id].coach_id
            for team_id in teamsWithGamesInCoachOverlap:
                if not self.teams.ix[team_id].coach_id is None and (
                        self.teams.ix[team_id].coach_id == team1_coach or self.teams.ix[
                    team_id].coach_id == team2_coach):
                    Compatible = False
                    if self.DEBUG: print('A Coach has another game scheduled too close to this slot')
                    return False

        ## ENSURE THAT THE DATE DOES NOT CONFLICT WITH BLACKOUT DATES
        CHECKBLACKOUTDATE = True
        if CHECKBLACKOUTDATE:
            slotDate = slot.time
            # team1_blackoutDates = self.teams.ix[game.team1_id].boDate
            # team2_blackoutDates = self.teams.ix[game.team2_id].boDate
            for blackoutDate in Team.objects.all().filter(pk=game.team1_id)[0].boDate.all():
                if slot.time.date().day == blackoutDate.date.day and slot.time.date().month == blackoutDate.date.month:
                    Compatible = False
                    if self.DEBUG: print('Day conflicts with Team 1 blackout dates')
                    if self.DEBUG: print('slot    :  ' + str(slot.time.date()))
                    if self.DEBUG: print('blackout:  ' + str(blackoutDate.date))
                    return False
            for blackoutDate in Team.objects.all().filter(pk=game.team2_id)[0].boDate.all():
                if slot.time.date == blackoutDate.date:
                    Compatible = False
                    if self.DEBUG: print('Day conflicts with Team 2 blackout dates')
                    if self.DEBUG: print('slot    :  ' + str(slot.time.date()))
                    if self.DEBUG: print('blackout:  ' + str(blackoutDate.date))
                    return False
            if self.DEBUG: print('No blackout conflicts')

        # scheduledSlots = self.slots.query('not game_id.isnull()')
        # teamsinLeague = self.teams[self.teams['league_id'] == game.league_id]
        # numTeamsInLeague = len(teamsinLeague)
        # gamesinLeague = self.games[self.games['league_id'] == game.league_id]
        # scheduledGamesInLeague = scheduledSlots[scheduledSlots['game_id'].isin(gamesinLeague['id'])]

        if Compatible:
            if self.DEBUG: print('SCHEDULING GAME: ' + str(game.id))
            if self.DEBUG: print(Game.objects.all().filter(pk=game.id)[0])
            if self.DEBUG: print('SLOT: ')
            if self.DEBUG: print(Slot.objects.all().filter(pk=slotIndex)[0])
            # print('-----------------------------------------------------------------------------------')
            # print('NUMBER GAMES UNSCHEDULED: ' + str(
            #     len(self.games) - len(self.slots.query('not game_id.isnull()'))))
            # print('NUMBER SLOTS UNSCHEDULED: ' + str(len(self.slots.query('game_id.isnull()'))))
            # print('-----------------------------------------------------------------------------------')

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

        SCHEDULEDGAMEPENALTY = True
        UNCHEDULEDGAMEHANDICAP = True
        MORETHANMINIMUMLEAGUESCHEDULEPENALTY = False
        INTERDIVISIONALHANDICAP = True
        LOWERTHANAVERAGESCHEDULEPENALTY = False
        COACHMUTLIPLETEAMHANDICAP = True

        score = 0

        # HANDICAP REDUCED AS NUMBER OF GAMES SCHEDULED INCREASES
        if SCHEDULEDGAMEPENALTY:
            gameswithteams2 = gamesWithTeams[gamesWithTeams['id'].isin(scheduledGames['game_id'])]
            scheduledGamesWithTeams = scheduledGames[scheduledGames['game_id'].isin(gameswithteams2['id'])]
            score = score + (len(scheduledGamesWithTeams) * 200)

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
                score = score - 400

        # TEAMS THAT HAVE COACHES WITH MORE THAN ONE TEAM GET PREFERENCE
        if COACHMUTLIPLETEAMHANDICAP:
            if len(self.teams[self.teams['coach_id'] == self.teams.ix[game.team1_id].coach_id]) > 1 or \
                    len(self.teams[self.teams['coach_id'] == self.teams.ix[game.team2_id].coach_id]) > 1:
                score = score - 4000

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

        # Account for Handicap if needed
        score = score + game.handicap

        self.games.ix[gameIndex, 'score'] = score

    def transferScheduleFromDfToObject(self):

        if self.DEBUG: print('POPULATING GAMES')

        scheduledGames = self.slots.query('not game_id.isnull()')
        for index, slot in scheduledGames.iterrows():
            game = Game.objects.all().filter(pk=slot.game_id)[0]
            dbslot = Slot.objects.all().filter(pk=index)[0]
            dbslot.game = game
            dbslot.save()

        #Create a sound to indicate completeness
        print('\007')
