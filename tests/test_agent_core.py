import base64
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image
from agent_core import Agent, encode_image, friendly_error


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = Agent.__new__(Agent)
        self.agent.client = Mock()
        self.agent.text_model = "text-model"
        self.agent.vision_model = "vision-model"
        self.agent.history = []
        self.agent.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="An answer"))])

    def test_image_routing_and_no_image_retention(self):
        url = encode_image(Image.new("RGB", (10, 10), "red"))
        self.agent.reply("What color?", url)
        request = self.agent.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "vision-model")
        self.assertEqual(request["messages"][-1]["content"][1]["image_url"]["url"], url)
        self.agent.reply("Explain more")
        request = self.agent.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "text-model")
        self.assertNotIn("data:image", str(request["messages"]))
        self.assertIn('successfully captured screen image', request['messages'][0]['content'])
        self.assertTrue(all(set(m) == {'role', 'content'} for m in request['messages']))

    def test_failed_call_preserves_history(self):
        self.agent.reply("Hello")
        before = list(self.agent.history)
        self.agent.client.chat.completions.create.side_effect = RuntimeError("Failure")
        with self.assertRaises(RuntimeError):
            self.agent.reply("Another question")
        self.assertEqual(self.agent.history, before)

    def test_history_is_bounded_in_complete_pairs(self):
        for i in range(12):
            self.agent.reply(str(i))
        self.assertEqual(len(self.agent.history), 16)
        self.assertEqual(self.agent.history[0]["content"], "4")
        self.assertEqual(self.agent.history[-1]["role"], "assistant")

    def test_image_size_limit_and_format(self):
        url = encode_image(Image.new("RGBA", (4000, 2000)))
        decoded = Image.open(io.BytesIO(base64.b64decode(url.split(",")[1])))
        self.assertLessEqual(decoded.width*decoded.height,4000000)
        self.assertLessEqual(decoded.width,3200)
        self.assertEqual(decoded.format, "PNG")

    def test_error_does_not_echo_secret_details(self):
        self.assertNotIn("secret", friendly_error(RuntimeError("secret")))

    def test_saved_memories_are_sent(self):
        self.agent.reply('Explain energy', memories='Start with intuition')
        request = self.agent.client.chat.completions.create.call_args.kwargs
        self.assertIn('Start with intuition', request['messages'][0]['content'])


if __name__ == "__main__":
    unittest.main()
