from django import forms
from .models import League, Team, Division, Field, Slot, SiteConfiguration
from django.contrib.admin import widgets
from django_range_slider.fields import RangeSliderField, RangeSlider
# from .widgets import RangeSlider


class NewLeagueForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'abbreviation','description','maxLateGames','maxGames']

class SettingsForm(forms.ModelForm):
    class Meta:
        model = SiteConfiguration
        fields = ['maxLateGames', 'enforceLateGameCap','daysBetweenGames']


class RangeSliderField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name', '')
        self.minimum = kwargs.pop('minimum',0)
        self.maximum = kwargs.pop('maximum',100)
        self.step = kwargs.pop('step',1)
        kwargs['widget'] = RangeSlider(self.minimum, self.maximum, self.step, self.name)
        if 'label' not in kwargs.keys():
            kwargs['label'] = False
        super(RangeSliderField, self).__init__(*args, **kwargs)

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
