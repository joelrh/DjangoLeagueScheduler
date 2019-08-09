from django.db import models


# THIS IS THE GLOBAL TO-DO AREA
# TODO: Definitely need to run multiple runs and keep the best scorer
#
# TODO: Need to be able to check for coach overlap
#
# TODO: Need to add realistic leagues
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
# TODO: remove team1/team2 and use teams instead.  This will eliminate the need to check for team1 and team2 - can use "__in"
#
# TODO: how to let the user make scheduling suggestions / corrections / confirmations
#
# TODO: add ability to run back through the schedule and remove games with the best situated teams and rerun with games for least suited teams
#
# TODO: add some sore of schedule distribution for each team
#
# TODO: need to make weekend games prime and reflect on a teams score
#
# TODO: how to even out the game schedule distribution for teams

# Create your models here.

from django.db import models
from solo.models import SingletonModel

class SiteConfiguration(models.Model):
    maxLateGames = models.IntegerField(null=True)
    enforceLateGameCap = models.BooleanField(default=False)
    daysBetweenGames = models.IntegerField(null=True)

    @classmethod
    def object(cls):
        return cls._default_manager.all().first() # Since only one item

    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)

class League(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=3, null=False)
    description = models.TextField(blank=True, null=True)
    maxLateGames = models.IntegerField(null=True)
    maxGames = models.IntegerField(null=True)
    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=2, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, default='1')
    division = models.ForeignKey(Division, on_delete=models.CASCADE)#, limit_choices_to={'league':league})

    def __str__(self):
        return str(self.name.__str__() + "-" + self.division.abbreviation.__str__() + "-" + self.league.__str__())
        # TODO: for some reason this is always displaying "Major" as the league


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
    enabled = models.BooleanField(default=True)
    # isScheduled = models.BooleanField(default=False)
    # enabled TODO:need to add a field to allow the user to disable a game from being scheduled

    def shortstr(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())

    def __str__(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())


class Slot(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, null=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True)
    time = models.DateTimeField(null=True)

    def __str__(self):
        return str(
            str(self.pk) + " | " + self.field.__str__() + " | " + self.time.__str__() + " | " + self.game.__str__())

class Coach(models.Model):
    firstName = models.CharField(max_length=20, null=False)
    lastName = models.CharField(max_length=20, null=False)

    def __str__(self):
        return str(
            self.firstName.__str__() + " " + self.lastName.__str__())