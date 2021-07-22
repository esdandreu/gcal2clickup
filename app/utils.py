GITHUB_URL = 'https://github.com/esdandreu/gcal2clickup/tree/main'
RAWGITHUB_URL = 'https://raw.githubusercontent.com/esdandreu/gcal2clickup/main'


def readme(title: str = 'gcal2clickup') -> str:
    # Returns a link to the readme
    return f'{GITHUB_URL}#{title}'


def readme_image_url(filename: str) -> str:
    # Returns a link to a readme image
    return f'{RAWGITHUB_URL}/README/{filename}'