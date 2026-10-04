import time
from unittest.mock import patch


def no_sleep():
    return patch.object(time, "sleep", lambda *_args, **_kwargs: None)
