#!/usr/bin/env python3
"""사이트 빌드 직전에 실행: 문장 듣기는 문장 끝 🔊, 문장 속 단어는 '마우스 올리면 뜻 · 누르면 발음'.

  python3 scripts/fr_interactive.py content

- 단어 뜻은 content 안의 단어 노트(3 Vocabulaire/3 Mots) 머리말(text · feminine · meaning · forms)에서 읽어요.
- 단어 소리: 그 모양 그대로의 소리 파일(_Audio/allez-xxxxxx.m4a)이 있으면 그것, 없으면 단어 노트의 소리.
  둘 다 없으면 뜻 말풍선 없이 글자만.
- 여러 번 실행해도 결과가 같아요 (이미 바뀐 문장은 건드리지 않음). 표준 라이브러리만 써요.
볼트 쪽 같은 규칙: Francisation_notes/_Tools/gen/tokens.py
"""
import glob, hashlib, json, os, re, sys, unicodedata

ROOT = sys.argv[1] if len(sys.argv) > 1 else 'content'
AUD = os.path.join(ROOT, '_Audio')
HAVE = {os.path.basename(p) for p in glob.glob(os.path.join(AUD, '*.m4a'))}
NAME = re.compile(r'junhyung|준형|\bkye\b', re.I)   # 실명은 건드리지 않기

def slug(t):
    s = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:40] or 'x'
def fname(text):   # 볼트 audio.py 의 이름 규칙과 같음
    return f'{slug(text)}-{hashlib.md5(text.encode()).hexdigest()[:6]}.m4a'
def norm(t):
    return unicodedata.normalize('NFC', t.replace('’', "'")).lower()

# ---------- 단어 노트 읽기 ----------
def frontmatter(t):
    m = re.match(r'^---\n(.*?)\n---\n?', t, re.S)
    return (m.group(1), t[m.end():]) if m else ('', t)
def fval(fm, key):
    m = re.search(rf'^{key}: (.*)$', fm, re.M)
    if not m: return None
    v = m.group(1).strip()
    if v.startswith('['):
        try: return json.loads(v)
        except Exception: return [x.strip().strip('"') for x in v.strip('[]').split(',') if x.strip()]
    return v.strip('"')
WORDS = {}
for p in glob.glob(os.path.join(ROOT, '3 Vocabulaire', '3 Mots', '**', '*.md'), recursive=True):
    fm, body = frontmatter(open(p, encoding='utf-8').read())
    if fval(fm, 'type') != 'word': continue
    sid = fval(fm, 'id')
    if not sid: continue
    a = re.search(r'\]\(_Audio/([^)\s]+\.m4a)\)', body)
    WORDS[sid] = {'pos': fval(fm, 'pos') or '', 'text': fval(fm, 'text') or '', 'fem': fval(fm, 'feminine') or '', 'meaning': fval(fm, 'meaning') or [],
                  'forms': re.findall(r'^\s+- text: "?(.*?)"?$', fm, re.M), 'audio': a.group(1) if a else None}

LEMMA, PHRASE = {}, {}
TOK = re.compile(r"[a-zà-ÿœæç]+(?:-[a-zà-ÿœæç]+)*'?", re.I)
def put(k, sid):
    k = norm(k).strip()
    if k and sid not in LEMMA.setdefault(k, []): LEMMA[k].append(sid)
for sid, w in WORDS.items():
    t = norm(w['text'])
    if len(TOK.findall(t)) > 1 and re.search(r"[ ']", t.strip("'")): PHRASE.setdefault(t, sid)
    else: put(t, sid)
    if w['fem']: put(w['fem'], sid)
    if t.startswith("s'") and ' ' not in t: put(t[2:], sid)   # s'appeler → appeler
IRR = {'etre': "suis es est sommes êtes sont été était étais c'était sera serai", 'avoir': "ai as a avons avez ont eu avais",
       'aller': "vais vas va allons allez vont", 'venir': "viens vient venons venez viennent",
       'pouvoir': "peux peut pouvons pouvez peuvent", 'vouloir': "veux veut voulons voulez veulent voudrais voudriez",
       'faire': "fais fait faisons faites font", 'savoir': "sais sait savons savez savent", 'aimer': "aimerais aimerait"}
for sid, fs in IRR.items():
    if sid in WORDS:
        for f in fs.split(): put(f, sid)
def stem(t):
    t = norm(t); return t[2:] if t.startswith("s'") else t
for sid, w in WORDS.items():   # 활용형: 표제어와 앞 두 글자가 같은 것만 (vous allez → allez = aller)
    for f in w['forms']:
        for tk in TOK.findall(norm(f)):
            if tk.endswith("'") or tk[:2] != stem(w['text'])[:2]: continue
            if tk not in LEMMA or all(norm(WORDS[s]['text']) != tk for s in LEMMA[tk]): put(tk, sid)
ELI = {"j'": 'je', "l'": 'le', "d'": 'de', "c'": 'ce', "n'": 'ne', "qu'": 'que', "m'": 'me', "t'": 'te', "s'": 'se'}
TIP = {'la': '그 (여성 정관사)', "l'": '그 (모음 앞 정관사 le · la)', 'les': '그 (복수 정관사)', 'le': '그 (남성 정관사)'}

def lookup(tok, hints=()):
    t = norm(tok)
    if t in ELI: return (LEMMA.get(ELI[t]) or [None])[0]
    c = LEMMA.get(t, [])
    if not c:
        for a, b in (('lle', 'ler'), ('lles', 'ler'), ('llent', 'ler'), ('tte', 'ter'), ('ez', 'er'), ('ons', 'er'), ('es', 'er'),
                     ('ent', 'er'), ('e', 'er'), ('é', 'er'), ('ée', 'er'), ('és', 'er'), ('s', ''), ('x', ''), ('e', ''), ('es', '')):
            if t.endswith(a) and len(t) > len(a) + 1:
                c = LEMMA.get(t[:-len(a)] + b, [])
                if c: break
    if not c and hints and '-' not in t:
        for h in hints:
            if h in WORDS and len(t) >= 3 and norm(WORDS[h]['text']).split("'")[-1][:3] == t[:3]: return h
    if not c: return None
    for h in hints:
        if h in c: return h
    return c[0]
def tip(sid, tok):
    if norm(tok) in TIP and sid in ('le', 'la', 'les'): return TIP[norm(tok)]
    w = WORDS[sid]; m = ', '.join(w['meaning'])
    same = norm(tok).strip("'") == norm(w['text']) or (w['fem'] and norm(tok) == norm(w['fem']))
    return m if same else f"{w['text']} · {m}"
def sound(seg, sid, spoken=None):
    f = fname(spoken or norm(seg))
    if f in HAVE: return f
    return WORDS[sid]['audio'] if WORDS[sid]['audio'] in HAVE else None

def segments(s, hints=()):
    out = []; i = 0; low = norm(s)
    while i < len(s):
        hit = None
        for ph, sid in PHRASE.items():
            if low.startswith(ph, i) and (i == 0 or not low[i-1].isalpha()) and (i + len(ph) >= len(s) or not low[i+len(ph)].isalpha()):
                if not hit or len(ph) > len(hit[0]): hit = (ph, sid)
        if hit:
            seg = s[i:i+len(hit[0])]; out.append((seg, hit[1], sound(seg, hit[1]))); i += len(seg); continue
        m = re.match(r"(?i)(qu|[jldcnmts])'", s[i:])
        if m and (i == 0 or not s[i-1].isalpha()):
            seg = m.group(0); sid = lookup(seg, hints)
            out.append((seg, sid, sound(seg, sid, WORDS[sid]['text']) if sid else None)); i += len(seg); continue
        m = re.match(r"[A-Za-zÀ-ÿœŒæÆçÇ]+(?:-[A-Za-zÀ-ÿœŒæÆçÇ]+)*", s[i:])
        if m:
            seg = m.group(0); sid = lookup(seg, hints)
            if sid or '-' not in seg: out.append((seg, sid, sound(seg, sid) if sid else None))
            else:
                for k, p in enumerate(seg.split('-')):
                    if k: out.append(('-', None, None))
                    sl = lookup(p, hints); out.append((p, sl, sound(p, sl) if sl else None))
            i += len(seg); continue
        out.append((s[i], None, None)); i += 1
    for k in range(len(out) - 1):   # m'appelle: m' 도 s'appeler
        seg, sid, f = out[k]
        if norm(seg) in ("m'", "t'", "s'") and out[k+1][1] and norm(WORDS[out[k+1][1]]['text']).startswith("s'"):
            out[k] = (seg, out[k+1][1], out[k+1][2])
    return out

def words(text, hints=()):
    """문장 → [단어](_Audio/소리 "뜻") …  (뜻을 모르는 단어는 글자 그대로)"""
    if NAME.search(text): return text
    res = []
    for seg, sid, f in segments(text, hints):
        if sid and f:
            t = tip(sid, seg).replace('"', '”').replace('|', '/').replace(']', ')').replace('[', '(')
            res.append(f'[{seg}](_Audio/{f} "{t}")')
        else: res.append(seg)
    return ''.join(res)

PLAIN = r"[^\[\]\n|*`]+?"
LINK = r"\(_Audio/([^)\s]+\.m4a)\)"
def is_sentence(t):
    return bool(re.search(r'[?.!…]$', t.strip())) or len(t.split()) >= 3

def transform(t):
    fm, body = frontmatter(t)
    hints = fval(fm, 'words') or []
    head = t[:len(t) - len(body)]
    # 1) 문장 노트: "[🔊 듣기](소리) · 👉 뜻" → "**문장** 🔊" + "👉 뜻"
    if fval(fm, 'type') == 'sentence' and fval(fm, 'text'):
        body = re.sub(r'(?m)^\[🔊 듣기\]' + LINK + r' · 👉 (.*)$',
                      lambda m: f"**{words(fval(fm, 'text'), hints)}** [🔊](_Audio/{m.group(1)})\n\n👉 {m.group(2)}", body)
    # 2) 대화: "> **A** : [문장](소리)" → "> **A** : 문장 🔊"
    body = re.sub(r'(?m)^(> (?:\*\*[^*\n]+\*\* : )?)\[(?!🔊|▶)(' + PLAIN + r')\]' + LINK + r'\s*$',
                  lambda m: f'{m.group(1)}{words(m.group(2), hints)} [🔊](_Audio/{m.group(3)})', body)
    # 3) 문장 블록: "> **문장**" 다음 줄 "> [🔊 ipa](소리) 한글" → 소리는 문장 끝으로
    body = re.sub(r'(?m)^(> \*\*)(' + PLAIN + r')(\*\*)\s*\n> \[🔊 ([^\]]+)\]' + LINK + r'(.*)$',
                  lambda m: f'{m.group(1)}{words(m.group(2), hints)}{m.group(3)} [🔊](_Audio/{m.group(5)})\n> [{m.group(4)}]{m.group(6)}', body)
    # 4) 표: "| 문장 | [🔊 ipa](소리) 한글 |" → "| 문장 🔊 | [ipa] 한글 |"
    def row(m):
        if not is_sentence(m.group(2)): return m.group(0)
        return f'{m.group(1)}{words(m.group(2).strip(), hints)} [🔊](_Audio/{m.group(4)}) | [{m.group(3)}]{m.group(5)}'
    body = re.sub(r'(?m)^(\| )(' + PLAIN + r') \| \[🔊 ([^\]]+)\]' + LINK + r'([^|\n]*)', row, body)
    # 5) 상황 표: "| [[문장]] | [🔊](소리) | 뜻 |" → "| [[문장]] 🔊 | 뜻 |"
    if re.search(r'(?m)^\| 문장 \| 🔊 \| 뜻 \|$', body):
        body = re.sub(r'(?m)^\| 문장 \| 🔊 \| 뜻 \|\n\|---\|---\|---\|$', '| 문장 | 뜻 |\n|---|---|', body)
        body = re.sub(r'(?m)^(\| \[\[[^\n]*?\]\]) \| (\[🔊\]' + LINK + r') \|', r'\1 \2 |', body)
    # 6) 이미 "문장 🔊" 모양 (볼트 새 형식): 앞의 문장을 단어로
    body = re.sub(r'(?m)^((?:# )?(?:> )?(?:\*\*[^*\n]+\*\* : )?(?:\| )?)(\*\*)?(' + PLAIN + r')(\*\*)? \[🔊\]' + LINK,
                  lambda m: f"{m.group(1)}{m.group(2) or ''}{words(m.group(3), hints) if re.search('[A-Za-zÀ-ÿ]', m.group(3)) else m.group(3)}{m.group(4) or ''} [🔊](_Audio/{m.group(5)})", body)
    return head + body

if __name__ == '__main__':
    n = 0
    for p in glob.glob(os.path.join(ROOT, '**', '*.md'), recursive=True):
        t = open(p, encoding='utf-8').read(); u = transform(t)
        if u != t: open(p, 'w', encoding='utf-8').write(u); n += 1
    print(f'fr_interactive: {len(WORDS)} words, {n} pages changed')
