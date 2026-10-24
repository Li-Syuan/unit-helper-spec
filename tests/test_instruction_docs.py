"""Offline documentation contracts; these tests do not evaluate any real model."""
import re
import unittest
from pathlib import Path

from desktop_app.workflows import WorkflowService, json_object


ROOT = Path(__file__).resolve().parents[1] / 'docs' / 'assistant-instructions'


def examples(name):
    return [json_object(block) for block in re.findall(
        r'```json\s*\n(.*?)\n```', (ROOT / name).read_text(encoding='utf-8'), re.S)]


class InstructionDocumentTests(unittest.TestCase):
    def test_planner_question_example_obeys_live_question_contract(self):
        service = object.__new__(WorkflowService)
        for result in examples('planner.md'):
            self.assertEqual(set(result), {'message', 'questions', 'steps'})
            self.assertTrue(service._questions(result['questions']))
            self.assertEqual(result['steps'], [])

    def test_role_examples_preserve_exact_facts_and_output_contract(self):
        for role in ('analysis', 'review', 'compose'):
            with self.subTest(role=role):
                for result in examples(role + '.md'):
                    expected = {'text', 'facts', 'verdict'} if role == 'review' else {'text', 'facts'}
                    self.assertEqual(set(result), expected)
                    self.assertEqual(result['facts'], {'quantity': '12.50'})
                    self.assertIsInstance(result['facts']['quantity'], str)
                    self.assertTrue(result['text'].strip())
                    self.assertLessEqual(len(result['text']), 12000)
                    if role == 'review':
                        self.assertEqual(result['verdict'], 'needs_attention')

    def test_compose_example_has_readable_literal_headings(self):
        text = examples('compose.md')[0]['text']
        headings = ['結論', '需要注意', '待確認與決策']
        lines = text.splitlines()
        self.assertEqual([line for line in lines if line in headings], headings)

    def test_search_role_example_does_not_invent_program_facts(self):
        result=examples('rag.md')[0]
        self.assertEqual(set(result),{'text','facts'})
        self.assertEqual(result['facts'],{})
        self.assertTrue(result['text'].strip())
        self.assertLessEqual(len(result['text']),12000)

    def test_guide_synthetic_examples_link_facts_to_source(self):
        payload, analysis, planner, review = examples('README.md')
        facts = payload['sources']['s1']['numeric_totals']
        self.assertEqual(analysis['facts'], facts)
        self.assertEqual(review['facts'], facts)
        self.assertEqual(review['verdict'], 'needs_attention')
        self.assertEqual(planner['steps'], [])
        self.assertTrue(object.__new__(WorkflowService)._questions(planner['questions']))

    def test_documents_are_standalone_and_local_links_resolve(self):
        for role in ('planner', 'analysis', 'review', 'compose'):
            text = (ROOT / (role + '.md')).read_text(encoding='utf-8')
            self.assertIn('## 共用規則', text)
            self.assertIn('## 精確輸出契約', text)
        guide = (ROOT / 'README.md').read_text(encoding='utf-8')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', guide):
            location, _, fragment = target.partition('#')
            path = (ROOT / location).resolve()
            self.assertTrue(path.is_file(), target)
            if fragment:
                headings = re.findall(r'^#{1,6}\s+(.+)$', path.read_text('utf-8'), re.M)
                anchors = {re.sub(r'[^\w\s-]', '', heading).lower().replace(' ', '-') for heading in headings}
                self.assertIn(fragment, anchors, target)
        self.assertIn('not_tested', guide)
        self.assertIn('不能保證零幻覺', guide)


if __name__ == '__main__':
    unittest.main()
