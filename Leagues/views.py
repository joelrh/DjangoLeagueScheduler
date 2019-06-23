from django.shortcuts import render
from Leagues.admin import TeamResource
from tablib import Dataset


# Create your views here.
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