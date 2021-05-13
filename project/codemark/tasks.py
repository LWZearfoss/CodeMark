# Create your tasks here

import time
import tempfile
import signal
import docker
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from json import dumps


from .models import User, Submission, RunStep, TestStep, Result, LevelOutput, RunStepOutput, TestStepOutput
from .serializers import ResultSerializer


# Custom exception class
class TimeoutException(Exception):
    pass


# Custom signal handler
def timeout_handler(signum, frame):
    raise TimeoutException


def send_submission_update(result):
    layer = get_channel_layer()
    data = ResultSerializer(result).data
    async_to_sync(layer.group_send)(
        'submission_%s' % result.submission.pk, {
            'type': 'update', 'data': data
        }
    )


@shared_task
def execute_result(result_pk):
    signal.signal(signal.SIGALRM, timeout_handler)
    result = Result.objects.get(pk=result_pk)
    for level_output in result.level_outputs.all():
        dir = tempfile.TemporaryDirectory()
        if result.submission.assignment.fixture:
            for file in result.submission.assignment.fixture.files.all():
                file.copy(dir.name)
        for file in result.submission.files.all():
            file.copy(dir.name)
        client = docker.from_env()
        container = client.containers.run(level_output.container, detach=True, auto_remove=True, tty=True, stdout=True, stderr=True, volumes={
            dir.name: {
                'bind': '/tmp',
                'mode': 'rw',
            }
        })
        for step_output in level_output.step_outputs.all():
            if isinstance(step_output, RunStepOutput):
                signal.alarm(int(step_output.timeout.total_seconds()))
                res = None
                stdout = ''
                stderr = ''
                timed_out = False
                try:
                    res = container.exec_run(
                        'bash -c "{0}"'.format(step_output.command.replace('"', '\\"')), workdir='/tmp', demux=True
                    )
                except TimeoutException:
                    timed_out = True
                    pass
                signal.alarm(0)
                if res and res.output[0]:
                    stdout = res.output[0].decode('utf-8', 'ignore')
                if res and res.output[1]:
                    stderr = res.output[1].decode('utf-8', 'ignore')
                step_output.stdout = stdout
                step_output.stderr = stderr
                step_output.timed_out = timed_out
            if isinstance(step_output, TestStepOutput):
                signal.alarm(int(step_output.timeout.total_seconds()))
                res = None
                actual_output = ''
                timed_out = False
                try:
                    res = container.exec_run(
                        'bash -c "{0}"'.format(step_output.command.replace('"', '\\"')), workdir='/tmp'
                    )
                except TimeoutException:
                    timed_out = True
                    pass
                signal.alarm(0)
                if res and res.output:
                    actual_output = res.output.decode('utf-8', 'ignore')
                step_output.actual_output = actual_output
                step_output.timed_out = timed_out

            step_output.save()
            send_submission_update(result)

        container.stop()
        dir.cleanup()


def trigger_run(submission_object):
    result = Result()
    result.submission = submission_object
    result.save()
    for level in submission_object.assignment.levels.all():
        level_output = LevelOutput()
        level_output.name = level.name
        level_output.save()
        for step in level.steps.all():
            if isinstance(step, RunStep):
                step_output = RunStepOutput()
                step_output.command = step.command
                step_output.timeout = step.timeout
                step_output.stdout = None
                step_output.stderr = None
                step_output.timed_out = None
            elif isinstance(step, TestStep):
                step_output = TestStepOutput()
                step_output.command = step.command
                step_output.timeout = step.timeout
                step_output.expected_output = step.expected_output
                step_output.case_insensitive = step.case_insensitive
                step_output.strip_whitespace = step.strip_whitespace
                step_output.actual_output = None
                step_output.timed_out = None
            step_output.name = step.name
            step_output.number = step.number
            step_output.weight = step.weight
            step_output.hidden = step.hidden
            step_output.save()
            level_output.step_outputs.add(step_output)
        level_output.save()
        result.level_outputs.add(level_output)
    result.save()
    execute_result.delay(result.pk)
