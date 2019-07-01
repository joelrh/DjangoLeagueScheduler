from django.db import models


# # For all models here, need to check and prevent duplication
# TODO: Definitely need to run multiple runs and keep the best scorer
#
# TODO: Need to be able to check for coach overlap
#
# TODO: Ideally update score based on the current slot available - will take time but will reduce the total number of iterations
#
# TODO: Need the ability to accept games or pre-schedule games
#
# TODO: Add iteration that removes a game from a high scoring team and gives the others a shot

# Create your models here.
class League(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=2, null=False)
    description = models.TextField(blank=True, null=True)

    # handicapp = models.IntegerField()

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
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name.__str__() + "-" + self.division.abbreviation.__str__() + "-" + self.league.__str__())


class Field(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ManyToManyField(League)

    def __str__(self):
        return self.name


class Game(models.Model):
    # team1 = models.ForeignKey(Team, on_delete=models.CASCADE)
    team1 = models.ForeignKey(Team, related_name='team1', on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name='team2', on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    score = models.IntegerField(null=True)
    isScheduled = models.BooleanField(default=False)

    def shortstr(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())

    def __str__(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__() + " | " + str(self.score) + " | " + str(
            self.isScheduled))


class Slot(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, null=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True)
    time = models.DateTimeField(null=True)

    # isScheduled = models.BooleanField(default=False)

    def __str__(self):
        return str(
            str(self.pk) + " | " + self.field.__str__() + " | " + self.time.__str__() + " | " + self.game.__str__())
