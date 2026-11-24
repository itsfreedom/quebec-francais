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

# ---------- 한글 발음 빼기 ----------
PV=re.compile(r'[aeiouyøœɛɔɑəɥ]')
HANG=re.compile(r'[가-힣]')
PIPA=r'(?:\[🔊 [^\]]+\]\(_Audio/[^)\s]+\)|\[\[_Audio/[^\]|]+\\?\|🔊 [^\]]+\]\]|`?\[(?![^\]]*[가-힣])[^\]\n]+\]`?(?![(\[]))'
PPRON=r'[가-힣][가-힣 ·,.?!…~\-]*?'
PEND=r'(?=[ \t]*(?:\||≠|$|\)|\(|→|\.\s|\.$|,|;))'
def _ok(ipa,pron):
    v=len(PV.findall(ipa)); h=len(HANG.findall(pron))
    return v>0 and h<=v*2+1
def strip_hangul(t):
    t=re.sub(r'('+PIPA+r')[ \t]+('+PPRON+r')'+PEND,lambda m:m.group(1) if _ok(m.group(1),m.group(2)) else m.group(0),t,flags=re.M)
    # 대화 발음 줄: "> **A** : 봉주흐!  `[bɔ̃ʒuʁ]`" → "> **A** : `[bɔ̃ʒuʁ]`"
    t=re.sub(r'(?m)^(>\s*(?:\*\*[^*\n]+\*\* : )?)([가-힣][^`\n]*?)\s+(`\[[^\]]+\]`)\s*$',lambda m:m.group(1)+m.group(3) if _ok(m.group(3),m.group(2)) else m.group(0),t)
    return t

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
    WORDS[sid] = {'path': os.path.relpath(p, ROOT).replace(os.sep, '/'), 'pos': fval(fm, 'pos') or '', 'text': fval(fm, 'text') or '', 'fem': fval(fm, 'feminine') or '', 'meaning': fval(fm, 'meaning') or [],
                  'display': fval(fm, 'display') or '', 'display_ipa': fval(fm, 'display_ipa') or '', 'forms': re.findall(r'^\s+- text: "?(.*?)"?$', fm, re.M), 'audio': a.group(1) if a else None}

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

POSKO = [('noun', '명사'), ('pronoun', '대명사'), ('verb', '동사'), ('adjective', '형용사'), ('adverb', '부사'), ('number', '수'),
         ('preposition', '전치사'), ('conjunction', '접속사'), ('article', '관사 · 한정사'), ('determiner', '관사 · 한정사'), ('interjection', '감탄사')]
def pos_group(m):
    q, rows = m.group(1), [r for r in m.group(2).split('\n') if r.strip()]
    if any(re.match(r'(?:> )?\| \*\*[^*]+\*\* \| \|', r) for r in rows): return m.group(0)   # 이미 묶음
    BYPATH = {w['path']: k for k, w in WORDS.items()}
    def pos(r):
        c = r.split('|')[1] if r.count('|') > 2 else r
        pm = re.search(r'<([^>#]+\.md)', c); sid = BYPATH.get(pm.group(1)) if pm else None
        if not sid:
            wm = re.search(r'\[\[([^\]|\\]+)', c); sid = (PHRASE.get(norm(wm.group(1))) or lookup(wm.group(1))) if wm else None
        p = WORDS[sid]['pos'] if sid else ''
        return next((ko for en, ko in POSKO if en == p), '표현 · 기타')
    order = []; groups = {}
    for r in rows:
        k = pos(r); groups.setdefault(k, []).append(r)
    keys = [ko for _, ko in POSKO if ko in groups]; keys = list(dict.fromkeys(keys)) + (['표현 · 기타'] if '표현 · 기타' in groups else [])
    if len(keys) < 2: return m.group(0)
    out = [f'{q}| 단어 | 발음 | 뜻 |', f'{q}|---|---|---|']
    for k in keys: out += [f'{q}| **{k}** | | |'] + groups[k]
    return '\n'.join(out) + '\n'
def wlink(seg, sid, f, t):
    """단어 링크: 마우스 올리면 단어 노트 팝업, 누르면 그 모양 그대로의 소리 (#snd-파일)"""
    return f'[{seg}](<{WORDS[sid]["path"]}#snd-{f[:-4]}> "{t}")'
def words(text, hints=()):
    """문장 → [단어](<단어 노트#snd-소리> "뜻") …  (뜻을 모르는 단어는 글자 그대로)"""
    if NAME.search(text): return text
    res = []
    for seg, sid, f in segments(text, hints):
        if sid and f:
            t = tip(sid, seg).replace('"', '”').replace('|', '/').replace(']', ')').replace('[', '(')
            res.append(wlink(seg, sid, f, t))
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
    # 0) 대화문 정리: 대화와 번역 떼기 · 대화 발음 칸 빼기 · 단어 표는 단어 | 🔊 발음 | 뜻
    body = re.sub(r'(?m)^(>.*)\n(?=> 📖 \*\*번역\*\*)', r'\1\n\n', body)
    body = re.sub(r'(?m)^> (?:💡 \*\*발음\*\*|\[!tip\][-+]? 발음(?: 기호)?)[ \t]*\n(?=> \*\*[^*\n]+\*\* : )(?:>.*(?:\n|$))*\n?', '', body)
    body = re.sub(r'(?m)^(>[^\n]*)\n\n(?=\| 단어 \| 발음 \| 뜻 \|)', r'\1\n\n**📝 단어**\n\n', body)
    # 대화 노트: 제목 단어(Au centre sportif → centre, sportif)도 단어 표에
    if fval(fm, 'type') == 'dialogue':
        tbl = re.search(r'(?m)^> \[!note\][-+]? 단어\n> \| 단어 \| 발음 \| 뜻 \|\n> \|---\|---\|---\|\n((?:> \|.*\n?)*)', body)
        if tbl:
            have = set(re.findall(r'\[\[([^\]|\\]+)', tbl.group(1))) | set(re.findall(r'/([^/>#]+)\.md', tbl.group(1)))
            add = []
            ttl = fval(fm, 'title') or ''
            cands = [ttl] + [t for t in re.findall(r"[A-Za-zÀ-ÿ'-]+", ttl) if norm(t) not in ('au', 'aux', 'le', 'la', 'les', 'se', "l'", 'un', 'une', 'du', 'des', 'de')]
            for c in cands:
                sid = PHRASE.get(norm(c)) or (lookup(c) if ' ' not in c else None)
                if not sid or os.path.basename(WORDS[sid]['path'])[:-3] in have: continue
                w = WORDS[sid]; have.add(os.path.basename(w['path'])[:-3])
                mean = ', '.join(w['meaning'][:2]) if isinstance(w['meaning'], list) else w['meaning']
                ipa = re.search(r'(?m)^ipa:\s*"?([^"\n]*)', open(os.path.join(ROOT, w['path']), encoding='utf-8').read())
                dip = w['display_ipa'] or (ipa.group(1) if ipa else '')
                snd = f"[🔊 {dip}](_Audio/{w['audio']})" if w['audio'] in HAVE else f"[{dip}]"
                base = os.path.basename(w['path'])[:-3]; disp = w['display'] or base
                m2 = re.match(r'(.*?)( \([mf]\.\))?$', disp)   # 성 표시는 링크 밖
                link = f"[[{base}]]" if m2.group(1) == base else f"[[{base}\\|{m2.group(1)}]]"
                add.append(f"> | {link}{m2.group(2) or ''} | {snd} | {mean} |")
            if add:
                e = tbl.end(1); body = body[:e] + ('' if body[e-1:e] == '\n' or e == tbl.start(1) else '\n') + '\n'.join(add) + '\n' + body[e:]
    def row(m):
        pre, w, ipa, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        a = re.search(r'\s*\[🔊\]\(_Audio/([^)\s]+)\)\s*$', w)
        name = re.sub(r'\[\[(?:[^\]|]*\\?\|)?([^\]]+)\]\]', r'\1', re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', w)).split(' (')[0].replace('🔊', '').strip()
        tm = re.search(r'\[\[([^\]|\\]+)', w) or re.search(r'<[^>]*/([^/>#]+)\.md', w)
        sid = (lookup(tm.group(1)) if tm else None) or PHRASE.get(norm(name)) or (lookup(name.split()[-1]) if name else None)
        if a: w, f = w[:a.start()], a.group(1)
        else: f = WORDS[sid]['audio'] if sid and WORDS[sid]['audio'] in HAVE else None
        if not f: return m.group(0)
        if sid and '[' not in w: w = f'[{w.strip()}](<{WORDS[sid]["path"]}>)'   # 단어 칸: 마우스 올리면 단어 팝업
        return f'{pre}{w.strip()} | [🔊 {ipa}](_Audio/{f}){rest}'

    def plain(m):
        name = m.group(2).split(' (')[0].strip(); sid = PHRASE.get(norm(name)) or (lookup(name.split()[-1]) if name else None)
        if not sid or norm(WORDS[sid]['text']).split()[-1] != norm(name).split()[-1]: return m.group(0)
        return f'{m.group(1)}[{m.group(2)}](<{WORDS[sid]["path"]}>) | [🔊 '
    def wtable(m):
        t = re.sub(r'(?m)^((?:> )?\| )(.+?) \| `?\[(?!🔊)([^\]\n]+)\]`?((?: [^|\n]*)? \|[^\n]*)$', row, m.group(0))
        return re.sub(r'(?m)^((?:> )?\| )([^|\[\]\n*]+?) \| \[🔊 ', plain, t)   # 단어 칸 → 단어 팝업
    WT = r'(?m)^(?:> )?\| 단어 \| 발음 \| 뜻 \|\n(?:(?:> )?\|.*\|[ \t]*(?:\n|$))+'
    body = re.sub(WT, wtable, body)
    body = re.sub(r'(?m)^ · (대화문 노트: )(\d+ [^\n\]]+?)[ \t]*$', lambda m: f"{m.group(1)}[[{m.group(2)}|{re.sub(r'^\d+ ', '', m.group(2))}]]", body)
    body = re.sub(r'( · 대화문 노트: )(\d+ [^\n\]]+?)[ \t]*$', lambda m: f"{m.group(1)}[[{m.group(2)}|{re.sub(r'^\d+ ', '', m.group(2))}]]", body, flags=re.M)
    body = body.replace('발음은 IPA와 한글 발음을 같이 적었어요. 한글 발음은 대략적인 참고용이에요.', '단어와 문장은 누르면 소리가 나요.')
    body = re.sub(r'\[▶ 이어서 듣기[^\]]*\]\(([^)]+)\)(?: · 문장을 누르면 그 문장만 들려요)?', r'[▶ 따라 해 보기](\1)', body)
    # 홈의 책 순서: 발음 → 대화 → 단어 → 문법
    if '## 📚 책' in body:
        def books(m):
            items = re.findall(r'(?m)^\d+\. (.*)$', m.group(1)); rank = ['4 Phonétique', '2 Dialogues', '3 Vocabulaire', '1 Grammaire']
            items.sort(key=lambda x: next((i for i, r in enumerate(rank) if r in x), 9))
            return '## 📚 책\n' + ''.join(f'{i}. {x}\n' for i, x in enumerate(items, 1))
        body = re.sub(r'## 📚 책\n((?:\d+\. .*\n?)+)', books, body)
    # 문장·대화의 발음 기호는 빼기 (소리가 있으니) · 단어 표의 발음 기호는 그대로
    body = re.sub(r'(?m)^(> \[!abstract\][-+]? 번역) · 발음 기호', r'\1', body)
    body = re.sub(r'(?m)^(> .*?→.*?)\s*·\s*`\[[^`\n]+\]`[ \t]*$', r'\1', body)
    body = re.sub(r'(?m)^> `\[[^`\n]+\]`[ \t]*\n', '', body)   # 상자 속 발음 기호만 있는 줄
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
    # 7) 예전 모양 [단어](_Audio/소리 "뜻") → 단어 노트 링크 (마우스 올리면 단어 팝업)
    def old(m):
        sid = PHRASE.get(norm(m.group(1))) or lookup(m.group(1), hints)
        if sid and norm(m.group(1)) in ("m'", "t'", "s'") and norm(WORDS[sid]['text']).startswith("s'"): return m.group(0)   # 7-1에서 동사와 합침
        return wlink(m.group(1), sid, m.group(2), m.group(3)) if sid else m.group(0)
    body = re.sub(r'\[([^\[\]\n]+)\]\(_Audio/([^)\s]+\.m4a) "([^"]*)"\)', old, body)
    # 7-1) m' t' s' + 동사 → 한 단어로 (t'appelles 를 누르면 "t'appelles" 소리)
    def eli(m):
        text = m.group(1) + m.group(2)
        f = next((c for c in (fname(text), fname(norm(text))) if c in HAVE), m.group(4) + '.m4a')
        return f'[{text}](<{m.group(3)}#snd-{f[:-4]}> "{m.group(5)}")'
    body = re.sub(r"\[([MmTtSs]')\]\((?:_Audio/[^)\s]+|<[^>]+>)(?: \"[^\"]*\")?\)\[([^\[\]\n]+)\]\(<([^>#]+\.md)#snd-([^>]+)> \"([^\"]*)\"\)", eli, body)
    # 7-2) 나중에 그 모양 그대로의 소리(allez …)가 생기면 그 소리로
    def up(m):
        cands = [c for c in (fname(m.group(1)), fname(norm(m.group(1)))) if c in HAVE]
        if not cands or m.group(3) + '.m4a' in cands: return m.group(0)
        return f'[{m.group(1)}](<{m.group(2)}#snd-{cands[0][:-4]}> "{m.group(4)}")'
    body = re.sub(r'\[([^\[\]\n]+)\]\(<([^>#]+\.md)#snd-([^>]+)> "([^"]*)"\)', up, body)
    # 9) 수업·대화의 단어 표를 품사별로 묶기 (명사 → 대명사 → 동사 …)
    if fval(fm, 'type') == 'dialogue':   # 대화 노트만 (수업 페이지는 볼트에서 주제·품사별로 묶여 옴)
        body = re.sub(r'(?m)^((?:> )?)\| 단어 \| 발음 \| 뜻 \|\n(?:> )?\|---\|---\|---\|\n((?:(?:> )?\|.*\|[ \t]*(?:\n|$))+)', pos_group, body)
    # 8) 한글 발음 표기 빼기 (소리로 들으니까 · 발음기호는 그대로)
    body = strip_hangul(body)
    return head + body

if __name__ == '__main__':
    n = 0
    for p in glob.glob(os.path.join(ROOT, '**', '*.md'), recursive=True):
        t = open(p, encoding='utf-8').read(); u = transform(t)
        if u != t: open(p, 'w', encoding='utf-8').write(u); n += 1
    print(f'fr_interactive: {len(WORDS)} words, {n} pages changed')
