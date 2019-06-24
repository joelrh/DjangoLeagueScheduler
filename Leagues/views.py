from django.shortcuts import render, get_object_or_404
from django.http import Http404
from Leagues.admin import TeamResource
from tablib import Dataset
from django.http import HttpResponse
from Leagues.models import League, Team, Division, Field


# Create your views here.
def home(request):
    teams = Team.objects.all()
    fields = Field.objects.all()
    return render(request, 'home.html', {'teams': teams, 'fields': fields})

def leagues(request, pk):
    league = get_object_or_404(League, pk=pk)
    return render(request, 'leagues.html', {'league': league})

def teams(request, pk):
    team = get_object_or_404(Team, pk=pk)
    return render(request, 'teams.html', {'team': team})

def fields(request, pk):
    field = get_object_or_404(Field, pk=pk)
    return render(request, 'fields.html', {'field': field})

def allfields(request):
    fields = Field.objects.all()
    return render(request, 'allfields.html', {'fields': fields})

def allleagues(request):
    leagues = League.objects.all()
    return render(request, 'allleagues.html', {'leagues': leagues})

def allteams(request):
    teams = Team.objects.all()
    return render(request, 'allteams.html', {'teams': teams})

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
