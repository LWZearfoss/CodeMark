from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.contrib.auth import logout
from django.forms import formset_factory
from django.core import serializers
from django.conf import settings
from django.http import Http404, JsonResponse, HttpResponse
from django.views.generic.edit import CreateView, UpdateView, FormView, DeleteView, FormMixin, DeletionMixin
from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from verify_email.email_handler import send_verification_email
import csv
import mosspy
import os
import tempfile


from . import forms
from . import models
from .tasks import trigger_run


def logout_view(request):
    logout(request)
    return redirect('/')


def register_view(request):
    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            send_verification_email(request, form)
            return render(request, 'activation/notify.html')
        else:
            context = {'form': form}
            return render(request, 'registration/register.html', context=context)
    else:
        form = forms.RegisterForm()
        context = {'form': form}
        return render(request, 'registration/register.html', context=context)


@login_required
def enroll_view(request):
    if request.method == 'POST':
        form = forms.EnrollForm(request.POST, user=request.user)
        if form.is_valid():
            form.cleaned_data['selected_class'].students.add(request.user)
            return redirect('/')
        else:
            redirect('/')
    else:
        return redirect('/')


@login_required
def unenroll_view(request, class_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.students.all() or request.user in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    class_object.students.remove(request.user)
    return redirect('/')


@login_required
def class_view(request, class_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.students.all() and request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    context = {'class': class_object}
    return render(request, 'codemark/class.html', context=context)


@login_required
def submit_view(request, class_pk, assignment_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.students.all() and request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    assignment_object = get_object_or_404(models.Assignment, pk=assignment_pk)
    if not assignment_object in class_object.assignments.all() or not assignment_object.submittable(request.user):
        raise Http404('No Assignment matches the given query.')
    files = None
    length = 0
    if assignment_object.submission_files:
        files = [file.text for file in assignment_object.submission_files.files.all()]
        length = len(files)
    SubmitFormSetFactory = formset_factory(
        form=forms.SubmitForm, formset=forms.SubmitFormSet, min_num=length, validate_min=True, max_num=length, validate_max=True)
    if request.method == 'POST':
        formset = SubmitFormSetFactory(
            request.POST, request.FILES, filenames=files)
        if formset.is_valid():
            submission_object = models.Submission()
            submission_object.enrolled_class = class_object
            submission_object.assignment = assignment_object
            submission_object.submitter = request.user
            submission_object.save()
            for form in formset:
                if form.is_valid():
                    file_object = form.save(commit=False)
                    file_object.creator = request.user
                    upload_to = file_object.file.field.upload_to
                    file_object.file.field.upload_to = lambda instance, filename: 'submission/{pk}/{name}'.format(pk=submission_object.pk, name=form.fields[
                        'file'].label)
                    file_object = form.save()
                    file_object.file.field.upload_to = upload_to
                    submission_object.files.add(file_object)
            submission_object.save()
            trigger_run(submission_object)
            return redirect('submission', submission_pk=submission_object.pk)
        else:
            context = {'formset': formset, 'class': class_object,
                       'assignment': assignment_object}
            return render(request, 'codemark/submit.html', context=context)
    else:
        formset = SubmitFormSetFactory(filenames=files)
        context = {'formset': formset, 'class': class_object,
                   'assignment': assignment_object}
        return render(request, 'codemark/submit.html', context=context)


@login_required
def run_submission_view(request, submission_pk):
    submission_object = get_object_or_404(models.Submission, pk=submission_pk)
    if request.user not in submission_object.enrolled_class.instructors.all():
        raise Http404('No Submission matches the given query.')
    trigger_run(submission_object)
    return redirect('submission', submission_pk=submission_pk)


@login_required
def run_assignment_view(request, class_pk, assignment_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    assignment_object = get_object_or_404(models.Assignment, pk=assignment_pk)
    if not assignment_object in class_object.assignments.all():
        raise Http404('No Assignment matches the given query.')
    for submission in models.Submission.objects.filter(assignment=assignment_pk).filter(enrolled_class=class_pk).order_by('submitter', '-timestamp').distinct('submitter'):
        trigger_run(submission)
    return redirect('grades', class_pk=class_pk)


@login_required
def submission_view(request, submission_pk):
    submission_object = get_object_or_404(models.Submission, pk=submission_pk)
    if request.user != submission_object.submitter and request.user not in submission_object.enrolled_class.instructors.all():
        raise Http404('No Submission matches the given query.')
    context = {'submission': submission_object}
    return render(request, 'codemark/submission.html', context=context)


@login_required
def grades_view(request, class_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    context = {'class': class_object}
    return render(request, 'codemark/grades.html', context=context)


@login_required
def download_grades_view(request, class_pk, assignment_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    assignment_object = get_object_or_404(models.Assignment, pk=assignment_pk)
    if not assignment_object in class_object.assignments.all():
        raise Http404('No Assignment matches the given query.')
    response = HttpResponse(
        content_type='text/csv'
    )
    response['Content-Disposition'] = 'attachment; filename={0}.csv'.format(
        assignment_object)
    writer = csv.writer(response)
    writer.writerow([
        'Last Name',
        'First Name',
        'Username',
        'Student ID',
        'Last Access',
        'Grade [Total Pts: {0}]'.format(assignment_object.total_points)
    ])
    for student in class_object.students.all():
        submission = None
        query = models.Submission.objects.filter(submitter=student).filter(
            assignment=assignment_pk).filter(enrolled_class=class_pk)
        if query.count() > 0:
            submission = query.latest()
        writer.writerow([student.last_name,
                         student.first_name,
                         student.username,
                         student.school_id,
                         submission.timestamp.strftime(
                             '%Y-%m-%d %H:%M:%S') if submission else '',
                         submission.latest_result.grade if submission else ''
                         ])
    return response


@login_required
def plagiarism_view(request, class_pk, assignment_pk):
    class_object = get_object_or_404(models.Class, pk=class_pk)
    if request.user not in class_object.instructors.all():
        raise Http404('No Class matches the given query.')
    assignment_object = get_object_or_404(models.Assignment, pk=assignment_pk)
    if not assignment_object in class_object.assignments.all():
        raise Http404('No Assignment matches the given query.')
    if request.method == 'POST':
        form = forms.PlagiarismForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language_field']
            m = mosspy.Moss(settings.MOSS_ID, language)
            submissions = models.Submission.objects.filter(assignment=assignment_object).order_by(
                'submitter', '-timestamp').distinct('submitter')
            dir = tempfile.TemporaryDirectory()
            for submission in submissions:
                for file in submission.files.all():
                    file.copy(dir.name, '{0}_{1}'.format(
                        submission.submitter.username, os.path.basename(file.file.name)))
            m.addFilesByWildcard('{0}/*'.format(dir.name))
            url = m.send()
            dir.cleanup()
            context = {'url': url}
            return render(request, 'codemark/plagiarism.html', context)
        else:
            context = {'form': form}
            return render(request, 'codemark/forms/plagiarism_form.html', context=context)
    else:
        form = forms.PlagiarismForm()
        context = {'form': form}
        return render(request, 'codemark/forms/plagiarism_form.html', context=context)


@login_required
def index_view(request):
    form = forms.EnrollForm(user=request.user)
    instructed_classes = models.Class.objects.filter(instructors=request.user)
    taken_classes = models.Class.objects.filter(
        students=request.user).exclude(instructors=request.user)
    context = {
        'instructed_classes': instructed_classes,
        'taken_classes': taken_classes,
        'form': form
    }
    return render(request, 'codemark/index.html', context=context)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = models.Class
    form_class = forms.ProfileForm
    template_name = 'codemark/profile.html'
    success_url = '/'

    def get_object(self, queryset=None):
        return self.request.user


class ErrorIfNotInstructorMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_instructor:
            return self.handle_no_permission()
        return super(ErrorIfNotInstructorMixin, self).dispatch(request, *args, **kwargs)


class FormParameterMixin(FormMixin):
    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(FormParameterMixin,
                            self).get_form_kwargs(**kwargs)
        form_kwargs['user'] = self.request.user
        return form_kwargs


class DeletePopupMixin(UpdatePopupMixin, DeletionMixin):
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        super().delete(request, *args, **kwargs)
        if self.is_popup():
            self.POPUP_ACTION = 'delete'
            return self.respond_script(object)
        else:
            return redirect(self.get_success_url())


class ClassAssignmentsUpdateView(LoginRequiredMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.Class
    form_class = forms.ClassAssignmentsUpdateForm
    template_name = 'codemark/forms/class_assignments_update_form.html'

    def dispatch(self, request, *args, **kwargs):
        class_object = get_object_or_404(
            models.Class, pk=self.kwargs['pk'])
        if request.user not in class_object.instructors.all():
            return self.handle_no_permission()
        return super(ClassAssignmentsUpdateView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('class', args=(self.kwargs['pk'],))


class AssignmentCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.Assignment
    form_class = forms.AssignmentForm
    template_name = 'codemark/forms/assignment_form.html'
    success_url = '/'


class AssignmentUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.Assignment
    form_class = forms.AssignmentForm
    template_name = 'codemark/forms/assignment_form.html'
    success_url = '/'


class AssignmentDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.Assignment
    success_url = '/'


class FixtureCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.Fixture
    form_class = forms.FixtureForm
    template_name = 'codemark/forms/fixture_form.html'
    success_url = '/'


class FixtureUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.Fixture
    form_class = forms.FixtureForm
    template_name = 'codemark/forms/fixture_form.html'
    success_url = '/'


class FixtureDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.Fixture
    success_url = '/'


class FileCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.File
    form_class = forms.FileForm
    template_name = 'codemark/forms/file_form.html'
    success_url = '/'


class FileUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.File
    form_class = forms.FileForm
    template_name = 'codemark/forms/file_form.html'
    success_url = '/'


class FileDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.File
    success_url = '/'


class LevelCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.Level
    form_class = forms.LevelForm
    template_name = 'codemark/forms/level_form.html'
    success_url = '/'


class LevelUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.Level
    form_class = forms.LevelForm
    template_name = 'codemark/forms/level_form.html'
    success_url = '/'


class LevelDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.Level
    success_url = '/'


class StepSelectView(LoginRequiredMixin, ErrorIfNotInstructorMixin, CreatePopupMixin, FormView):
    template_name = 'codemark/forms/step_select_form.html'
    form_class = forms.StepSelectForm
    success_url = '/'

    def form_valid(self, form):
        if self.is_popup():
            return redirect(reverse(form.cleaned_data['steps_field']) + '?_popup=1')
        else:
            return redirect(form.cleaned_data['steps_field'])


class StepUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, CreatePopupMixin, DeleteView):
    model = models.Step
    success_url = '/'

    def dispatch(self, request, *args, **kwargs):
        step = self.get_object()
        if isinstance(step, models.RunStep):
            if self.is_popup():
                return redirect(reverse('run_step_update', kwargs={'pk': step.pk}) + '?_popup=1')
            else:
                return redirect('run_step_update', pk=step.pk)
        elif isinstance(step, models.TestStep):
            if self.is_popup():
                return redirect(reverse('test_step_update', kwargs={'pk': step.pk}) + '?_popup=1')
            else:
                return redirect('test_step_update', pk=step.pk)
        return redirect(self.success_url)


class RunStepCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.RunStep
    form_class = forms.RunStepForm
    template_name = 'codemark/forms/run_step_form.html'
    success_url = '/'


class RunStepUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.RunStep
    form_class = forms.RunStepForm
    template_name = 'codemark/forms/run_step_form.html'
    success_url = '/'


class RunStepDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.RunStep
    success_url = '/'


class TestStepCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.TestStep
    form_class = forms.TestStepForm
    template_name = 'codemark/forms/test_step_form.html'
    success_url = '/'


class TestStepUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.TestStep
    form_class = forms.TestStepForm
    template_name = 'codemark/forms/test_step_form.html'
    success_url = '/'


class TestStepDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.TestStep
    success_url = '/'


class FileSchemaCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.FileSchema
    form_class = forms.FileSchemaForm
    template_name = 'codemark/forms/file_schema_form.html'
    success_url = '/'


class FileSchemaUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.FileSchema
    form_class = forms.FileSchemaForm
    template_name = 'codemark/forms/file_schema_form.html'
    success_url = '/'


class FileSchemaDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.FileSchema
    success_url = '/'


class TextCreateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, CreatePopupMixin, CreateView):
    model = models.Text
    form_class = forms.TextForm
    template_name = 'codemark/forms/text_form.html'
    success_url = '/'


class TextUpdateView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, UpdatePopupMixin, UpdateView):
    model = models.Text
    form_class = forms.TextForm
    template_name = 'codemark/forms/text_form.html'
    success_url = '/'


class TextDeleteView(LoginRequiredMixin, ErrorIfNotInstructorMixin, FormParameterMixin, DeletePopupMixin, DeleteView):
    model = models.Text
    success_url = '/'
