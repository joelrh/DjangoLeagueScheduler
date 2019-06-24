from django import forms
from .models import League, Team, Division, Field


class NewLeagueForm(forms.ModelForm):
    # message = forms.CharField(
    #     widget=forms.Textarea(),
    #     max_length=4000,
    #     help_text='The max length of the text is 4000.'
    # )

    class Meta:
        model = League
        fields = ['name', 'description']


class NewTeamForm(forms.ModelForm):
    # message = forms.CharField(
    #     widget=forms.Textarea(),
    #     max_length=4000,
    #     help_text='The max length of the text is 4000.'
    # )

    class Meta:
        model = Team
        fields = ['name', 'description' , 'league', 'division']
