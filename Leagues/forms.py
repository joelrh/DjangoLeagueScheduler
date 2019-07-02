from django import forms
from .models import League, Team, Division, Field, Slot
from django.contrib.admin import widgets


class NewLeagueForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'description']


class NewTeamForm(forms.ModelForm):
    # def __init__(self,*args,**kwargs):
    #     super(NewTeamForm, self).__init__(*args, **kwargs)
    #     # self.fields['division'].queryset = Division.objects.filter(
    #     #     league=self.instance.league,
    #     self.fields.get('division').choices = ['1',Division.objects.all().filter()



    class Meta:
        model = Team
        fields = ['name', 'description', 'league', 'division']

    def __init__(self, *args, **kwargs):
        super(NewTeamForm, self).__init__(*args, **kwargs)
        # if self.instance.id:
        #     if self.instance.state:
        # try:
        #     divisions = Division.objects.filter(league=self.instance.league)
        #
        #     division_field = self.fields['division'].widget
        #     division_choices = []
        #     if divisions is None:
        #         division_choices.append(('', '---------'))
        #
        #     for division in divisions:
        #         division_choices.append((division.id, division.name))
        #     division_field.choices = division_choices
        # except:pass

    # def clean(self):
    #     try:
    #         divisions = Division.objects.filter(league=self.instance.league)
    #
    #         division_field = self.fields['division'].widget
    #         division_choices = []
    #         if divisions is None:
    #             division_choices.append(('', '---------'))
    #
    #         for division in divisions:
    #             division_choices.append((division.id, division.name))
    #         division_field.choices = division_choices
    #     except:pass



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
