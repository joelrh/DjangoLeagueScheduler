from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Min, Avg, Max
from django_tables2 import RequestConfig
from django.http import Http404
from Leagues.admin import TeamResource
from tablib import Dataset
from .forms import NewLeagueForm, NewTeamForm, NewFieldForm, NewDivisionForm, NewSlotForm
from django.http import HttpResponse
from Leagues.models import League, Team, Division, Field, Game, Slot
from Leagues.gameGenerator import generateGames, updateGameScores
from .tables import GamesTable, SlotsTable


# Create your views here.
def home(request):
    teams = Team.objects.all()
    fields = Field.objects.all()
    return render(request, 'home.html', {'teams': teams, 'fields': fields})


def gengames(request):
    generateGames()
    teams = Team.objects.all()
    fields = Field.objects.all()
    return render(request, 'home.html', {'teams': teams, 'fields': fields})


def leagues(request, pk):
    league = get_object_or_404(League, pk=pk)
    teams = Team.objects.all().filter(league=league)
    return render(request, 'leagues.html', {'league': league, 'teams': teams})


def teams(request, pk):
    team = get_object_or_404(Team, pk=pk)
    return render(request, 'teams.html', {'team': team})


def fields(request, pk):
    field = get_object_or_404(Field, pk=pk)
    return render(request, 'fields.html', {'field': field})


def divisions(request, pk):
    division = get_object_or_404(Division, pk=pk)
    teams = Team.objects.all().filter(division=division)
    return render(request, 'divisions.html', {'division': division, 'teams': teams})


def allfields(request):
    fields = Field.objects.all()
    return render(request, 'allfields.html', {'fields': fields})


def allleagues(request):
    leagues = League.objects.all()
    return render(request, 'allleagues.html', {'leagues': leagues})


def allteams(request):
    teams = Team.objects.all()
    return render(request, 'allteams.html', {'teams': teams})


def alldivisions(request):
    divisions = Division.objects.all()
    return render(request, 'alldivisions.html', {'divisions': divisions})


def allgames(request):
    table = GamesTable(Game.objects.all())
    RequestConfig(request).configure(table)
    updateGameScores()
    # return render(request, 'tutorial/people.html', {'table': table})
    # games = Game.objects.all()
    # leagues = League.objects.all()
    return render(request, 'allgames.html', {'table': table})#, 'leagues': leagues})

def allslots(request):
    table = SlotsTable(Slot.objects.all())
    RequestConfig(request).configure(table)
    # return render(request, 'tutorial/people.html', {'table': table})
    # games = Game.objects.all()
    # leagues = League.objects.all()
    return render(request, 'allslots.html', {'table': table})#, 'leagues': leagues})

def simple_upload(request):
    if request.method == 'POST':
        person_resource = TeamResource()
        dataset = Dataset()
        new_persons = request.FILES['myfile']

        imported_data = dataset.load(new_persons.read())
        result = person_resource.import_data(dataset, dry_run=True)  # Test the data import

        if not result.has_errors():
            person_resource.import_data(dataset, dry_run=False)  # Actually import now

    return render(request, 'core/simple_upload.html')


def new_league(request):  # , pk):
    league = League()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewLeagueForm(request.POST)
        if form.is_valid():
            league = form.save()
            return redirect('allleagues')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewLeagueForm()
    return render(request, 'new_league.html', {'league': league, 'form': form})


def new_team(request):  # , pk):
    team = Team()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewTeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            generateGames()
            updateGameScores()
            return redirect('allteams')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewTeamForm()
    return render(request, 'new_team.html', {'team': team, 'form': form})


def new_field(request):  # , pk):
    field = Field()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewFieldForm(request.POST)
        if form.is_valid():
            field = form.save()
            return redirect('allfields')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewFieldForm()
    return render(request, 'new_field.html', {'field': field, 'form': form})

def new_slot(request):  # , pk):
    slot = Slot()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewSlotForm(request.POST)
        if form.is_valid():
            slot = form.save()
            return redirect('allslots')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewSlotForm()
    return render(request, 'new_slot.html', {'slot': slot, 'form': form})

def new_division(request):  # , pk):
    division = Division()  # get_object_or_404(League, pk=pk)
    user = User.objects.first()  # TODO: get the currently logged in user
    if request.method == 'POST':
        form = NewDivisionForm(request.POST)
        if form.is_valid():
            division = form.save()
            return redirect('alldivisions')  # , pk=league.pk)  # TODO: redirect to the created topic page
    else:
        form = NewDivisionForm()
    return render(request, 'new_division.html', {'division': division, 'form': form})


def genGames(request):
    generateGames()
    updateGameScores()
    games = Game.objects.all()
    return render(request, 'allgames.html', {'games': games})

# def scheduleGames(request):
#
#     slots = Slot.objects.all().filter
#     # update scores
#     updateGameScores()
#     # get lowest scoring game
#     lowest Game.objects.order_by('score')[0]
#
#     (u'First1', 10)
#     games = Game.objects.all()
#     return render(request, 'allgames.html', {'games': games})
