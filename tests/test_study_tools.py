import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from study_tools import command_for, validate
from provider_usage import metrics, record
from local_store import Store
from agent_core import Agent

class StudyTests(unittest.TestCase):
    def test_commands_only_at_start(self):
        self.assertEqual(command_for('/mermaid, draw this'),'mermaid')
        self.assertIsNone(command_for('Discuss /mermaid'))

    def test_flashcards_and_removed_tools(self):
        self.assertEqual(validate('flashcards','{"cards":[{"front":"Q","back":"A"}]}')['cards'][0]['back'],'A')
        for raw in ['{"cards":[]}','{"cards":[{"front":"Q"}]}']:
            with self.assertRaises(ValueError):validate('flashcards',raw)
        with self.assertRaises(ValueError):validate('desmos',json.dumps({'expressions':['x']*21}))

    def test_usage_reports_only_allowed_fields_and_missing_is_unknown(self):
        report=metrics(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=5,completion_tokens=7,total_tokens=12)),{'authorization':'secret','x-ratelimit-remaining-tokens':'100'})
        self.assertNotIn('secret',json.dumps(report))
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/'test.db')
            record(store,'profile','model',report)
            record(store,'profile','model',metrics())
            entry=store.get('api_usage')['profile']
            self.assertEqual((entry['requests'],entry['total_tokens'],entry['unreported']),(2,12,1))
            store.close()

    def test_study_routing_and_output_limit(self):
        a=Agent.__new__(Agent);a.client=Mock();a.text_model='test';a.vision_model='vision';a.history=[]
        a.config={'output_limit':2000,'capabilities':{'test':{'max_output':500}}}
        a.client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Study result'))])
        a.reply('/flashcards explain energy',github=True)
        request=a.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request['max_completion_tokens'],500)
        self.assertNotIn('tools',request)
        self.assertIn('one ```flashcards block',request['messages'][0]['content'])

    def test_screen_marker_only_after_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/'test.db');cid=store.new_chat()
            mid=store.add(cid,'user','Question')
            self.assertFalse(store.messages(cid)[0]['screen'])
            store.mark_screen(mid);self.assertTrue(store.messages(cid)[0]['screen']);store.close()

if __name__=='__main__':unittest.main()
