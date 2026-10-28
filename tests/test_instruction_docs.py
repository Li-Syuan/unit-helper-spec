"""Offline documentation contracts; these tests do not evaluate any real model."""
import hashlib
import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt

from desktop_app.workflows import WorkflowService, json_object


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'docs' / 'assistant-instructions'


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
        self.assertIn('not_tested', guide)
        self.assertIn('不能保證零幻覺', guide)

        # Validate discoverable metadata and portable references, not prompt wording.
        skills = sorted((REPO / '.github' / 'skills').glob('*/SKILL.md'))
        self.assertTrue(skills, 'No development skills discovered')
        names = set()
        for skill in skills:
            with self.subTest(skill=skill.relative_to(REPO).as_posix()):
                text = skill.read_text('utf-8')
                match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
                self.assertIsNotNone(match)
                metadata = yaml.safe_load(match.group(1))
                self.assertIsInstance(metadata, dict)
                self.assertIsInstance(metadata.get('name'), str)
                name = metadata['name']
                self.assertRegex(name, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
                self.assertLessEqual(len(name), 64)
                self.assertEqual(name, skill.parent.name)
                self.assertNotIn(name, names)
                names.add(name)
                self.assertIsInstance(metadata.get('description'), str)
                self.assertTrue(metadata['description'].strip())
                self.assertIs(metadata.get('disable-model-invocation'), True)
                self.assertIs(metadata.get('user-invocable'), True)

        documents = [ROOT / 'README.md', *skills,
                     *(REPO / '.github' / 'prompts').glob('*.prompt.md'),
                     *(REPO / '.github' / 'agents').glob('*.agent.md')]
        documents += [REPO / name for name in (
            '.github/copilot-instructions.md', 'TO-AGENT.md', 'README.md',
            'COMPANY-HANDOFF.md', 'docs/THIRD-PARTY-NOTICES.md',
            'docs/UX-SIMPLIFICATION.md', 'docs/ARCHITECTURE.md',
            'docs/AGENTIC-AI-VISUAL-BRIEF.md',
            'docs/HERMES-COMPATIBILITY.md', 'doc/hermes/README.md',
            'doc/hermes/UPSTREAM.md', 'doc/hermes/WORK-ITEMS.md')]
        for document in documents:
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', document.read_text('utf-8')):
                with self.subTest(document=document.relative_to(REPO).as_posix(), target=target):
                    url = urlsplit(target)
                    if url.scheme in {'http', 'https', 'mailto'}:
                        continue
                    self.assertFalse(url.scheme or url.netloc, 'Nonportable local link')
                    path = (document.parent / unquote(url.path)).resolve() if url.path else document
                    self.assertTrue(path.is_relative_to(REPO))
                    self.assertTrue(path.is_file(), target)
                    if url.fragment:
                        headings = re.findall(r'^#{1,6}\s+(.+)$', path.read_text('utf-8'), re.M)
                        anchors = {re.sub(r'[^\w\s-]', '', heading).lower().replace(' ', '-')
                                   for heading in headings}
                        self.assertIn(unquote(url.fragment), anchors, target)

        bundle = REPO / 'doc' / 'hermes'
        sources = json.loads((bundle / 'SOURCES.json').read_text('utf-8'))
        self.assertEqual(sources['schema_version'], 1)
        self.assertIs(sources['runtime_imported'], False)
        self.assertEqual(sources['repository'], 'https://github.com/NousResearch/hermes-agent')
        self.assertRegex(sources['commit'], r'^[0-9a-f]{40}$')
        self.assertTrue(sources['files'])
        copied = set()
        for item in sources['files']:
            with self.subTest(reference=item['local_path']):
                path = (bundle / item['local_path']).resolve()
                self.assertTrue(path.is_relative_to(bundle))
                self.assertNotIn(path, copied)
                copied.add(path)
                data = path.read_bytes()
                self.assertEqual(len(data), item['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
                self.assertRegex(item['source_sha256'], r'^[0-9a-f]{64}$')
                self.assertRegex(item['git_blob_sha1'], r'^[0-9a-f]{40}$')
                self.assertEqual(item['source_url'], sources['repository'] + '/blob/' + sources['commit'] + '/' + item['upstream_path'])
                if path.name == 'LICENSE.txt':
                    self.assertEqual(item['source_sha256'], item['sha256'])
                    self.assertEqual(item['source_bytes'], item['bytes'])
                    self.assertIn(b'Copyright (c) 2025 Nous Research', data)
                    continue
                self.assertEqual(path.suffix, '.md')
                for token in MarkdownIt().parse(data.decode('utf-8')):
                    for child in token.children or []:
                        if child.type != 'link_open':
                            continue
                        url = urlsplit(child.attrGet('href'))
                        if url.scheme or url.netloc or not url.path:
                            continue
                        linked = (path.parent / unquote(url.path)).resolve()
                        self.assertTrue(linked.is_relative_to(REPO))
                        self.assertTrue(linked.is_file(), str(linked.relative_to(REPO)))
        expected = {p.resolve() for p in (bundle / 'reference').iterdir() if p.is_file()}
        expected.add((bundle / 'LICENSE.txt').resolve())
        self.assertEqual(copied, expected)
        self.assertTrue(sources['code_references'])
        for item in sources['code_references']:
            self.assertIs(item['included'], False)
            self.assertRegex(item['git_blob_sha1'], r'^[0-9a-f]{40}$')
            self.assertEqual(item['source_url'], sources['repository'] + '/blob/' + sources['commit'] + '/' + item['path'])


if __name__ == '__main__':
    unittest.main()
