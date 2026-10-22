import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from agent_core import Agent
import github_plugin

class GitHubTests(unittest.TestCase):
    def test_invalid_repository_names_cannot_be_sent(self):
        for name in ('../bad','x/y','', '.', '..', 'name with spaces'):
            with self.assertRaises(ValueError):
                github_plugin.validate_repo({'name': name})
        self.assertTrue(github_plugin.validate_repo({'name':'hello-world'})['private'])

    def test_create_sends_reviewed_values(self):
        with patch('github_plugin.request', return_value={'full_name':'me/test','html_url':'https://github.com/me/test'}) as request:
            github_plugin.create_repo({'name':'test','description':'Example','private':False})
            request.assert_called_once_with('POST','/user/repos',{'name':'test','description':'Example','private':False,'auto_init':True})

    def test_model_tool_prepares_without_creating(self):
        agent=Agent.__new__(Agent)
        agent.client=Mock()
        agent.history=[]
        agent.text_model='text'
        agent.vision_model='vision'
        call=SimpleNamespace(function=SimpleNamespace(name='propose_github_repository',arguments='{"name":"test","description":"Example","private":true}'))
        agent.client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None,tool_calls=[call]))])
        with patch('github_plugin.create_repo') as create:
            result=agent.reply('Create a private repo called test',github=True)
            self.assertIn('Review',result)
            self.assertEqual(agent.pending_action['name'],'test')
            create.assert_not_called()

if __name__=='__main__':
    unittest.main()
