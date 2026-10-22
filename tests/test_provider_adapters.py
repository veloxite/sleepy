import base64
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from agent_core import friendly_error
from provider_adapters import AnthropicAdapter, OpenAICompatibleAdapter, adapter_for
from provider_usage import metrics


class Raw:
    def __init__(self, value, headers=None):self.value=value;self.headers=headers or {}
    def parse(self):return self.value


class ProviderAdapterTests(unittest.TestCase):
    def test_anthropic_request_uses_native_system_image_and_tools(self):
        client=Mock()
        reply=SimpleNamespace(content=[SimpleNamespace(type='text',text='I see red'),
            SimpleNamespace(type='tool_use',name='propose_github_repository',input={'name':'demo'})],
            usage=SimpleNamespace(input_tokens=10,output_tokens=4))
        client.messages.with_raw_response.create.return_value=Raw(reply,{'anthropic-ratelimit-requests-remaining':'49'})
        adapter=AnthropicAdapter({'api_key':'hidden'},client)
        result=adapter.complete(system='Be useful',history=[{'role':'user','content':'Earlier'}],question='Look',
            image_url='data:image/png;base64,'+base64.b64encode(b'png').decode(),model='claude-test',max_tokens=123,
            tools=[{'type':'function','function':{'name':'propose_github_repository','description':'Prepare','parameters':{'type':'object'}}}])
        request=client.messages.with_raw_response.create.call_args.kwargs
        self.assertEqual(request['system'],'Be useful')
        self.assertNotIn('system',[m['role'] for m in request['messages']])
        self.assertEqual(request['messages'][-1]['content'][0]['source']['media_type'],'image/png')
        self.assertNotIn('data:image',request['messages'][-1]['content'][0]['source']['data'])
        self.assertEqual(request['tools'][0]['input_schema'],{'type':'object'})
        self.assertEqual(result['text'],'I see red')
        self.assertEqual(result['tool_calls'][0]['arguments'],{'name':'demo'})

    def test_anthropic_usage_is_normalized_and_headers_allowlisted(self):
        result=SimpleNamespace(usage=SimpleNamespace(input_tokens=10,output_tokens=4,
            cache_creation_input_tokens=3,cache_read_input_tokens=2))
        report=metrics(result,{'anthropic-ratelimit-tokens-remaining':'900','authorization':'secret'})
        self.assertEqual(report['tokens']['prompt_tokens'],15)
        self.assertEqual(report['tokens']['completion_tokens'],4)
        self.assertEqual(report['tokens']['total_tokens'],19)
        self.assertNotIn('authorization',report['limits'])

    def test_anthropic_catalog_preserves_unknown_capabilities(self):
        client=Mock();client.models.list.return_value=SimpleNamespace(data=[SimpleNamespace(id='claude-a',capabilities={'vision':True},context_window=200000,max_output_tokens=8192)])
        catalog=AnthropicAdapter({'api_key':'hidden'},client).list_catalog()
        self.assertEqual(catalog['models'],['claude-a'])
        self.assertTrue(catalog['capabilities']['claude-a']['vision'])
        self.assertIsNone(catalog['capabilities']['claude-a']['tools'])

    def test_existing_profiles_default_to_openai_compatible_adapter(self):
        client=Mock()
        self.assertIsInstance(adapter_for({},client),OpenAICompatibleAdapter)

    def test_anthropic_rejects_non_data_image_before_network(self):
        client=Mock();adapter=AnthropicAdapter({'api_key':'hidden'},client)
        with self.assertRaisesRegex(ValueError,'unsupported format'):
            adapter.complete(system='s',history=[],question='q',image_url='https://example.test/private.png',
                             model='claude-test',max_tokens=10)
        client.messages.create.assert_not_called()

    def test_anthropic_error_is_specific_and_secret_is_redacted(self):
        error=RuntimeError();error.status_code=403;error.body={'error':{'message':'api_key=sk-ant-secret'}};error.request_id='req_123'
        message=friendly_error(error)
        self.assertIn('HTTP 403',message);self.assertIn('req_123',message);self.assertNotIn('sk-ant-secret',message)


if __name__=='__main__':unittest.main()
