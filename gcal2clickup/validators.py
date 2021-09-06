from django.core.exceptions import ValidationError

import re

def validate_is_pattern(pattern):
    try:
        re.compile(pattern)
    except Exception as e:
        raise ValidationError('Invalid regex pattern: ' + str(e)) from e