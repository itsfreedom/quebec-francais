"""영문판 만들기: 한글판 content(빌드 직전, fr_interactive 끝난 것) → content-en
- 단어 뜻: 단어 노트 머리말 meaning_en 사용 (단어 표 '뜻' 칸, 단어 노트 '뜻', 말풍선)
- 나머지 한글 설명: 번역 캐시 i18n/ko-en.json 에서 찾아 바꿈 (한글 덩어리 → 영어)
  캐시에 없는 덩어리는 한글 그대로 두고 i18n/missing.txt 에 적어요 → 번역해서 캐시에 넣으면 다음 빌드부터 영어
- 소리 파일은 복사 안 함 (영문판도 한글판 /_audio/ 를 씀 · Head.tsx)
사용: python3 scripts/en_site.py content content-en [--missing]"""
import os, re, sys, json, glob, shutil

SRC, DST = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '..', 'i18n', 'ko-en.json')
TR = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
HANG = re.compile(r'[가-힣]')
SPAN = re.compile(r'(?:\d+ ?)?[가-힣~][^|\n\[\]*`"<>\x00]*[가-힣)]|[가-힣]')
missing = {}

def tr(s):
    k = s.strip()
    if k in TR: return s.replace(k, TR[k])
    missing[k] = missing.get(k, 0) + 1
    return s

def frontmatter(t):
    m = re.match(r'^---\n(.*?)\n---\n?', t, re.S)
    return (m.group(1), t[m.end():]) if m else ('', t)
def fval(fm, key):
    m = re.search(rf'^{key}: (.*)$', fm, re.M)
    return m.group(1).strip().strip('"') if m else ''

# 단어 노트: 경로(확장자 없이) → 영어 뜻
WORD = {}
for p in glob.glob(os.path.join(SRC, '3 Vocabulaire', '3 Mots', '**', '*.md'), recursive=True):
    fm, _ = frontmatter(open(p, encoding='utf-8').read())
    if fval(fm, 'type') != 'word': continue
    rel = os.path.relpath(p, SRC)[:-3].replace(os.sep, '/')
    WORD[rel] = WORD[os.path.basename(rel)] = {'en': fval(fm, 'meaning_en'), 'text': fval(fm, 'text'), 'display': fval(fm, 'display')}

def target(cell):
    m = re.search(r'\[\[([^\]|\\#]+)', cell) or re.search(r'\(<([^>#]+)\.md', cell)
    return WORD.get(m.group(1).strip()) if m else None

def tables(body):
    """단어 표: 첫 칸이 단어 노트 링크면 마지막 칸(뜻)을 meaning_en 으로"""
    out = []
    for line in body.split('\n'):
        m = re.match(r'^((?:> ?)*)\|(.*)\|[ \t]*$', line)
        if m:
            cells = re.split(r'(?<!\\)\|', m.group(2))
            w = target(cells[0]) if len(cells) >= 3 else None
            if w and w['en'] and HANG.search(cells[-1]):
                cells[-1] = f" {w['en']} "
                line = f"{m.group(1)}|{'|'.join(cells)}|"
        m = re.match(r'^(\s*- \[\[[^\]]+\]\][^—\n]*— )(.*)$', line)   # 사전 목록: - [[단어|…]] — 뜻
        if m and HANG.search(m.group(2)):
            w = target(m.group(1))
            if w and w['en']: line = m.group(1) + w['en']
        out.append(line)
    return '\n'.join(out)

def tips(body):
    """말풍선: [seg](<path.md#snd-x> "뜻") → 영어 뜻"""
    def f(m):
        w = WORD.get(m.group(2)) or WORD.get(os.path.basename(m.group(2)))
        if not w or not w['en']: return m.group(0)
        same = m.group(1).lower().strip("'") in (w['text'].lower(), (w['display'] or '').lower())
        t = w['en'] if same else f"{w['display'] or w['text']} · {w['en']}"
        return f'[{m.group(1)}](<{m.group(2)}.md#{m.group(3)}> "{t}")'
    return re.sub(r'\[([^\[\]\n]+)\]\(<([^>#]+)\.md#(snd-[^>]+)> "[^"]*"\)', f, body)

def wordnote(fm, body):
    en = fval(fm, 'meaning_en')
    if en:
        body = re.sub(r'(?m)^## 뜻\n(?:\d+\..*\n?)+', f'## Meaning\n{en}\n', body)
        body = re.sub(r'(?m)^\*\*English\*\* · [^\n]*?(?: · (≈ \*[^*]+\*))?(?: \(비슷한 영어 단어\))?[ \t]*$',
                      lambda m: f'Similar English word: {m.group(1)}' if m.group(1) else '', body)
    return body

def convert(t):
    fm, body = frontmatter(t)
    if fval(fm, 'type') == 'word': body = wordnote(fm, body)
    body = tables(tips(body))
    keep = []   # 링크 주소 · 링크 대상은 번역 안 함
    def hide(m): keep.append(m.group(0)); return f'\x00{len(keep)-1}\x00'
    body = re.sub(r'(?<!\])\]\([^)\n]*\)|\[\[[^\]|#\n]*(?=\\?\||\]\]|#)|<[^>\n]*>|`[^`\n]*`', hide, body)
    def sub(m):   # 한국어는 조사를 붙여 쓰니, 영어로 바꾸면 앞뒤 띄어쓰기를 넣어요
        t = tr(m.group(0)); a, b = m.start(), m.end()
        if not t: return t
        def word_before(k):   # k 바로 앞이 단어 끝인지 (닫는 ** · 링크 포함)
            if k <= 0: return False
            c = body[k-1]
            if c == '*':
                r = k - 1
                while r > 0 and body[r-1] == '*': r -= 1
                return r > 0 and not body[r-1].isspace()
            if c == '\x00':
                return True   # 링크 바로 뒤
            return bool(re.match(r"[\w)\]’']", c))
        def word_after(k):
            if k >= len(body): return False
            c = body[k]
            if c == '*':
                r = k
                while r < len(body) and body[r] == '*': r += 1
                return r < len(body) and not body[r].isspace() and body[r] not in '.,:;!?)'
            if c == '\x00':
                q = body.index('\x00', k+1); return not keep[int(body[k+1:q])].startswith('](')
            return bool(re.match(r'[\w(\[]', c))
        if re.match(r'[\w("“]', t[0]) and word_before(a): t = ' ' + t
        if re.match(r'[\w).”]', t[-1]) and word_after(b): t = t + ' '
        return t
    body = SPAN.sub(sub, body)
    body = re.sub(r'\x00(\d+)\x00', lambda m: keep[int(m.group(1))], body)
    fm2 = re.sub(r'(?m)^(title|description): "?(.*?)"?$', lambda m: f'{m.group(1)}: "{SPAN.sub(lambda x: tr(x.group(0)), m.group(2))}"' if HANG.search(m.group(2)) else m.group(0), fm)
    return (f'---\n{fm2}\n---\n' if fm else '') + body

if __name__ == '__main__':
    shutil.rmtree(DST, ignore_errors=True)
    for p in glob.glob(os.path.join(SRC, '**', '*'), recursive=True):
        rel = os.path.relpath(p, SRC)
        if rel.split(os.sep)[0] == '_Audio' or os.path.isdir(p): continue
        out = os.path.join(DST, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
        if p.endswith('.md'): open(out, 'w', encoding='utf-8').write(convert(open(p, encoding='utf-8').read()))
        else: shutil.copy(p, out)
    left = sum(missing.values())
    print(f'en_site: {len(TR)} cached, {len(missing)} missing spans ({left} uses)')
    if '--missing' in sys.argv:
        open(os.path.join(HERE, '..', 'i18n', 'missing.json'), 'w', encoding='utf-8').write(
            json.dumps(dict(sorted(missing.items(), key=lambda x: -x[1])), ensure_ascii=False, indent=0))
