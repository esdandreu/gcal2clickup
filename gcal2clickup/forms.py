from django import forms
from gcal2clickup.models import Matcher


class MatcherForm(forms.ModelForm):
    calendar_id = forms.ChoiceField(label='Calendar')

    class Meta:
        model = Matcher
        fields = [
            'user', 'calendar_id', 'list_id', 'tag_name', '_name_regex',
            '_description_regex'
            ]


def matcher_form_factory(
    user,
    calendar_choices=[],
    calendar_initial=None,
    list_choices=[],
    ):
    form = MatcherForm
    form.base_fields['user'].initial = user
    form.base_fields['user'].disabled = True
    form.base_fields['calendar_id'].choices = calendar_choices
    if calendar_initial:
        form.base_fields['calendar_id'].initial = calendar_initial
    return form
