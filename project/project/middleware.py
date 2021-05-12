import django.utils.timezone
from pytz import timezone


class TimezoneMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz = timezone('US/Pacific')
        django.utils.timezone.activate(tz)
        return self.get_response(request)
