"""사이트 날짜 페이지 = 볼트 수업 노트 모양 그대로 (2026-11-24)
- 순서: 자료(프린트) 순서. 두 선생님 칸을 이어지는 주제끼리 붙임 (AFTER)
- 필기 내용은 맨 끝 ➕ Un peu plus 하나로, 새 단어는 주제 → 품사별 접힌 상자 하나로 합침
- 공개 안 하는 것: 정답 링크, NOREVIEW 날의 복습 듣기, 이전/다음 줄"""
import re, os, glob
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import VAULT as V
C = f'{V}/5 Cours/2026-11'
TITLE = {}   # 비어 있으면 'N일차'
# 칸 제목(앞부분) → 자료에서 잘라 온 그림 (_Tools/site/img → 사이트 수업/자료)
IMAGES = {('20261118', 'Les voyelles orales'): 'voyelles-orales.png',
          ('20261118', 'Les voyelles nasales'): 'voyelles-nasales.png',
          ('20261118', 'Les semi-consonnes'): 'semi-consonnes.png'}
# 이링 수업 칸을 이사벨 수업의 어느 칸 뒤에 붙일지 (없으면 이사벨 칸 다음에 전부)
AFTER = {'20261118': "Les lettres de l'alphabet", '20261120': 'Les nombres'}
NOREVIEW = {'20261120'}   # 생년월일 문장이 들어 있어 사용자 확인 전까지 안 올림
GROUPS = ['👋 인사', '📅 요일', '🗓 달', '🔢 숫자', '🌍 나라 · 언어', '명사', '동사', '형용사', '그 밖']

def split(path):
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'^---\n.*?\n---\n', '', t, flags=re.S)
    parts = re.split(r'(?m)^(?=## )', t)
    pre, secs = parts[0], []
    for p in parts[1:]:
        h, _, body = p.partition('\n')
        secs.append((h[3:].strip(), body))
    return pre, secs

def clean(t):
    t = re.sub(r'(?m)^.*\[\[[^\]]*_정답[^\]]*\]\].*\n?', '', t)          # 정답 링크 줄
    t = re.sub(r'(?m)^.*\[\[[^\]]*_복습\.m4a.*\n?', '', t)                          # 복습 듣기 (summary()에서 따로 넣음)
    t = re.sub(r'(?m)^(?:← )?\[\[\d{8}_[A-Za-z]+\|[^\]]*\]\](?: · \[\[\d{8}_[A-Za-z]+\|[^\]]*\]\])*(?: →)?\s*$\n?', '', t)  # 이전/다음
    t = re.sub(r'(?m)^←.*→\s*$\n?', '', t)
    return t

EXITEM = r'(\[\[[^\]|]+(?:\|[^\]]*)?\]\]) \[\[_Audio/([^|\]]+)\|🔊 ?([^\]]*)\]\]'
def ex_tables(t):
    """예시 줄 'six 🔊 · salut 🔊 …' → 단어 | 발음 표 (한 줄에 몰려 있으면 단어와 발음 기호가 구분이 안 돼요)"""
    def block(m):
        rows = []
        for line in m.group(0).strip('\n').split('\n'):
            for w, f, ipa in re.findall(EXITEM, line):
                rows.append(f'| {w} | [[_Audio/{f}\\|🔊 {ipa}]] |' if ipa else f'| {w} | [[_Audio/{f}\\|🔊]] |')
        return '| 단어 | 발음 |\n|---|---|\n' + '\n'.join(rows) + '\n'
    return re.sub(r'(?m)(^(?:- )?' + EXITEM + r'(?: · ' + EXITEM + r')*[ \t]*$\n?)+', '', t)   # 예시 줄은 빼기 (아래 📖 노트 표에 같은 예시가 있음)
    return re.sub(r'(?m)(^(?:- )?' + EXITEM + r'(?: · ' + EXITEM + r')*[ \t]*$\n?)+', block, t)

def dedupe_embeds(t):
    """같은 노트 끼워 넣기 상자가 두 번 나오면 두 번째부터 빼기"""
    seen = set()
    def one(m):
        n = m.group(2)
        if n in seen: return ''
        seen.add(n); return m.group(0)
    return re.sub(r'(?m)^(> \[!info\][-+]? [^\n]*\n)> !\[\[([^\]|#]+)\]\][ \t]*\n?\n?', one, t)

def nobox(b):
    """칸마다 있는 '📚 단어 (N)' 상자 빼기 (맨 끝 '오늘 새 단어'에 다 있음)"""
    return re.sub(r'(?m)^> \[!example\][-+]? 📚 단어 \(\d+\)\n(?:>.*\n?)*\n?', '', b)

def merge_words(bodies):
    """여러 '📚 오늘 새 단어' 칸 → 묶음(주제·품사)별 접힌 상자 하나씩"""
    rows, seen = {}, set()
    for b in bodies:
        for m in re.finditer(r'(?m)^> \[!example\][-+]? (.+?)(?: \(\d+\))?\n((?:>.*\n?)*)', b):
            g = m.group(1).strip()
            key = next((k for k in GROUPS if g.startswith(k)), g)
            for l in m.group(2).split('\n'):
                if not l.startswith('> | ') or l.startswith('> | 단어') or l.startswith('> |---'): continue
                k = re.sub(r'\W', '', (re.search(r'\[\[([^\]|\\]+)', l) or re.search(r'\| (.+?) \|', l)).group(1).lower())
                if k in seen: continue
                seen.add(k); rows.setdefault(key, []).append(l)
    out = [f'## 📚 오늘 새 단어 ({len(seen)})', '']
    for g in GROUPS + [k for k in rows if k not in GROUPS]:
        if g not in rows: continue
        name = '그 밖 (부사 · 대명사 · 전치사 …)' if g == '그 밖' else g
        out += [f'> [!example]- {name} ({len(rows[g])})', '> | 단어 | 발음 | 뜻 |', '> |---|---|---|'] + rows[g] + ['']
    return '\n'.join(out)

def summary(pres):
    lines, seen = [], set()
    for p in pres:
        m = re.search(r'(?m)^> \[!summary\][^\n]*\n((?:>.*\n?)*)', p)
        if not m: continue
        for l in m.group(1).split('\n'):
            l = l.strip()
            if '_복습.m4a' in l:                                      # 복습 오디오: 사이트 소리 링크로
                m2 = re.search(r'\[\[(\d{8})_복습\.m4a[^\]]*\]\](.*)', l)
                if m2 and m2.group(1) not in NOREVIEW and glob.glob(f'{V}/5 Cours/*/{m2.group(1)}/{m2.group(1)}_복습.m4a'):   # 파일이 있을 때만
                    l = f'> 🎧 [복습 듣기](_Audio/{m2.group(1)}_복습.m4a){m2.group(2)}'
                else: continue
            if not l or l in seen: continue
            seen.add(l); lines.append(l)
    return '> [!summary] 오늘 한눈에\n' + '\n'.join(lines) + '\n' if lines else ''

def materials(pres):
    items = []
    for p in pres:
        for m in re.finditer(r'(?m)^📎 \*\*수업 자료\*\*: (.+)$', p): items += [x.strip() for x in m.group(1).split(' · ')]
    return '📎 **수업 자료**: ' + ' · '.join(items) + '\n' if items else ''

def build(day):
    files = sorted(glob.glob(f'{C}/{day}/{day}_*.md'))
    I = next((f for f in files if f.endswith('_Isabelle.md')), None)
    Y = next((f for f in files if f.endswith('_YiLing.md')), None)
    notes = [split(f) for f in (I, Y) if f]
    pres = [n[0] for n in notes]
    def kind(h):
        return 'more' if h.startswith('➕') else 'words' if h.startswith('📚 오늘 새 단어') else 'print'
    ip = [s for s in notes[0][1] if kind(s[0]) == 'print']
    yp = [s for s in notes[1][1] if kind(s[0]) == 'print'] if len(notes) > 1 else []
    order = ip + yp
    if day in AFTER and yp:
        i = next((n for n, s in enumerate(ip) if AFTER[day] in s[0]), None)
        if i is not None: order = ip[:i + 1] + yp + ip[i + 1:]
    more = [ex_tables(nobox(s[1])).strip('\n') for n in notes for s in n[1] if kind(s[0]) == 'more']
    words = [s[1] for n in notes for s in n[1] if kind(s[0]) == 'words']
    out = [summary(pres), materials(pres)]
    for h, b in order:
        b = nobox(b)
        img = next((f for (d, k), f in IMAGES.items() if d == day and k in h), None)
        if img: b = f'\n![[{img}]]\n' + b
        out.append(f'## {h}\n{ex_tables(b).rstrip()}\n')
    if more: out.append('## ➕ Un peu plus · 조금 더 (필기)\n\n' + '\n\n'.join(more) + '\n')
    if words: out.append(merge_words(words))
    n = days().index(day) + 1
    return TITLE.get(day, f'{n}일차'), dedupe_embeds(clean('\n'.join(x for x in out if x)))

def days():
    return sorted(os.path.basename(d) for d in glob.glob(f'{C}/2026*') if os.path.isdir(d))
