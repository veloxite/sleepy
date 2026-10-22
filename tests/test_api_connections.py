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

if __name__=='__main__':unittest.main()
