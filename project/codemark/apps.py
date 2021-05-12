from django.apps import AppConfig


class CodemarkConfig(AppConfig):
    name = 'codemark'

    def ready(self):
        import codemark.tasks
        import codemark.consumers
