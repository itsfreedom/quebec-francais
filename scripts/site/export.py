import os,re,shutil,glob,sys,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import VAULT as V, REPO, OUT as Q
sys.path.insert(0,f'{V}/_Tools/blog')
AUD=re.compile(r'\[\[_Audio/([^|\]\\]+)\\?\|🔊 ([^\]]+)\]\]')
BADNAME=re.compile(r'junhyung|kye',re.I)
BADF={l.split('\t')[0] for l in open(f'{V}/_Audio/audio_list.tsv') if re.search(r'junhyung|kye\b|준형',l,re.I)}
def site_audio(t):
    # drop links whose audio contains the real name; keep others
    t=AUD.sub(lambda m:(f'[{m.group(2)}]' if m.group(1) in BADF else f'[🔊 {m.group(2)}](_Audio/{m.group(1)})') if 'ëëë' not in m.group(2) else m.group(0),t)
    t=re.sub(r'\[\[_Audio/([^|]+)\|▶ 이어서 듣기 \(문장 사이 3초\)\]\]',lambda m:'' if m.group(1) in BADF else f'[▶ 이어서 듣기 (문장 사이 3초)](_Audio/{m.group(1)})',t)
    t=re.sub(r'(?m)^\[▶ 이어서 듣기 \(문장 사이 3초\)\]\(_Audio/([^)]+)\)\n+',lambda m:'' if m.group(1) in BADF else m.group(0),t)
    # 대화문 문장 링크 [[_Audio/f|문장]] → [문장](_Audio/f), 실명 파일은 글자만
    t=re.sub(r'\[\[_Audio/([^|\]\\]+)\\?\|([^\]]+)\]\]',lambda m:m.group(2) if m.group(1) in BADF else f'[{m.group(2)}](_Audio/{m.group(1)})',t)
    return t
def plain_audio(t):
    return AUD.sub(lambda m:f'[{m.group(1)}]',t)
DAY={os.path.basename(d):f'{os.path.basename(d)[:4]}-{os.path.basename(d)[4:6]}-{os.path.basename(d)[6:]}' for d in glob.glob(f'{V}/5 Cours/*/2026*') if os.path.isdir(d)}   # 수업 날짜 → 사이트 날짜 페이지
def fix_common(t):
    t=re.sub(r'```dataview.*?```','',t,flags=re.S)
    t=re.sub(r'(?m)^#flashcards/\S+\s*$','',t)
    t=re.sub(r'(?m)^(.+?):::(.+)$',lambda m:m.group(1)+'::'+m.group(2),t)   # 양방향 카드
    t=re.sub(r'(?m)^(.+?)::(.+)$',lambda m:f'**{m.group(1).strip()}** — {m.group(2).strip()}' if not m.group(1).startswith(('-','>','|','#')) else m.group(0),t)
    for k,d in DAY.items():
        t=re.sub(r'\[\['+k+r'(?:_[A-Za-z]+)?(?:#[^\]|]*)?\|([^\]]+)\]\]',lambda m,d=d:f'[[{d}|{m.group(1)}]]',t)
        t=re.sub(r'\[\['+k+r'(?:_[A-Za-z]+)?\]\]',f'[[{d}]]',t)
    t=re.sub(r'<!--SR:.*?-->','',t)
    return site_audio(t)
def run():
    shutil.rmtree(Q,ignore_errors=True); os.makedirs(Q)
    for folder in ['1 Grammaire','2 Dialogues','3 Vocabulaire','4 Phonétique']:
        for p in glob.glob(f'{V}/{folder}/**/*.md',recursive=True):
            rel=os.path.relpath(p,V); out=f'{Q}/{rel}'
            os.makedirs(os.path.dirname(out),exist_ok=True)
            open(out,'w').write(fix_common(open(p).read()))
    # 날짜 페이지 = 볼트 수업 노트 모양 그대로 (daypage.py) + 수업 자료 내려받기
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    import daypage
    from blogmake import NAME
    os.makedirs(f'{Q}/수업/자료',exist_ok=True)
    days=[]
    for k in daypage.days():
        if k not in DAY: DAY[k]=f'{k[:4]}-{k[4:6]}-{k[6:]}'
        d=DAY[k]; title,md=daypage.build(k); days.append((d,title))
        for a,b in NAME: md=md.replace(a,b)
        open(f'{Q}/수업/{d}.md','w').write(f'---\ntitle: "{title}"\ndate: {d}\ntags: [수업]\n---\n\n'+fix_common(md))
        for f in glob.glob(f'{V}/5 Cours/*/{k}/*'):
            if f.lower().endswith(('.pdf','.pptx')): shutil.copy(f,f'{Q}/수업/자료/')
            if f.endswith('_복습.m4a') and k not in daypage.NOREVIEW: os.makedirs(f'{Q}/_Audio',exist_ok=True); shutil.copy(f,f'{Q}/_Audio/')
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),'img','*.png')): shutil.copy(f,f'{Q}/수업/자료/')   # 자료에서 잘라 온 그림
    idx='---\ntitle: 퀘벡 불어 노트\n---\n\n몬트리올에서 정부 불어 과정(Francisation)을 들으며 매일 정리하는 노트예요. 🔊 발음기호를 누르면 캐나다 프랑스어 음성으로 들을 수 있어요.\n\n## 📅 수업\n'
    for d,t in sorted(days,reverse=True): idx+=f'- [[{d}|{t}]]\n'
    idx+='\n## 📚 책\n1. [[00 Grammaire|📐 문법]]\n2. [[00 Dialogues|🗣 대화]]\n3. [[00 Vocabulaire|📚 단어 · 표현]]\n4. [[00 Phonétique|🔤 발음]]\n'
    open(f'{Q}/index.md','w').write(idx)
    # audio
    os.makedirs(f'{Q}/_Audio',exist_ok=True)
    for a in glob.glob(f'{V}/_Audio/*.m4a'):
        if os.path.basename(a) not in BADF: shutil.copy(a,f'{Q}/_Audio/')
    # keep audio already published in the site repo
    for a in glob.glob(f'{REPO}/content/_Audio/*.m4a'):
        b=os.path.basename(a)
        if b not in BADF and not os.path.exists(f'{Q}/_Audio/{b}'): shutil.copy(a,f'{Q}/_Audio/')
    used=set()
    for p in glob.glob(f'{Q}/**/*.md',recursive=True): used|=set(re.findall(r'_Audio/([^)\s]+\.m4a)',open(p).read()))
    have={os.path.basename(a) for a in glob.glob(f'{Q}/_Audio/*.m4a')}
    print('audio linked',len(used),'missing',len(used-have))
    leak=[p for p in glob.glob(f'{Q}/**/*.md',recursive=True) if re.search(r'junhyung|준형|\bkye\b|계준형',open(p).read(),re.I)]
    print('pages',len(glob.glob(f'{Q}/**/*.md',recursive=True)),'leaks',leak)
if __name__=='__main__':
    run()
    # 사이트용 정리 (번호·날짜·안내 상자·중복 빼기, 색인 노트 → 폴더 첫 화면)
    import subprocess; subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),'tidy.py'),Q],check=True)
