from django.db import models


# For all models here, need to check and prevent duplication

# Create your models here.
class League(models.Model):
    name = models.CharField(max_length=20, null=False)
    abbreviation = models.CharField(max_length=2, null=False)
    description = models.TextField(blank=True, null=True)

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
    # team2 = models.ManyToManyField(Team)
    # team2 = models.ForeignKey(Team, on_delete=models.CASCADE)
    # league = models.ForeignKey(League, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.team1.__str__() + " | " + self.team2.__str__())


class Slot(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    time = models.DateTimeField
    isScheduled = False

    def __str__(self):
        return str('')
