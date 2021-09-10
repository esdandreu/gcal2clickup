from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from gcal2clickup.models import GoogleCalendarWebhook, ClickupWebhook, SyncedEvent

import logging
import json

logger = logging.getLogger('gcal2clikup')


@csrf_exempt
def google_calendar_endpoint(request):
    state = request.headers.get('X-Goog-Resource-State', None)
    if state:
        channel_id = request.headers['X-Goog-Channel-Id']
        resource_id = request.headers['X-Goog-Resource-Id']
        try:
            webhook = GoogleCalendarWebhook.objects.get(
                channel_id=channel_id, resource_id=resource_id
                )
        except GoogleCalendarWebhook.DoesNotExist:
            return HttpResponseForbidden()
        # Ignore signals from inactive users
        if not webhook.user.is_active:
            logger.info('Ignoring google calendar change')
            return HttpResponse('Ignored', status=218)
        created, updated = webhook.check_events()
        return HttpResponse(
            f'Created {created} tasks, updated {updated} tasks', status=200
            )
    return HttpResponseForbidden()


@csrf_exempt
def clickup_endpoint(request):
    body = json.loads(request.body)
    try:
        webhook = ClickupWebhook.objects.get(pk=body['webhook_id'])
    except ClickupWebhook.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)
    # Ignore signals from inactive users
    if not webhook.clickup_user.user.is_active:
        logger.info(body)
        return HttpResponse('Ignored', status=218)
    task_id = body['task_id']
    event = body['event']
    items = body.get('history_items', [])
    try:
        try:
            synced_event = SyncedEvent.objects.get(task_id=task_id)
            if event == 'taskDeleted':
                synced_event.delete(with_event=True)
                return HttpResponse('Event deleted', status=204)
            else:
                synced_event.update_event_from_task_history(items)
                synced_event.save()
                return HttpResponse('Updated event', status=201)
        except SyncedEvent.DoesNotExist:
            # Was sync tag added?
            if event == 'taskUpdated':
                if ClickupWebhook.is_sync_tag_added(items):
                    if webhook.check_task(task_id=task_id):
                        return HttpResponse('Created event', status=201)
                else:
                    webhook.clickup_user.remove_sync_tag(task_id=task_id)
                    return HttpResponse('Sync removed', status=204)
    except Exception as e:
        logger.error(body)
        raise e
    return HttpResponse('Nothing happened', status=200)
