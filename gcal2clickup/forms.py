from django import forms
from gcal2clickup.models import Matcher


class MatcherForm(forms.ModelForm):
    calendar_id = forms.ChoiceField(label='Calendar')
    clickup_list = forms.ChoiceField(label='List')

    class Meta:
        model = Matcher
        fields = [
            'user', 'calendar_id', 'clickup_list', '_tags', '_name_regex',
            '_description_regex'
            ]


def matcher_form_factory(
    user,
    calendar_choices=[],
    calendar_initial=None,
    list_choices=[],
    list_initial=None,
    ):
    form = MatcherForm
    form.base_fields['user'].initial = user
    form.base_fields['user'].disabled = True
    form.base_fields['calendar_id'].choices = calendar_choices
    if calendar_initial:
        form.base_fields['calendar_id'].initial = calendar_initial
    form.base_fields['clickup_list'].choices = list_choices
    if list_initial:
        form.base_fields['clickup_list'].initial = list_initial
    return form
