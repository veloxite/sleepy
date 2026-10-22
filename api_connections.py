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
        return self.store.get('api_profiles', [])

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
        return {'profiles':self.profiles(), 'active':self.store.get('api_active',''), 'presets':PRESETS, 'usage':self.store.get('api_usage',{}),'credits':self.store.get('api_credits',{})}

    def save(self, data):
        old = self.find(data.get('id'))
        base_url = validate_url(data.get('base_url',''))
        secret = str(data.get('key','')).strip()
        if old and base_url != old['base_url'] and not secret:
            raise ValueError('Changing an API address requires a new key. Add a separate connection for a local server.')
        profile = {'id':old['id'] if old else uuid.uuid4().hex,
                   'name':str(data.get('name','')).strip()[:60] or 'My API',
                   'base_url':base_url, 'model':str(data.get('model','')).strip()[:200],
                   'vision_model':str(data.get('vision_model','')).strip()[:200],
                   'tools':bool(data.get('tools',False)),
                   'token_parameter':data.get('token_parameter','max_completion_tokens'),
                   'models':old.get('models',[]) if old and base_url == old['base_url'] else []}
        profile['capabilities'] = old.get('capabilities',{}) if old and base_url == old['base_url'] else {}
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
    with OpenAI(api_key=config['api_key'],base_url=config['base_url'],timeout=25,max_retries=0) as client:
        return sorted({m.id for m in client.models.list()})

def fetch_catalog(config):
    with OpenAI(api_key=config['api_key'],base_url=config['base_url'],timeout=25,max_retries=0) as client:
        models=list(client.models.list())
    capabilities={}
    for model in models:
        data=model.model_dump()
        architecture=data.get('architecture') or {}
        inputs=architecture.get('input_modalities')
        outputs=architecture.get('output_modalities')
        params=data.get('supported_parameters')
        provider=data.get('top_provider') or {}
        def positive(value):
            return value if isinstance(value,int) and not isinstance(value,bool) and value>0 else None
        capabilities[model.id]={
            'text': 'text' in outputs if isinstance(outputs,list) else None,
            'vision': 'image' in inputs if isinstance(inputs,list) else None,
            'tools': 'tools' in params if isinstance(params,list) else None,
            'structured': any(p in params for p in ('structured_outputs','response_format')) if isinstance(params,list) else None,
            'reasoning': 'reasoning_effort' in params if isinstance(params,list) else None,
            'context': positive(data.get('context_length') or data.get('context_window')),
            'max_output': positive(provider.get('max_completion_tokens') or data.get('max_completion_tokens'))}
    return {'models':sorted(capabilities),'capabilities':capabilities}

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
        agent.client.close()
