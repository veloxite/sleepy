"""Only retain provider-reported counters and allowlisted quota headers."""
from datetime import datetime, timezone

def credits(config):
    import json
    import urllib.request
    import urllib.error
    if config['base_url']!='https://openrouter.ai/api/v1':
        raise ValueError('This provider does not expose an account-credit balance here. Sleepy shows reported request limits instead.')
    def get(path):
        request=urllib.request.Request('https://openrouter.ai/api/v1/'+path,headers={'Authorization':'Bearer '+config['api_key']})
        with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)['data']
    key=get('key')
    if key.get('limit') is not None and key.get('limit_remaining') is not None:
        total=float(key['limit']);remaining=float(key['limit_remaining']);unit='USD key allowance'
    else:
        try:data=get('credits')
        except urllib.error.HTTPError as error:
            if error.code==403:raise ValueError('OpenRouter does not expose an account balance to this key. No remaining credit amount was guessed. Check the provider dashboard, or use a key with a defined spending allowance.') from None
            raise
        total=float(data['total_credits']);remaining=max(0,total-float(data['total_usage']));unit='USD account credits'
    return {'total':total,'used':max(0,total-remaining),'remaining':remaining,'unit':unit,'at':datetime.now(timezone.utc).isoformat(timespec='seconds')}

def metrics(result=None, headers=None):
    usage = getattr(result,'usage',None)
    counts = {}
    for key in ('prompt_tokens','completion_tokens','total_tokens'):
        value = getattr(usage,key,None)
        if isinstance(value,int) and value>=0:
            counts[key]=value
    if usage is not None and not counts:
        direct = {key:getattr(usage,key,None) for key in
                  ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')}
        for key,value in direct.items():
            if isinstance(value,int) and value>=0:counts[key]=value
        if 'input_tokens' in counts:
            counts['prompt_tokens']=sum(counts.get(k,0) for k in
                ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens'))
        if 'output_tokens' in counts:counts['completion_tokens']=counts['output_tokens']
        if 'prompt_tokens' in counts or 'completion_tokens' in counts:
            counts['total_tokens']=counts.get('prompt_tokens',0)+counts.get('completion_tokens',0)
    limits = {}
    for key,value in (headers or {}).items():
        key=key.lower()
        if key in ('retry-after','x-ratelimit-limit-requests','x-ratelimit-limit-tokens','x-ratelimit-remaining-requests','x-ratelimit-remaining-tokens','x-ratelimit-reset-requests','x-ratelimit-reset-tokens',
                   'anthropic-ratelimit-requests-limit','anthropic-ratelimit-requests-remaining','anthropic-ratelimit-requests-reset',
                   'anthropic-ratelimit-tokens-limit','anthropic-ratelimit-tokens-remaining','anthropic-ratelimit-tokens-reset',
                   'anthropic-ratelimit-input-tokens-limit','anthropic-ratelimit-input-tokens-remaining','anthropic-ratelimit-input-tokens-reset',
                   'anthropic-ratelimit-output-tokens-limit','anthropic-ratelimit-output-tokens-remaining','anthropic-ratelimit-output-tokens-reset'):
            limits[key]=str(value)[:100]
    return {'tokens':counts,'limits':limits,'at':datetime.now(timezone.utc).isoformat(timespec='seconds')}

def record(store, profile, model, report):
    if not report:
        return
    all_usage=store.get('api_usage',{})
    entry=all_usage.setdefault(profile,{'requests':0,'total_tokens':0,'unreported':0,'models':{}})
    entry['requests']+=1
    total=report.get('tokens',{}).get('total_tokens')
    if total is None:
        entry['unreported']+=1
    else:
        entry['total_tokens']+=total
    entry['models'][model]=report
    store.set('api_usage',all_usage)
