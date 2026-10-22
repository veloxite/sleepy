import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from agent_core import encode_image,friendly_error
from desktop_actions import explicit_action,file_plan,execute_plan,safe_url
from local_store import Store
from study_tools import command_for

class DesktopFeatureTests(unittest.TestCase):
    def test_blank_chats_not_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            s=Store(Path(folder)/'test.db');first=s.new_chat();second=s.new_chat()
            self.assertNotEqual(first,second);self.assertEqual(s.chats(),[])
            s.add(second,'user','Hello');self.assertEqual(len(s.chats()),1);s.close()

    def test_file_plan_confined_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'a.pdf').write_bytes(b'example')
            with self.assertRaises(ValueError):file_plan(root,{'kind':'create_folder','name':'../escape'})
            with self.assertRaises(ValueError):file_plan(root,{'kind':'rename_file','source':'a.pdf','target':'a.pdf'})
            plan=file_plan(root,{'kind':'rename_file','source':'a.pdf','target':'notes/b.pdf'})
            self.assertTrue((root/'a.pdf').exists());execute_plan(plan)
            self.assertEqual((root/'notes/b.pdf').read_bytes(),b'example')
            (root/'another.pdf').write_bytes(b'another')
            plan=file_plan(root,{'kind':'organize_pdfs'});self.assertEqual(len(plan),1);execute_plan(plan)
            self.assertTrue(list((root/'PDFs').glob('*/*.pdf')))

    def test_actions_use_registered_names(self):
        apps=[{'name':'Calculator','path':'ignored'}];presets=[{'name':'Physics'}]
        self.assertEqual(explicit_action('Sleepy open my physics preset',apps,presets)['kind'],'open_preset')
        self.assertEqual(explicit_action('Open Calculator',apps,presets)['kind'],'open_app')
        self.assertIsNone(explicit_action('Explain how to open Calculator',apps,presets))
        self.assertEqual(explicit_action('Play Piano Man',apps,presets)['query'],'Piano Man')
        with self.assertRaises(ValueError):safe_url('javascript:alert(1)')

    def test_image_payload_bounded(self):
        image=Image.effect_noise((3000,2000),100).convert('RGB')
        result=encode_image(image,max_bytes=1000000)
        self.assertLessEqual(len(result),1000000)
        with self.assertRaises(ValueError):encode_image(image,max_bytes=10)

    def test_specific_error_scrubs_credentials(self):
        class ProviderError(Exception):
            status_code=413
            body={'error':{'message':'Image size too large, api_key=gsk_exampleSecret'}}
        answer=friendly_error(ProviderError())
        self.assertIn('Select a screen area',answer);self.assertIn('413',answer);self.assertNotIn('exampleSecret',answer)

    def test_natural_study_requests(self):
        self.assertEqual(command_for('Make a flowchart of this process'),'mermaid')
        self.assertEqual(command_for('Create flashcards for this page'),'flashcards')
        self.assertEqual(command_for('/eli5 electromagnetism'),'eli5')
        self.assertIsNone(command_for('/desmos y=x^2'))

if __name__=='__main__':unittest.main()
