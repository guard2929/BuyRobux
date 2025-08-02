default_app_config = 'BuyRobux.apps.BuyRobuxConfig'

from .celery import app as celery_app

__all__ = ('celery_app',)
