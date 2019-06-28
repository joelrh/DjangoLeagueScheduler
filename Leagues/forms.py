from django import forms
from .models import League, Team, Division, Field, Slot
from django.contrib.admin import widgets


class NewLeagueForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'description']


class NewTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description', 'league', 'division']


class NewFieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['name', 'description', 'league']


class NewDivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['name', 'description', 'league']


class NewSlotForm(forms.ModelForm):
    time = forms.DateTimeField(widget=forms.DateInput(attrs={'placeholder': 'YYYY-MM-DD HH:MM', 'required': 'required'}),input_formats=['%d/%m/%Y %H:%M'])

    class Meta:
        model = Slot
        fields = ['field', 'time']
    #
    # def __init__(self, *args, **kwargs):
    #     super(NewSlotForm, self).__init__(*args, **kwargs)
    #     self.fields['time'].widget = widgets.AdminSplitDateTime()
