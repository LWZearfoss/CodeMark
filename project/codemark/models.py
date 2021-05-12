from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser, PermissionsMixin, Group
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from polymorphic.models import PolymorphicModel
from datetime import timedelta, datetime
import os
import shutil


GCC = 'gcc'
PYTHON = 'python'
ALPINE = 'alpine'
UBUNTU = 'ubuntu'
BASH = 'bash'
RUST = 'rust'
JAVA = 'java'
NODE = 'node'
CONTAINER_CHOICES = [
    (GCC, 'GCC'),
    (PYTHON, 'Python'),
    (ALPINE, 'Alpine'),
    (UBUNTU, 'Ubuntu'),
    (BASH, 'Bash'),
    (RUST, 'Rust'),
    (JAVA, 'Java'),
    (NODE, 'Node'),
]


class User(AbstractUser):
    email = models.EmailField(blank=False, unique=True)
    nickname = models.CharField(blank=True, null=True, max_length=30)
    phone_number = PhoneNumberField(blank=True, null=True)
    school_id = models.CharField(
        blank=False, null=True, max_length=30, verbose_name='School ID'
    )

    @property
    def is_instructor(self):
        return Class.objects.filter(instructors=self).count() > 0


class Department(models.Model):
    name = models.CharField(max_length=30)
    abbreviation = models.CharField(max_length=4)

    def __str__(self):
        return self.name


def user_directory_path(instance, filename):
    return 'user/{0}/{1}/{2}'.format(instance.creator.id, datetime.now().strftime('%Y-%m-%d--%H-%M-%S'), filename)


class File(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_path)

    def copy(self, dest, name=None):
        if not name:
          name = self.file.name
        dst = open(os.path.join(dest, os.path.basename(name)), "wb")
        shutil.copyfileobj(self.file, dst)

    def __str__(self):
        return os.path.basename(self.file.name)


class Fixture(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    files = models.ManyToManyField(File)

    def __str__(self):
        return self.name


class Text(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class FileSchema(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    files = models.ManyToManyField(Text)

    def __str__(self):
        return self.name

    @property
    def file_names(self):
        return ', '.join([str(file) for file in self.files.all()])


class Step(PolymorphicModel):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    number = models.IntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    weight = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    hidden = models.BooleanField()

    def __str__(self):
        return self.name + ' - ' + str(self.number)

    class Meta:
        ordering = ['number']


class RunStep(Step):
    command = models.TextField()
    timeout = models.DurationField()

    def __str__(self):
        return self.command + ' - ' + str(self.number)


class TestStep(Step):
    command = models.TextField()
    timeout = models.DurationField()
    expected_output = models.TextField()
    case_insensitive = models.BooleanField()
    strip_whitespace = models.BooleanField()

    def __str__(self):
        return self.command + ' - ' + str(self.number)


class Level(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    steps = models.ManyToManyField(Step)

    container = models.CharField(
        max_length=30,
        choices=CONTAINER_CHOICES,
        default=GCC,
    )

    def __str__(self):
        return self.name


class Assignment(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    deadline = models.DateTimeField(blank=True, null=True)
    late_deadline = models.DateTimeField(blank=True, null=True)
    submission_limit = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    cool_off = models.DurationField(default=timedelta())
    fixture = models.ForeignKey(
        Fixture, on_delete=models.PROTECT, blank=True, null=True
    )
    levels = models.ManyToManyField(Level, blank=True)
    submission_files = models.ForeignKey(
        FileSchema, on_delete=models.PROTECT, blank=True, null=True
    )

    def __str__(self):
        return self.name

    def submittable(self, user):
        query = Submission.objects.filter(
            submitter=user).filter(assignment=self)
        if self.submission_limit and query.count() > self.submission_limit:
            return False
        elif query.count() > 0 and timezone.now() - query.latest().timestamp < self.cool_off:
            return False
        elif self.late_deadline:
            return timezone.now() < self.late_deadline
        elif self.deadline:
            return timezone.now() < self.deadline
        else:
            return True

    @property
    def total_points(self):
        points = 0
        for level in self.levels.all():
            for step in level.steps.all():
                points += step.weight
        return points

    @property
    def past_due(self):
        if self.deadline:
            return timezone.now() > self.deadline
        else:
            return False

    @property
    def past_late_due(self):
        if self.late_deadline:
            return timezone.now() > self.late_deadline
        else:
            return False

    @property
    def due_delta(self):
        if self.deadline:
            return self.deadline - timezone.now()
        else:
            return None

    @property
    def late_due_delta(self):
        if self.late_deadline:
            return self.late_deadline - timezone.now()
        else:
            return None


class Course(models.Model):
    name = models.CharField(max_length=30)
    number = models.CharField(max_length=4)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.department.abbreviation + ' ' + self.number


class Class(models.Model):
    class Term(models.TextChoices):
        FALL = 'FA', _('Fall')
        WINTER = 'WI', _('Winter')
        SPRING = 'SP', _('Spring')
        SUMMER = 'SU', _('Summer')
    term = models.CharField(
        max_length=2,
        choices=Term.choices
    )
    year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    section = models.CharField(max_length=4)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructors = models.ManyToManyField(User, related_name='instructor_users')
    students = models.ManyToManyField(User, related_name='student_users')
    assignments = models.ManyToManyField(Assignment)

    def __str__(self):
        return str(self.course) + '.' + self.section + ' ' + self.get_term_display() + ' ' + str(self.year) + ' - ' + ', '.join([instructor.get_full_name() for instructor in self.instructors.all()])

    class Meta:
        verbose_name_plural = 'Classes'


class Submission(models.Model):
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    enrolled_class = models.ForeignKey(Class, on_delete=models.CASCADE)
    files = models.ManyToManyField(File)

    def __str__(self):
        return self.assignment.name + ' ' + self.submitter.get_full_name() + ' - ' + str(self.timestamp)

    @property
    def latest_result(self):
        query = Result.objects.filter(submission=self)
        result = None
        if query.count() > 0:
            result = query.latest()
        return result

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = ['timestamp']


class StepOutput(PolymorphicModel):
    name = models.CharField(max_length=30)
    number = models.IntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    weight = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    hidden = models.BooleanField()

    def __str__(self):
        return self.name + ' - ' + str(self.number)

    @property
    def grade(self):
        return 0

    class Meta:
        ordering = ['number']


class RunStepOutput(StepOutput):
    command = models.TextField()
    timeout = models.DurationField()
    stdout = models.TextField(null=True)
    stderr = models.TextField(null=True)
    timed_out = models.BooleanField(null=True)

    def __str__(self):
        return self.command + ' - ' + str(self.number)

    @property
    def grade(self):
        return self.weight if not self.stderr else 0


class TestStepOutput(StepOutput):
    command = models.TextField()
    timeout = models.DurationField()
    expected_output = models.TextField()
    case_insensitive = models.BooleanField()
    strip_whitespace = models.BooleanField()
    actual_output = models.TextField(null=True)
    timed_out = models.BooleanField(null=True)

    def __str__(self):
        return self.command + ' - ' + str(self.number)

    @property
    def grade(self):
        expected = str(self.expected_output)
        actual = str(self.actual_output)
        if self.case_insensitive:
            expected = expected.lower()
            actual = actual.lower()
        if self.strip_whitespace:
            expected = expected.strip()
            actual = actual.strip()
        return self.weight if expected == actual else 0


class LevelOutput(models.Model):
    name = models.CharField(max_length=30)
    step_outputs = models.ManyToManyField(StepOutput)

    container = models.CharField(
        max_length=30,
        choices=CONTAINER_CHOICES,
        default=GCC,
    )

    def __str__(self):
        return self.name


class Result(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    level_outputs = models.ManyToManyField(LevelOutput)

    def __str__(self):
        return str(self.submission)

    @property
    def grade(self):
        points = 0
        for level in self.level_outputs.all():
            for step in level.step_outputs.all():
                points += step.grade
        return points

    class Meta:
        get_latest_by = ['timestamp']
