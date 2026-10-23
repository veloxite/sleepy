"""Provider profiles in SQLite; API keys stay in the OS credential vault."""
import os
import uuid
from urllib.parse import urlsplit
import keyring

def OpenAI(*args,**kwargs):
    """Load the provider SDK only when an API operation actually needs it."""
    from openai import OpenAI as Client
    return Client(*args,**kwargs)

SERVICE = 'Sleepy.API'
PRESETS = {
    'Groq': 'https://api.groq.com/openai/v1',
    'OpenAI': 'https://api.openai.com/v1',
    'OpenRouter': 'https://openrouter.ai/api/v1',
    'Gemini (compatible)': 'https://generativelanguage.googleapis.com/v1beta/openai',
    'Ollama (local)': 'http://localhost:11434/v1',
    'Custom': '',
}
PROVIDER_PRESETS = {
    name: {'base_url': url, 'provider_type': 'anthropic' if name == 'Anthropic' else 'openai_compatible'}
    for name, url in {**PRESETS, 'Anthropic': 'https://api.anthropic.com'}.items()
}

def validate_url(value):
    value = str(value).strip().rstrip('/')
    parts = urlsplit(value)
    if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('Enter an API base URL without credentials, query parameters, or fragments.')
    local = parts.hostname in ('localhost', '127.0.0.1', '::1')
    if parts.scheme != 'https' and not (parts.scheme == 'http' and local):
        raise ValueError('Use HTTPS for remote APIs. HTTP is allowed only on localhost.')
    return value

class Connections:
    def __init__(self, store):
        self.store = store
        if store.get('api_profiles') is None:
            profiles = []
            if os.getenv('GROQ_API_KEY'):
                profiles = [{'id':'legacy-groq', 'name':'Groq', 'base_url':PRESETS['Groq'],
                    'model':os.getenv('GROQ_TEXT_MODEL','openai/gpt-oss-120b'),
                    'vision_model':os.getenv('GROQ_VISION_MODEL','qwen/qwen3.8-27b'),
                    'tools':True, 'token_parameter':'max_completion_tokens', 'models':[]}]
            store.set('api_profiles', profiles)
            store.set('api_active', profiles[0]['id'] if profiles else '')

    def profiles(self):
        profiles = self.store.get('api_profiles', [])
        return [{**p, 'provider_type': p.get('provider_type', 'openai_compatible')} for p in profiles]

    def find(self, profile_id):
        return next((p for p in self.profiles() if p['id'] == profile_id), None)

    def active(self):
        return self.find(self.store.get('api_active', ''))

    def key(self, profile):
        secret = keyring.get_password(SERVICE, profile['id']) or ''
        if not secret and profile['id'] == 'legacy-groq' and profile['base_url'] == PRESETS['Groq']:
            secret = os.getenv('GROQ_API_KEY', '')
        return secret

    def public(self):
        # No key retrieval is needed to list profiles; never emit secrets to the web UI.
        return {'profiles':self.profiles(), 'active':self.store.get('api_active',''), 'presets':PRESETS,
                'provider_presets':PROVIDER_PRESETS, 'usage':self.store.get('api_usage',{}),'credits':self.store.get('api_credits',{})}

    def save(self, data):
        old = self.find(data.get('id'))
        provider_type = str(data.get('provider_type') or (old or {}).get('provider_type') or 'openai_compatible')
        if provider_type not in ('openai_compatible', 'anthropic'):
            raise ValueError('Choose a supported provider type.')
        base_url = validate_url(data.get('base_url',''))
        if provider_type == 'anthropic' and base_url != 'https://api.anthropic.com':
            raise ValueError('Native Anthropic connections use https://api.anthropic.com.')
        secret = str(data.get('key','')).strip()
        if old and (base_url != old['base_url'] or provider_type != old.get('provider_type','openai_compatible')) and not secret:
            raise ValueError('Changing an API address requires a new key. Add a separate connection for a local server.')
        profile = {'id':old['id'] if old else uuid.uuid4().hex,
                   'name':str(data.get('name','')).strip()[:60] or 'My API',
                   'provider_type':provider_type,
                   'base_url':base_url, 'model':str(data.get('model','')).strip()[:200],
                   'vision_model':str(data.get('vision_model','')).strip()[:200],
                   'tools':bool(data.get('tools',False)),
                   'token_parameter':'max_tokens' if provider_type == 'anthropic' else data.get('token_parameter','max_completion_tokens'),
                   'models':old.get('models',[]) if old and base_url == old['base_url'] and provider_type == old.get('provider_type','openai_compatible') else []}
        profile['capabilities'] = old.get('capabilities',{}) if old and base_url == old['base_url'] and provider_type == old.get('provider_type','openai_compatible') else {}
        profile['output_limit'] = max(64,min(16384,int(data.get('output_limit',4096))))
        profile['reasoning'] = data.get('reasoning','') if data.get('reasoning','') in ('','low','medium','high') else ''
        if profile['token_parameter'] not in ('max_completion_tokens','max_tokens'):
            raise ValueError('Select a supported token limit parameter.')
        local = urlsplit(base_url).hostname in ('localhost','127.0.0.1','::1')
        if not secret and not local and not (old and self.key(old)):
            raise ValueError('Enter your API key for this connection.')
        if secret:
            keyring.set_password(SERVICE,profile['id'],secret)
        profiles = [profile if p['id']==profile['id'] else p for p in self.profiles()]
        if not old:
            profiles.append(profile)
        self.store.set('api_profiles',profiles)
        if not self.active():
            self.store.set('api_active',profile['id'])
        return profile

    def select(self, profile_id, model=None, screen=False):
        profile = self.find(profile_id)
        if not profile:
            raise ValueError('Choose an API connection in Settings → Models & APIs.')
        if model is not None:
            profile['vision_model' if screen else 'model'] = str(model).strip()[:200]
            self.store.set('api_profiles',[profile if p['id']==profile_id else p for p in self.profiles()])
        self.store.set('api_active',profile_id)

    def delete(self, profile_id):
        if not self.find(profile_id):
            return
        try:
            keyring.delete_password(SERVICE,profile_id)
        except keyring.errors.PasswordDeleteError:
            pass
        remaining = [p for p in self.profiles() if p['id']!=profile_id]
        self.store.set('api_profiles',remaining)
        if self.store.get('api_active')==profile_id:
            self.store.set('api_active',remaining[0]['id'] if remaining else '')

    def preview(self, data):
        """Build an ephemeral catalog request without saving credentials."""
        url = validate_url(data.get('base_url', ''))
        kind = data.get('provider_type', 'openai_compatible')
        if kind not in ('openai_compatible', 'anthropic'):
            raise ValueError('Choose a supported provider.')
        if kind == 'anthropic' and url != 'https://api.anthropic.com':
            raise ValueError('Native Anthropic uses https://api.anthropic.com.')
        old = self.find(data.get('id'))
        secret = str(data.get('key', '')).strip()
        if not secret and old and old['base_url'] == url and old.get('provider_type','openai_compatible') == kind:
            secret = self.key(old)
        local = urlsplit(url).hostname in ('localhost','127.0.0.1','::1')
        if not secret and not local:
            raise ValueError('Enter your API key, then load available models.')
        return {'base_url':url, 'provider_type':kind, 'api_key':secret or 'local-no-key'}

    def runtime(self, profile_id=None, screen=False, require_model=True):
        profile = self.find(profile_id) if profile_id else self.active()
        if not profile:
            raise ValueError('Add your API connection in Settings → Models & APIs to start chatting.')
        model = profile['vision_model'] if screen else profile['model']
        if require_model and not model:
            raise ValueError('Choose a screen-capable model in Models & APIs, or turn Screen off.' if screen else 'Choose a chat model in Models & APIs.')
        meta=profile.get('capabilities',{}).get(model,{})
        if require_model and (meta.get('text') is False or (screen and meta.get('vision') is False)):
            raise ValueError('Provider metadata marks this model incompatible. Choose a different model or turn Screen off.')
        local = urlsplit(profile['base_url']).hostname in ('localhost','127.0.0.1','::1')
        secret = self.key(profile)
        if not secret and not local:
            raise ValueError('This connection has no API key. Add one in Models & APIs.')
        return {**profile, 'api_key':secret or 'local-no-key', 'selected_model':model}

    def cache_models(self, profile_id, models):
        profile = self.find(profile_id)
        if profile:
            profile['models'] = models['models'] if isinstance(models,dict) else models
            if isinstance(models,dict):
                profile['capabilities']=models['capabilities']
            self.store.set('api_profiles',[profile if p['id']==profile_id else p for p in self.profiles()])

def fetch_models(config):
    return fetch_catalog(config)['models']

def fetch_catalog(config):
    from provider_adapters import adapter_for
    adapter = adapter_for(config, timeout=25)
    try:
        return adapter.list_catalog()
    finally:
        adapter.close()

def test_connection(config, screen=False):
    from agent_core import Agent, encode_image
    from PIL import Image
    agent=Agent({**config,'output_limit':256,'tools':False})
    try:
        answer=agent.reply('Reply with a short greeting.' if not screen else 'Name the color of this test image.',
                           encode_image(Image.new('RGB',(32,32),'red')) if screen else None)
        return {'message':('Screen model' if screen else 'Chat model')+' responded successfully: '+answer[:160],
                'usage':agent.usage_report,'model':config['vision_model'] if screen else config['model']}
    finally:
        agent.close()
