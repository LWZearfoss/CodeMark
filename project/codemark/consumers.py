from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async, async_to_sync
from .models import Submission, Result, User, Class
from .serializers import ResultSerializer
from json import dumps


class SubmissionConsumer(AsyncWebsocketConsumer):
    async def omit_hidden(self, data):
        if await sync_to_async(lambda user: user not in Class.objects.get(submission=self.submission_pk).instructors.all())(self.user):
            for level in data['level_outputs']:
                level['step_outputs'] = [step for step in level['step_outputs'] if not step['hidden']]
            data['level_outputs'] = [level for level in data['level_outputs'] if len(level['step_outputs']) > 0]
        return data

    async def connect(self):
        self.user = self.scope["user"]
        self.submission_pk = self.scope['url_route']['kwargs']['submission_pk']
        self.submission_group_name = 'submission_%s' % self.submission_pk

        submission_object = await sync_to_async(Submission.objects.get)(pk=self.submission_pk)
        if await sync_to_async(lambda user, submission: user == submission.submitter or user in submission.enrolled_class.instructors.all())(self.user, submission_object):
            await self.channel_layer.group_add(
                self.submission_group_name,
                self.channel_name
            )
            await self.accept()
            query = await sync_to_async(Result.objects.filter)(submission=submission_object)
            result = None
            if await sync_to_async(query.count)() > 0:
                result = await sync_to_async(query.latest)()
            data = await self.omit_hidden(await sync_to_async(lambda: ResultSerializer(result).data)())
            await self.send(dumps(data))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.submission_group_name,
            self.channel_name
        )

    async def update(self, event):
        data = await self.omit_hidden(event['data'])
        await self.send(dumps(data))
