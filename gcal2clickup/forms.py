from django import forms
from gcal2clickup.models import Matcher

class MatcherForm(forms.ModelForm):
    # TODO dropdown with calendar options
    calendar_id = forms.CharField()

    class Meta:
        model = Matcher
        fields = '__all__'