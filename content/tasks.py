from celery import shared_task

from content.models import Post


@shared_task
def create_scheduled_post(post_data):
    post_data.pop("schedule_date", None)
    Post.objects.create(**post_data)
