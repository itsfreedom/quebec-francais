"""볼트 → 사이트 content 한 번에 갱신
사용 (사이트 저장소에서): python3 scripts/site/publish.py
1) export.py: 볼트 노트 → 임시 폴더 (실명 · 정답 · 비공개 내용 빼기, tidy 포함)
2) 저장소 content/ 를 그 결과로 바꿈 → 그다음 git add/commit/push 하면 GitHub Actions 가 빌드·배포
"""
import os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import VAULT, REPO, OUT
subprocess.run([sys.executable, os.path.join(HERE, 'export.py')], check=True)
dst = os.path.join(REPO, 'content')
shutil.rmtree(dst); shutil.copytree(OUT, dst)
print('content 갱신 끝 →', dst)
