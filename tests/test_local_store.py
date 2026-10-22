import tempfile
import unittest
from pathlib import Path
from local_store import Store

class StoreTests(unittest.TestCase):
    def test_bounded_context_and_unchanged_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'test.db');cid=store.new_chat()
            for i in range(30):
                store.add(cid,'user' if i%2==0 else 'assistant',str(i))
                store.add(cid,'error','not model context')
            self.assertEqual([m['content'] for m in store.recent_context(cid)],[str(i) for i in range(14,30)])
            store.set('draft','hello');changes=store.db.total_changes
            store.set('draft','hello');self.assertEqual(store.db.total_changes,changes)
            store.set('draft','edited');self.assertEqual(store.get('draft'),'edited')
            store.close()
    def test_restart_history_memories_and_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.db'
            store = Store(path)
            cid = store.new_chat()
            store.add(cid, 'user', 'Solve problem 3.14', True)
            store.add(cid, 'assistant', 'An explanation')
            store.set('memories', 'Explain intuitively first')
            store.close()
            store = Store(path)
            self.assertEqual(store.chats()[0]['title'], 'Solve problem 3.14')
            self.assertEqual(len(store.messages(cid)), 2)
            self.assertEqual(store.messages(cid)[0]['screen'], 1)
            self.assertEqual(store.get('memories'), 'Explain intuitively first')
            store.delete(cid)
            self.assertEqual(store.chats(), [])
            self.assertEqual(store.messages(cid), [])
            self.assertEqual(store.get('memories'), 'Explain intuitively first')
            store.close()

if __name__ == '__main__':
    unittest.main()
