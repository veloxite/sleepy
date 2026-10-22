"""Small, explicit GitHub integration. Tokens never enter model context or SQLite."""
import json
import os
import re
import urllib.request
import urllib.error
import keyring

SERVICE = 'Sleepy.GitHub'

def token():
    return keyring.get_password(SERVICE, 'token') or os.getenv('GITHUB_TOKEN') or ''

def request(method, path, data=None, credential=None):
    secret = credential if credential is not None else token()
    if not secret:
        raise ValueError('Connect GitHub in Settings → Plugins first.')
    req = urllib.request.Request('https://api.github.com' + path, method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer ' + secret, 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json', 'User-Agent': 'Sleepy-Desktop',
                 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise ValueError('GitHub rejected that token. Check or replace it in Plugins.') from None
        if error.code == 403:
            raise ValueError('GitHub denied access. Check token permissions and account rate limits.') from None
        if error.code == 422:
            raise ValueError('GitHub could not create that repository. The name may already exist or be invalid.') from None
        raise ValueError(f'GitHub returned HTTP {error.code}.') from None
    except (OSError, TimeoutError):
        raise ValueError('GitHub could not be reached. For a create request, check your GitHub account before trying again.') from None

def connect(credential):
    account = request('GET', '/user', credential=credential)
    keyring.set_password(SERVICE, 'token', credential)
    return account['login']

def disconnect():
    try:
        keyring.delete_password(SERVICE, 'token')
    except keyring.errors.PasswordDeleteError:
        pass
    if os.getenv('GITHUB_TOKEN'):
        return 'Disabled. Remove GITHUB_TOKEN from .env to erase the environment credential too.'
    return 'GitHub disconnected.'

def validate_repo(data):
    name = data.get('name', '').strip()
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', name) or name in ('.', '..'):
        raise ValueError('Use a repository name with letters, numbers, dots, hyphens, or underscores.')
    return {'name': name, 'description': str(data.get('description', ''))[:350],
            'private': data.get('private', True) is not False, 'auto_init': True}

def create_repo(data):
    repo = request('POST', '/user/repos', validate_repo(data))
    return {'name': repo['full_name'], 'url': repo['html_url']}

REPO_TOOL = {'type': 'function', 'function': {
    'name': 'propose_github_repository',
    'description': 'Prepare a repository creation proposal only when the user explicitly requests a new GitHub repository. This does not create it. The user reviews and approves it in the UI. Default to private unless public was requested. Ask for the name if missing.',
    'parameters': {'type': 'object', 'properties': {
        'name': {'type': 'string'}, 'description': {'type': 'string'}, 'private': {'type': 'boolean'}},
        'required': ['name', 'description', 'private'], 'additionalProperties': False}}}
