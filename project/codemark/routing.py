from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import url

from .consumers import SubmissionConsumer

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            url(
                r'^ws/submission/(?P<submission_pk>[^/]+)/$', SubmissionConsumer.as_asgi()),
        ])
    ),
})