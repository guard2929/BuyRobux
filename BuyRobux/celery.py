from celery import Celery
from celery.schedules import crontab

app = Celery('your_project_name')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-pending-payments-every-minute': {
        'task': 'core.tasks.check_pending_payments',
        'schedule': crontab(minute='*/1'),
    },
}