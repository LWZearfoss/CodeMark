from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms import Form, ModelForm, ModelChoiceField, Select, SelectMultiple, BaseFormSet, ChoiceField, HiddenInput, DateTimeInput, CharField, PasswordInput, ValidationError
from django.utils.translation import gettext_lazy as _
from django_addanother.widgets import AddAnotherWidgetWrapper, AddAnotherEditSelectedWidgetWrapper
from django.urls import reverse_lazy
from .models import Class, File, Assignment, Fixture, FileSchema, Level, Step, File, Text, RunStep, TestStep


class RegisterForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'nickname',
                  'username', 'email', 'school_id', 'phone_number')
        labels = {
            'phone_number': _('Phone number (optional)'),
            'nickname': _('Nickname (optional)'),
        }


class ProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['readonly'] = True

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'nickname',
                  'username', 'email', 'school_id', 'phone_number')


class EnrollForm(Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(EnrollForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['selected_class'].queryset = Class.objects.exclude(
                students=user).exclude(instructors=user)

    selected_class = ModelChoiceField(
        queryset=Class.objects.all(), widget=Select, label='Enroll in Class')


class SubmitForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.filename = kwargs.pop('filename', None)
        super(SubmitForm, self).__init__(*args, **kwargs)
        if self.filename is not None:
            self.fields['file'].label = self.filename

    class Meta:
        model = File
        fields = ['file']


class SubmitFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        filenames = kwargs.pop('filenames', None)
        super(SubmitFormSet, self).__init__(*args, **kwargs)
        self.filenames = filenames
        for form in self.forms:
            form.empty_permitted = False

    def get_form_kwargs(self, form_index):
        form_kwargs = super(SubmitFormSet, self).get_form_kwargs(form_index)
        if form_index < len(self.filenames):
            form_kwargs['filename'] = self.filenames[form_index]
        return form_kwargs


class ClassAssignmentsUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ClassAssignmentsUpdateForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['assignments'].queryset = (Assignment.objects.filter(
                class__instructors=user
            ) | Assignment.objects.filter(
                creator=user
            )).distinct()

    class Meta:
        model = Class
        fields = ['assignments']
        widgets = {
            'assignments': AddAnotherEditSelectedWidgetWrapper(
                SelectMultiple,
                reverse_lazy('assignment_create'),
                reverse_lazy('assignment_update', args=['__fk__'])
            )
        }


class AssignmentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(AssignmentForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user
            self.fields['fixture'].queryset = (Fixture.objects.filter(
                assignment__class__instructors=user
            ) | Fixture.objects.filter(
                creator=user
            )).distinct()
            self.fields['levels'].queryset = (Level.objects.filter(
                assignment__class__instructors=user
            ) | Level.objects.filter(
                creator=user
            )).distinct()
            self.fields['submission_files'].queryset = (FileSchema.objects.filter(
                assignment__class__instructors=user
            ) | FileSchema.objects.filter(
                creator=user
            )).distinct()

    def clean(self):
        if self.cleaned_data['late_deadline'] and self.cleaned_data['deadline'] and self.cleaned_data['late_deadline'] < self.cleaned_data['deadline']:
            self.add_error('late_deadline', ValidationError(
                'Late deadline must be after regular deadline.'))
        return self.cleaned_data

    class Meta:
        model = Assignment
        fields = '__all__'
        widgets = {
            'fixture': AddAnotherEditSelectedWidgetWrapper(
                Select,
                reverse_lazy('fixture_create'),
                reverse_lazy('fixture_update', args=['__fk__'])
            ),
            'levels': AddAnotherEditSelectedWidgetWrapper(
                SelectMultiple,
                reverse_lazy('level_create'),
                reverse_lazy('level_update', args=['__fk__'])
            ),
            'submission_files': AddAnotherEditSelectedWidgetWrapper(
                Select,
                reverse_lazy('file_schema_create'),
                reverse_lazy('file_schema_update', args=['__fk__'])
            ),
            'creator': HiddenInput(),
        }


class FixtureForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FixtureForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user
            self.fields['files'].queryset = (File.objects.filter(
                fixture__assignment__class__instructors=user
            ) | File.objects.filter(
                creator=user
            )).distinct()

    class Meta:
        model = Fixture
        fields = '__all__'
        widgets = {
            'files': AddAnotherEditSelectedWidgetWrapper(
                SelectMultiple,
                reverse_lazy('file_create'),
                reverse_lazy('file_update', args=['__fk__'])
            ),
            'creator': HiddenInput()
        }


class FileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FileForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user

    class Meta:
        model = File
        fields = '__all__'
        widgets = {
            'creator': HiddenInput()
        }


class LevelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(LevelForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user
            self.fields['steps'].queryset = (Step.objects.filter(
                level__assignment__class__instructors=user
            ) | Step.objects.filter(
                creator=user
            )).distinct()

    class Meta:
        model = Level
        fields = '__all__'
        widgets = {
            'steps': AddAnotherEditSelectedWidgetWrapper(
                SelectMultiple,
                reverse_lazy('step_select'),
                reverse_lazy('step_update', args=['__fk__'])
            ),
            'creator': HiddenInput()
        }


class StepSelectForm(Form):
    STEP_CHOICES = (
        ('run_step_create', 'RunStep'),
        ('test_step_create', 'TestStep')
    )

    steps_field = ChoiceField(choices=STEP_CHOICES, label='Step')


class StepForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(StepForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user

    class Meta:
        model = Step
        fields = '__all__'
        widgets = {
            'creator': HiddenInput()
        }


class RunStepForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(RunStepForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user

    class Meta:
        model = RunStep
        fields = '__all__'
        widgets = {
            'creator': HiddenInput()
        }


class TestStepForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TestStepForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user

    def clean(self):
        self.cleaned_data = super(TestStepForm, self).clean()
        self.cleaned_data['expected_output'] = self.cleaned_data['expected_output'].replace(
            '\r\n', '\n')
        return self.cleaned_data

    class Meta:
        model = TestStep
        fields = '__all__'
        widgets = {
            'creator': HiddenInput()
        }


class FileSchemaForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FileSchemaForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user
            self.fields['files'].queryset = (Text.objects.filter(
                fileschema__assignment__class__instructors=user
            ) | Text.objects.filter(
                creator=user
            )).distinct()

    class Meta:
        model = FileSchema
        fields = '__all__'
        widgets = {
            'files': AddAnotherEditSelectedWidgetWrapper(
                SelectMultiple,
                reverse_lazy('text_create'),
                reverse_lazy('text_update', args=['__fk__'])
            ),
            'creator': HiddenInput()
        }


class TextForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TextForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['creator'].initial = user

    class Meta:
        model = Text
        fields = '__all__'
        widgets = {
            'creator': HiddenInput()
        }


class PlagiarismForm(Form):
    LANGUAGE_CHOICES = (
        ('c', 'C'),
        ('cc', 'C++'),
        ('java', 'Java'),
        ('pascal', 'Pascal'),
        ('haskell', 'Haskell'),
        ('fortran', 'Fortran'),
        ('ascii', 'ASCII'),
        ('perl', 'Perl'),
        ('matlab', 'MATLAB'),
        ('python', 'Python'),
        ('javascript', 'JavaScript')
    )

    language_field = ChoiceField(choices=LANGUAGE_CHOICES, label='Language')
