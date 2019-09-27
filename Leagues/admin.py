from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import League, Division, Team, Field, Game, Slot, Coach, SiteConfiguration
from import_export import resources


# Register your models here.
@admin.register(Game)
class GameAdmin(ImportExportModelAdmin):
    pass

class GameResource(resources.ModelResource):
    class Meta:
        model = Game


@admin.register(Team)
class TeamAdmin(ImportExportModelAdmin):
    pass

class TeamResource(resources.ModelResource):
    class Meta:
        model = Team


@admin.register(Field)
class FieldAdmin(ImportExportModelAdmin):
    pass

class FieldResource(resources.ModelResource):
    class Meta:
        model = Field


@admin.register(Division)
class DivisionAdmin(ImportExportModelAdmin):
    pass

class DivisionResource(resources.ModelResource):
    class Meta:
        model = Division


@admin.register(League)
class LeagueAdmin(ImportExportModelAdmin):
    pass

class LeagueResource(resources.ModelResource):
    class Meta:
        model = League

@admin.register(Coach)
class CoachAdmin(ImportExportModelAdmin):
    pass

class CoachResource(resources.ModelResource):
    class Meta:
        model = Coach

@admin.register(Slot)
class SlotAdmin(ImportExportModelAdmin):
    pass

class SlotResource(resources.ModelResource):
    class Meta:
        model = Slot

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(ImportExportModelAdmin):
    pass

class SiteConfigurationResource(resources.ModelResource):
    class Meta:
        model = SiteConfiguration