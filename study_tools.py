"""Bounded study artifacts. Never execute model-generated code."""
import json
import re

COMMANDS = ('mermaid', 'flashcards', 'eli5')

def command_for(text):
    text=text.strip()
    match=re.match(r'^/(mermaid|flashcards|eli5)\b',text,re.I)
    if match:return match.group(1).lower()
    if re.search(r'\b(flowchart|flow chart|concept map)\b',text,re.I):return 'mermaid'
    if re.search(r'\b(make|create|generate)\b.*\bflash ?cards?\b',text,re.I):return 'flashcards'
    if re.search(r'explain.*like.*(?:five|5)|\beli5\b',text,re.I):return 'eli5'
    return None

def instruction(command):
    common = '\nUse only provided material. A screenshot is one visible page, not an entire chapter. Ask for missing pages or unclear symbols. '
    formats = {
        'mermaid': 'Return a short explanation and exactly one ```mermaid block with a flowchart (flowchart TD or LR). Use quoted node labels. No HTML, links, click handlers, directives or frontmatter. Keep under 60 nodes.',
        'flashcards': 'Return a short scope note and one ```flashcards block containing JSON {"title":"...","cards":[{"front":"question","back":"answer"}]}. Generate 3 to 30 concise cards. Math may use LaTeX.',
        'eli5': 'Explain this concept simply and in detail, as for an intelligent beginner. Use everyday examples and an analogy, build understanding step by step, explain every technical word, and end with a small worked example. Do not talk down to the user or sacrifice correctness.'}
    return common+formats[command]

def validate(kind, raw):
    if len(raw) > 60000:
        raise ValueError('This artifact is too large. Ask for a smaller diagram or deck.')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Expected an artifact object.')
    title = str(data.get('title', 'Sleepy study'))[:120]
    if kind == 'flashcards':
        cards = data.get('cards')
        if not isinstance(cards,list) or not 1 <= len(cards) <= 50:
            raise ValueError('Expected 1–50 flashcards.')
        for card in cards:
            if not isinstance(card,dict) or any(not isinstance(card.get(k),str) or not card[k].strip() or len(card[k])>3000 for k in ('front','back')):
                raise ValueError('Each card needs a question and answer.')
        return {'title':title,'cards':[{'front':c['front'],'back':c['back']} for c in cards]}
    raise ValueError('This study tool is no longer available.')
