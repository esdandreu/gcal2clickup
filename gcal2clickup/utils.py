from typing import Union, Optional

from django.utils.timezone import make_aware

from datetime import datetime, date


def make_aware_datetime(
    dt: Union[datetime, date],
    hour: Optional[int] = 0,
    minute: Optional[int] = 0, 
    second: Optional[int] = 0,
    ) -> datetime:
    if type(dt) is date:
        dt = datetime(dt.year, dt.month, dt.day, hour, minute, second)
    try:
        return make_aware(dt)
    except ValueError as e: 
        if 'Not naive datetime' in str(e):
            return dt
        raise e
