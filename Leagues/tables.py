import django_tables2 as tables
from .models import Game, Slot


class GamesTable(tables.Table):
    class Meta:
        model = Game
        template_name = 'django_tables2/bootstrap.html'

class SlotsTable(tables.Table):
    class Meta:
        model = Slot
        template_name = 'django_tables2/bootstrap.html'