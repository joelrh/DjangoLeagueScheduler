from django.db import models


# For all models here, need to check and prevent duplication

# Create your models here.
class League(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=20, null=False)
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
        return self.name


class Field(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.TextField(blank=True, null=True)
    league = models.ManyToManyField(League)

    def __str__(self):
        return self.name
