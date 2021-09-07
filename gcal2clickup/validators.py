from django.core.exceptions import ValidationError

import re


def validate_is_pattern(pattern: str):
    try:
        re.compile(pattern)
    except Exception as e:
        raise ValidationError('Invalid regex pattern: ' + str(e)) from e


def validate_is_clickup_token(token: str):
    if not token.startswith('pk_'):
        raise ValidationError(
            'Invalid clickup API Token, it must start with "pk"'
            )
