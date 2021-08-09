from typing import List

from datetime import datetime

import requests
import logging
import json

logger = logging.getLogger(__name__)


class Clickup:
    def __init__(self, token):
        self.token = token

    def url(self, path: str, version: int = 2):
        return self.base_url(version=version) + path

    def base_url(self, version: int = 2):
        return f'https://api.clickup.com/api/v{version}/'

    def request(self, method, url, version: int = 2, retry_count=0, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = self.token
        headers['Content-Type'] = (
            'application/json'
            if 'Content-Type' not in headers else headers['Content-Type']
            )
        headers['Accept'] = (
            'application/json'
            if 'Accept' not in headers else headers['Accept']
            )
        if not url.startswith('https://'):
            url = self.url(url, version=version)
        response = requests.request(method, url, headers=headers, **kwargs)
        if response.status_code > 250:
            if retry_count < 2:
                return self.request(
                    method, url, retry_count=retry_count + 1, **kwargs
                    )
            raise Exception(
                f'Error { response.status_code }: { response.text }'
                )
        else:
            try:
                return json.loads(response.text)
            except json.decoder.JSONDecodeError:
                return response.text

    def options(self, url):
        return self.request('OPTIONS', url)

    def post(self, url, data):
        return self.request('POST', url, data=json.dumps(data))

    def get(self, url, params=None):
        return self.request('GET', url, params=params)

    def put(self, url, data):
        return self.request('PUT', url, data=json.dumps(data))

    def patch(self, url, data):
        return self.request('PATCH', url, data=json.dumps(data))

    def delete(self, url, params=None):
        return self.request('DELETE', url, params=params)

    @property
    def user(self):
        return self.get('user')['user']

    def list_teams(self):
        for team in self.get('team')['teams']:
            yield team

    def list_spaces(self, teams: List[int] = None):
        if teams is None:
            teams = self.list_teams()
        for team in teams:
            for space in self.get(f'team/{team["id"]}/space')['spaces']:
                yield space

    def list_folders(self, spaces=None):
        if spaces is None:
            spaces = self.list_spaces()
        for space in spaces:
            for folder in self.get(f'space/{space["id"]}/folder')['folders']:
                yield folder

    def list_lists(self, spaces=None):
        if spaces is None:
            spaces = self.list_spaces()
        for space in spaces:
            for folder in self.get(f'space/{space["id"]}/folder')['folders']:
                for _list in self.get(f'folder/{folder["id"]}/list')['lists']:
                    yield _list
            for _list in self.get(f'space/{space["id"]}/list')['lists']:
                yield _list

    def create_task(
        self,
        list_id: str,
        start_date: datetime,
        due_date: datetime,
        all_day: bool = False,
        **data,
        ):
        data['start_date'] = start_date.timestamp() * 1000
        data['due_date'] = due_date.timestamp() * 1000
        data['start_date_time'] = not all_day
        data['due_date_time'] = not all_day
        return self.post(f'list/{list_id}/task', data=data)

    def update_task(
        self,
        task_id: str,
        start_date: datetime,
        due_date: datetime,
        all_day: bool = False,
        **data,
        ):
        data['start_date'] = start_date.timestamp() * 1000
        data['due_date'] = due_date.timestamp() * 1000
        data['start_date_time'] = not all_day
        data['due_date_time'] = not all_day
        return self.put(f'task/{task_id}', data=data)

    def delete_task(self, task_id: str):
        return self.delete(f'task/{task_id}')

    @staticmethod
    def repr_list(l: dict) -> str:
        if not l["folder"]["hidden"]:
            folder = " > " + l["folder"]["name"]
        else:
            folder = ""
        return f'{l["space"]["name"]}{folder} > {l["name"]}'

    def list_webhooks(self, teams=None):
        if teams is None:
            teams = self.list_teams()
        for team in teams:
            for webhook in self.get(f'team/{team["id"]}/webhook')['webhooks']:
                yield webhook

    def create_webhook(self, team):
        pass
    

    # If due date is at 2:00:00 AM then it is the whole day

    # {
    #     "endpoint": "https://gcal2clickup.herokuapp.com/api/clickup/",
    #     "events": [
    #         "taskCreated",
    #         "taskUpdated",
    #         "taskDeleted",
    #         "taskMoved",
    #     ]
    # }
