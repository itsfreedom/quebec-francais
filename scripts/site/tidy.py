"""사이트용 정리: 번호 없는 제목, 색인 노트(00 …)를 폴더 첫 화면(index.md)으로, 링크 갱신"""
import os,re,glob,sys
Q=sys.argv[1] if len(sys.argv)>1 else __import__('paths').OUT
NUM=re.compile(r'^\d+\s+')
def strip(n): return NUM.sub('',n)
FM=re.compile(r'^---\n(.*?)\n---\n',re.S)
def set_title(t,title):
    m=FM.match(t)
    q=title.replace('"','\\"')
    if m:
        fm=m.group(1)
        if re.search(r'(?m)^title:',fm):
            fm=re.sub(r'(?m)^title:\s*(.*)$',lambda x:'title: "'+strip(x.group(1).strip().strip('"\''))+'"',fm)
        else: fm=f'title: "{q}"\n'+fm
        fm=re.sub(r'(?m)^(date|created|first|lessons):.*\n?','',fm)
        return f'---\n{fm}\n---\n'+t[m.end():]
    return f'---\ntitle: "{q}"\n---\n\n'+t
# 1) 색인 노트 → 폴더 index.md
IDX={}
for d,dirs,files in os.walk(Q):
    if '/_Audio' in d+'/' or d==Q: continue
    rel=os.path.relpath(d,Q)
    zero=[f for f in files if f.startswith('00 ') and f.endswith('.md')] or [f for f in files if f==os.path.basename(d)+'.md']
    if zero:
        f=zero[0]; IDX[f[:-3]]=rel
        os.rename(f'{d}/{f}',f'{d}/index.md')
        t=open(f'{d}/index.md').read()
        open(f'{d}/index.md','w').write(set_title(t,strip(f[:-3])))
    elif 'index.md' not in files and glob.glob(f'{glob.escape(d)}/**/*.md',recursive=True):   # 노트가 없는 폴더(소리·자료)는 건너뜀
        open(f'{d}/index.md','w').write(f'---\ntitle: "{strip(os.path.basename(d))}"\n---\n')
# 2) 모든 노트 제목·링크
LINK=re.compile(r'(!?)\[\[([^\]|#\\]+)(#[^\]|\\]*)?((?:\\?\|)[^\]]*)?\]\]')
def fix(m):
    bang,tgt,head,alias=m.group(1),m.group(2),m.group(3) or '',m.group(4) or ''
    sep='\\|' if alias.startswith('\\|') else '|'
    name=tgt.strip()
    if name in IDX:
        new=IDX[name]+'/index'
        if bang: return f'![[{new}{head}{alias}]]'
        return f'[[{new}{head}{alias or sep+strip(name)}]]' if alias else f'[[{new}{head}|{strip(name)}]]'
    if not bang and not alias and NUM.match(os.path.basename(name)):
        return f'[[{tgt}{head}|{strip(os.path.basename(name))}]]'
    return m.group(0)
for p in glob.glob(f'{Q}/**/*.md',recursive=True):
    t=open(p).read()
    base=os.path.basename(p)[:-3]
    if base!='index' or os.path.dirname(p)==Q:
        t=set_title(t,strip(base)) if not FM.match(t) or not re.search(r'(?m)^title:',FM.match(t).group(1)) else set_title(t,'')
    t=LINK.sub(fix,t)
    open(p,'w').write(t)
print('index notes',len(IDX))
# 3) 사이트에 필요 없는 안내 상자·날짜 빼기
DROPCALL=re.compile(r'^> \[!(info|example)\] |^> \[!tip\] 양방향 카드')   # 접지 않는 안내 상자만 (접는 상자 ]- 는 내용)
def clean(t):
    out=[]; skip=False
    for l in t.split('\n'):
        if skip:
            if l.startswith('>'): continue
            skip=False
        if DROPCALL.match(l): skip=True; continue
        if l.startswith('📅'): continue  # 날짜
        l=re.sub(r'\s*·?\s*(처음 나온 수업|수업):(\s*\[\[\d{4}-\d{2}-\d{2}[^\]]*\]\])+','',l)
        l=re.sub(r'\s*\(\[\[\d{4}-\d{2}-\d{2}[^\]]*\]\]\)','',l)
        out.append(l)
    t='\n'.join(out)
    # 표에서 '처음 나온 수업' 열 빼기
    def table(block):
        rows=block.split('\n'); head=[c.strip() for c in rows[0].strip('|').split('|')]
        drop=[i for i,h in enumerate(head) if h in ('처음 나온 수업','#')]
        if not drop: return block
        def cut(r):
            cells=re.split(r'(?<!\\)\|',r.strip().strip('|'))
            cells=[c for j,c in enumerate(cells) if j not in drop]
            return '| '+' | '.join(c.strip() for c in cells)+' |'
        return '\n'.join(cut(r) for r in rows)
    t=re.sub(r'(?m)(^\|.*\|[ \t]*\n?)+',lambda m:table(m.group(0).rstrip('\n'))+('\n' if m.group(0).endswith('\n') else ''),t)
    return re.sub(r'\n{3,}','\n\n',t)
for p in glob.glob(f'{Q}/**/*.md',recursive=True):
    t=open(p).read(); n=clean(t)
    if n!=t: open(p,'w').write(n)
# 4) 목차·중복 정리
H1=re.compile(r'(?m)^# (.+)\n+')
def toc_cols(block):
    rows=block.split('\n'); head=[c.strip() for c in rows[0].strip('|').split('|')]
    drop=[i for i,h in enumerate(head) if h in ('예','순서','#')]
    if not drop: return block
    def cut(r):
        cells=re.split(r'(?<!\\)\|',r.strip().strip('|'))
        return '| '+' | '.join(c.strip() for j,c in enumerate(cells) if j not in drop)+' |'
    return '\n'.join(cut(r) for r in rows)
def children(d):
    """빈 폴더 첫 화면용: 하위 폴더·노트 목록 (번호 순)"""
    items=[]
    for n in sorted(os.listdir(d),key=lambda s:[int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',s)]):
        p=f'{d}/{n}'; rel=os.path.relpath(p,Q)
        if os.path.isdir(p) and n!='_Audio': items.append(f'- 📁 [[{rel}/index|{strip(n)}]]')
        elif n.endswith('.md') and n!='index.md':
            m=FM.match(open(p).read()); tt=re.search(r'(?m)^title:\s*"?(.*?)"?\s*$',m.group(1)).group(1) if m else strip(n[:-3])
            items.append(f'- [[{rel[:-3]}|{tt}]]')
    return '\n'.join(items)
for p in glob.glob(f'{Q}/**/*.md',recursive=True):
    t=open(p).read(); o=t
    m=FM.match(t); fm=t[:m.end()] if m else ''; body=t[len(fm):]
    title=re.search(r'(?m)^title:\s*"?(.*?)"?\s*$',m.group(1)).group(1) if m else ''
    h=H1.search(body)
    if h and title and title.lower() in h.group(1).lower(): body=body[:h.start()]+body[h.end():]   # 제목과 겹치는 # 제목 줄
    body=re.sub(r'(?m)^←.*\n?','',body)                     # 위 경로(breadcrumbs)와 겹치는 ← 줄
    body=re.sub(r'\s*\((\d+)~(\d+)\)','',body)              # 번호 범위 (1~5)
    if os.path.basename(p)=='index.md':
        body=re.sub(r'(?m)(^\|.*\|[ \t]*\n?)+',lambda x:toc_cols(x.group(0).rstrip('\n'))+'\n',body)
        if not body.strip() and os.path.dirname(p)!=Q: body='\n'+children(os.path.dirname(p))+'\n'
    t=fm+body.lstrip('\n') if fm else body
    t=re.sub(r'\n{3,}','\n\n',t)
    if t!=o: open(p,'w').write(t)
# 5) 목차 꼬리 정리: 다른 책 링크(왼쪽 목록과 겹침), 빈 섹션, 제목 번호, 폴더 경로 설명
for p in glob.glob(f'{Q}/**/*.md',recursive=True):
    t=open(p).read(); o=t
    m=FM.match(t); fm=t[:m.end()] if m else ''; body=t[len(fm):]
    body=re.sub(r'(?m)^다른 책:.*\n?','',body)
    body=re.sub(r'(?m)^.*`3 Mots/.*\n?','',body)
    body=re.sub(r'(?m)^(#+ )\d+부?\s*·\s*',r'\1',body)
    body=re.sub(r'(?m)^#+ .*\(자동\)\s*$\n?','',body)
    body=re.sub(r'(?m)^(#+ .*)\n+(?=#+ |\Z)','',body)       # 내용 없는 제목
    body=re.sub(r'\n+---\s*\Z','\n',body.rstrip()+'\n')    # 끝에 남은 구분선
    t=fm+body.lstrip('\n')
    t=re.sub(r'\n{3,}','\n\n',t)
    if t!=o: open(p,'w').write(t)
# 6) 사이트에서 겹치는 플래시카드 목록(위 표와 같음)·빈 항목 빼기
for p in glob.glob(f'{Q}/**/*.md',recursive=True):
    t=open(p).read(); o=t
    t=re.sub(r'(?ms)^## 🃏 플래시카드.*?(?=^## |\Z)','',t)
    t=re.sub(r'(?m)^\*\*[^*]+\*\*:\s*—\s*$\n?','',t)
    t=re.sub(r'\n{3,}','\n\n',t).rstrip()+'\n'
    if t!=o: open(p,'w').write(t)
