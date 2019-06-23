from Leagues.admin import TeamResource, LeagueResource, FieldResource, DivisionResource
import tablib
from Leagues.models import Team
from import_export import resources
from django.http import HttpResponse

def printall():
    teamdataset = TeamResource().export()
    fielddataset = FieldResource().export()
    leaguedataset = LeagueResource().export()
    divisiondataset = DivisionResource().export()

    print(teamdataset.csv)
    print(fielddataset.csv)
    print(leaguedataset.csv)
    print(divisiondataset.csv)



    response = HttpResponse(teamdataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teams.csv"'
    # return response

def loadall():
    team_resource = resources.modelresource_factory(model=Team)()
    dataset = tablib.Dataset(['', 'New Team','just added this one','1','1'], headers=['id', 'name', 'description', 'league', 'division'])
    result = team_resource.import_data(dataset, dry_run=True)
    # print(result)
    print(result.has_errors())
    result = team_resource.import_data(dataset, dry_run=False)
    # >>> print(result.has_errors())
    # False
    # >>> result = book_resource.import_data(dataset, dry_run=False)

def export(request):
    teamdataset = TeamResource().export()
    dataset = teamdataset.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teams.csv"'
    return response
