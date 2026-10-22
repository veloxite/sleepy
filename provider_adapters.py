"""Small provider boundary for native and OpenAI-compatible chat APIs."""
import json
import re


def _dump(value):
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return vars(value)


def _positive(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


class OpenAICompatibleAdapter:
    provider_type = 'openai_compatible'

    def __init__(self, config, client=None, timeout=60):
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=config['api_key'], base_url=config['base_url'],
                            timeout=timeout, max_retries=0)
        self.client = client

    def complete(self, *, system, history, question, image_url, model, max_tokens,
                 token_parameter='max_completion_tokens', tools=None, reasoning='', capture_usage=True):
        content = question
        if image_url:
            content = [{'type': 'text', 'text': question},
                       {'type': 'image_url', 'image_url': {'url': image_url}}]
        messages = [{'role': 'system', 'content': system}]
        messages.extend({'role': item['role'], 'content': item['content']} for item in history)
        messages.append({'role': 'user', 'content': content})
        options = {token_parameter: max_tokens}
        if tools:
            options.update(tools=tools, tool_choice='auto')
        if reasoning:
            options['reasoning_effort'] = reasoning
        if capture_usage:
            raw = self.client.chat.completions.with_raw_response.create(model=model, messages=messages, **options)
            result, headers = raw.parse(), raw.headers
        else:
            result = self.client.chat.completions.create(model=model, messages=messages, **options)
            headers = None
        message = result.choices[0].message
        calls = []
        for call in getattr(message, 'tool_calls', None) or []:
            calls.append({'name': call.function.name, 'arguments': json.loads(call.function.arguments)})
        return {'text': message.content, 'tool_calls': calls, 'result': result, 'headers': headers}

    def list_catalog(self):
        models = list(self.client.models.list())
        capabilities = {}
        for model in models:
            data = _dump(model)
            architecture = data.get('architecture') or {}
            inputs, outputs = architecture.get('input_modalities'), architecture.get('output_modalities')
            params = data.get('supported_parameters')
            provider = data.get('top_provider') or {}
            capabilities[model.id] = {
                'text': 'text' in outputs if isinstance(outputs, list) else None,
                'vision': 'image' in inputs if isinstance(inputs, list) else None,
                'tools': 'tools' in params if isinstance(params, list) else None,
                'structured': any(p in params for p in ('structured_outputs', 'response_format')) if isinstance(params, list) else None,
                'reasoning': 'reasoning_effort' in params if isinstance(params, list) else None,
                'context': _positive(data.get('context_length') or data.get('context_window')),
                'max_output': _positive(provider.get('max_completion_tokens') or data.get('max_completion_tokens'))}
        return {'models': sorted(capabilities), 'capabilities': capabilities}

    def close(self):
        self.client.close()


class AnthropicAdapter:
    provider_type = 'anthropic'
    _IMAGE = re.compile(r'^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$')

    def __init__(self, config, client=None, timeout=60):
        if client is None:
            from anthropic import Anthropic
            client = Anthropic(api_key=config['api_key'], timeout=timeout, max_retries=0)
        self.client = client

    @staticmethod
    def _tools(tools):
        native = []
        for tool in tools or []:
            function = tool.get('function', tool)
            native.append({'name': function['name'], 'description': function.get('description', ''),
                           'input_schema': function.get('parameters', {'type': 'object'})})
        return native

    def complete(self, *, system, history, question, image_url, model, max_tokens,
                 token_parameter='max_tokens', tools=None, reasoning='', capture_usage=True):
        del token_parameter, reasoning
        content = question
        if image_url:
            match = self._IMAGE.fullmatch(image_url)
            if not match:
                raise ValueError('The captured screen image has an unsupported format. Select a screen area and try again.')
            content = [{'type': 'image', 'source': {'type': 'base64', 'media_type': match.group(1), 'data': match.group(2)}},
                       {'type': 'text', 'text': question}]
        messages = [{'role': item['role'], 'content': item['content']} for item in history]
        messages.append({'role': 'user', 'content': content})
        options = {'model': model, 'max_tokens': max_tokens, 'system': system, 'messages': messages}
        native_tools = self._tools(tools)
        if native_tools:
            options['tools'] = native_tools
        if capture_usage:
            raw = self.client.messages.with_raw_response.create(**options)
            result, headers = raw.parse(), raw.headers
        else:
            result = self.client.messages.create(**options)
            headers = None
        text, calls = [], []
        for block in result.content:
            kind = getattr(block, 'type', None)
            if kind == 'text':
                text.append(block.text)
            elif kind == 'tool_use':
                calls.append({'name': block.name, 'arguments': block.input})
        return {'text': '\n'.join(text).strip(), 'tool_calls': calls, 'result': result, 'headers': headers}

    def list_catalog(self):
        page = self.client.models.list(limit=1000)
        capabilities = {}
        for model in page.data:
            data = _dump(model)
            caps = data.get('capabilities') or {}
            def supported(*names):
                value = next((caps[n] for n in names if n in caps), None)
                if isinstance(value, dict):
                    value = value.get('supported', value.get('enabled'))
                return value if isinstance(value, bool) else None
            capabilities[model.id] = {
                'text': True,
                'vision': supported('vision', 'image_input'),
                'tools': supported('tool_use', 'tools'),
                'structured': supported('structured_outputs'),
                'reasoning': supported('thinking', 'extended_thinking'),
                'context': _positive(data.get('context_window')),
                'max_output': _positive(data.get('max_output_tokens'))}
        return {'models': sorted(capabilities), 'capabilities': capabilities}

    def close(self):
        self.client.close()


def adapter_for(config, client=None, timeout=60):
    provider = config.get('provider_type', 'openai_compatible')
    if provider == 'anthropic':
        return AnthropicAdapter(config, client, timeout)
    if provider == 'openai_compatible':
        return OpenAICompatibleAdapter(config, client, timeout)
    raise ValueError('This provider type is not supported.')
