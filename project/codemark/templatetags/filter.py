from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def smooth_timedelta(timedeltaobj):
    """Convert a datetime.timedelta object into Days, Hours."""
    if not timedeltaobj:
        return None
    secs = timedeltaobj.total_seconds()
    timetot = ""
    if secs > 86400:  # 60sec * 60min * 24hrs
        days = secs // 86400
        timetot += "{} days".format(int(days))
        secs = secs - days*86400

    if secs > 3600:
        hrs = secs // 3600
        timetot += " {} hours".format(int(hrs))
        secs = secs - hrs*3600

    return timetot.strip()


@register.filter()
def submitted_in(submissions, enrolled_class):
    if submissions:
        return submissions.filter(enrolled_class=enrolled_class)


@register.filter()
def submitted_by(submissions, user):
    if submissions:
        return submissions.filter(submitter=user)


@register.filter()
def latest(queryset):
    if queryset:
        return queryset.latest()


@register.filter()
def timestamp(submission):
    if submission:
        return submission.timestamp


@register.filter()
def grade(submission):
    if submission and submission.latest_result:
        return submission.latest_result.grade
    else:
        return ''


@register.filter()
def submittable(assignment, user):
    if assignment:
        return assignment.submittable(user)
