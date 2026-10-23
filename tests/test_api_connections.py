import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from api_connections import Connections, PRESETS, SERVICE, validate_url
from local_store import Store


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.folder.name)/'test.sqlite3')
        self.vault={}
        self.patches=[patch.dict(os.environ,{'GROQ_API_KEY':''}),
            patch('api_connections.keyring.get_password',side_effect=lambda s,k:self.vault.get((s,k))),
            patch('api_connections.keyring.set_password',side_effect=lambda s,k,v:self.vault.update({(s,k):v})),
            patch('api_connections.keyring.delete_password',side_effect=lambda s,k:self.vault.pop((s,k),None))]
        for p in self.patches:p.start()
        self.connections=Connections(self.store)

    def tearDown(self):
        for p in self.patches:p.stop()
        self.store.close()
        self.folder.cleanup()

    def add(self,**extra):
        return self.connections.save({'name':'Test','base_url':PRESETS['Groq'],'key':'test-private-key',
            'model':'chat-model','vision_model':'vision-model','tools':True,**extra})

    def test_keys_never_in_database_or_public_state(self):
        p=self.add()
        self.assertEqual(self.connections.runtime()['api_key'],'test-private-key')
        self.assertNotIn('test-private-key',json.dumps(self.connections.public()))
        self.assertNotIn(b'test-private-key',self.store.path.read_bytes())
        self.assertEqual(self.vault[(SERVICE,p['id'])],'test-private-key')

    def test_catalog_preview_does_not_save_credentials_or_profiles(self):
        config=self.connections.preview({'base_url':PRESETS['Groq'],'key':'preview-only-key'})
        self.assertEqual(config['api_key'],'preview-only-key')
        self.assertEqual(self.connections.profiles(),[])
        self.assertEqual(self.vault,{})
        self.assertNotIn(b'preview-only-key',self.store.path.read_bytes())

    def test_catalog_preview_never_reuses_key_for_changed_host(self):
        profile=self.add()
        self.assertEqual(self.connections.preview({'id':profile['id'],'base_url':PRESETS['Groq']})['api_key'],'test-private-key')
        with self.assertRaises(ValueError):
            self.connections.preview({'id':profile['id'],'base_url':'https://example.com/v1'})

    def test_switching_connections_and_chat_vs_screen_models(self):
        first=self.add()
        second=self.add(name='Second',model='second-chat',vision_model='second-vision')
        self.connections.select(second['id'])
        self.assertEqual(self.connections.runtime()['selected_model'],'second-chat')
        self.assertEqual(self.connections.runtime(screen=True)['selected_model'],'second-vision')
        self.connections.select(second['id'],'another-vision',screen=True)
        self.assertEqual(self.connections.runtime(screen=True)['selected_model'],'another-vision')
        self.assertEqual(self.connections.runtime()['selected_model'],'second-chat')
        self.connections.delete(second['id'])
        self.assertEqual(self.connections.active()['id'],first['id'])
        self.assertNotIn((SERVICE,second['id']),self.vault)

    def test_changed_host_requires_new_credential(self):
        p=self.add()
        with self.assertRaises(ValueError):
            self.add(id=p['id'],base_url='https://other.example/v1',key='')
        self.assertEqual(self.connections.active()['base_url'],PRESETS['Groq'])

    def test_local_server_needs_no_key_but_remote_does(self):
        self.add(base_url=PRESETS['Ollama (local)'],key='')
        self.assertEqual(self.connections.runtime()['api_key'],'local-no-key')
        with self.assertRaises(ValueError):self.add(key='')

    def test_missing_vision_model_stops_before_request(self):
        self.add(vision_model='')
        with self.assertRaises(ValueError):self.connections.runtime(screen=True)
        self.assertEqual(self.connections.runtime()['selected_model'],'chat-model')

    def test_url_rejects_remote_http_and_embedded_credentials(self):
        for url in ['http://remote.example/v1','https://name:secret@host/v1','https://host/v1?key=secret','file:///test','https://host/#key']:
            with self.assertRaises(ValueError):validate_url(url)
        self.assertEqual(validate_url('http://localhost:11434/v1/'),'http://localhost:11434/v1')

    def test_existing_environment_connection_is_migrated_without_storing_key(self):
        self.store.db.execute("DELETE FROM settings WHERE key='api_profiles'")
        self.store.db.commit()
        with patch.dict(os.environ,{'GROQ_API_KEY':'legacy-private-key'}):
            c=Connections(self.store)
            self.assertEqual(c.runtime()['api_key'],'legacy-private-key')
            self.assertNotIn('legacy-private-key',json.dumps(c.public()))

    def test_anthropic_profile_is_native_and_keeps_key_in_vault(self):
        profile=self.add(name='Anthropic',base_url='https://api.anthropic.com',provider_type='anthropic',
                         key='sk-ant-private',token_parameter='max_completion_tokens')
        runtime=self.connections.runtime(profile['id'])
        self.assertEqual(runtime['provider_type'],'anthropic')
        self.assertEqual(runtime['token_parameter'],'max_tokens')
        self.assertNotIn('sk-ant-private',json.dumps(self.connections.public()))
        self.assertEqual(self.connections.public()['provider_presets']['Anthropic']['provider_type'],'anthropic')

    def test_old_profiles_remain_openai_compatible(self):
        profile=self.add()
        raw=self.store.get('api_profiles');raw[0].pop('provider_type',None);self.store.set('api_profiles',raw)
        self.assertEqual(self.connections.runtime(profile['id'])['provider_type'],'openai_compatible')

if __name__=='__main__':unittest.main()
