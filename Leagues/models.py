from django.db import models

# THIS IS THE GLOBAL TO-DO AREA
# TODO: Definitely need to run multiple runs and keep the best scorer
#
# TODO: website flow needs improvement - how do you know where to start
#
# TODO: Ideally update score based on the current slot available - will take time but will reduce the total number of iterations.
#  Games with too many late games will have their score handicap reduced.  Better to chose game based on specific circumstances
#  instead of generic overall condition
#
# TODO: Need the ability to accept games or pre-schedule games
#
# TODO: Add iteration that removes a game from a high scoring team and gives the others a shot
#
# TODO: how to let the user make scheduling suggestions / corrections / confirmations
#
# TODO: add ability to run back through the schedule and remove games with the best situated teams and rerun with games for least suited teams

# TODO: create discrete schedule based on excel spreadsheet

# TODO: games need to be varied length set per league

# TODO: 2 games scheduled per week in every division - may need to add a check for this after the schedule is generated

# TODO: add equal rest between games for opponents peewee and above

# TODO: need better way to view the slots since they all start on different times and have different durations

# TODO: need to go thorugh the schedule and find days where there are only 1-2 games scheduled / remove these games / mark slots as unavailable/ and attempy to reschedule them

# Create your models here.

from django.db import models
from solo.models import SingletonModel

class BlackOutDate(models.Model):
    date = models.DateField(null=True)

class SiteConfiguration(models.Model):
    maxLateGames = models.IntegerField(null=True)
    enforceLateGameCap = models.BooleanField(default=False)
    daysBetweenGames = models.IntegerField(null=True)

    @classmethod
    def object(cls):
        return cls._default_manager.all().first()  # Since only one item

    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)

class Coach(models.Model):
    firstName = models.CharField(max_length=20, null=False)
    lastName = models.CharField(max_length=20, null=False)

    def __str__(self):
        return str(
            self.firstName.__str__() + " " + self.lastName.__str__())

class League(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=3, null=False)
    description = models.TextField(blank=True, null=True)
    maxLateGames = models.IntegerField(null=True)
    maxGames = models.IntegerField(null=True)
    gameDuration = models.IntegerField(null=False,default=120)
    daysBetween = models.IntegerField(null=False,default=0)

    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=2, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class BODate(models.Model):
    date = models.DateTimeField(null=True)

    # def __str__(self):
    #     return self.date


class Team(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)  # , limit_choices_to={'league':league})
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, null=True)
    boDate = models.ManyToManyField(BODate, null=True, related_name='boDate')
    #coach = models.ManyToManyField(Coach)

    def __str__(self):
        return str(self.league.abbreviation.__str__() + " " + self.name.__str__() + " " + self.division.abbreviation.__str__())


class Field(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ManyToManyField(League)

    def __str__(self):
        return self.name


class Game(models.Model):
    team1 = models.ForeignKey(Team, related_name='team1', on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name='team2', on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    score = models.IntegerField(null=True)
    enabled = models.BooleanField(default=True)  # TODO: Use this to remove games that are no longer "schedule-able"
    complete = models.BooleanField(default=False)
    handicap = models.IntegerField(default=0)

    def shortstr(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())

    def __str__(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())


class Slot(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, null=False)
    # league = models.ManyToManyField(League, related_name='league')
    primaryLeague = models.ForeignKey(League, on_delete=models.CASCADE, null=False, related_name='primaryLeague')
    secondaryLeague = models.ManyToManyField(League,related_name='secondaryLeague')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True)
    time = models.DateTimeField(null=True)
    duration = models.IntegerField(null=True)

    class Meta:
        get_latest_by = 'time'

    def __str__(self):
        return str(
            str(self.pk) + " | " + self.field.__str__() + " | " + self.time.__str__() + " | " + self.game.__str__())



