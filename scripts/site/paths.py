"""경로 설정 — 볼트 위치가 다르면 VAULT 환경 변수로 바꿔요"""
import os
VAULT = os.path.expanduser(os.environ.get('VAULT', '~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Francisation_notes'))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.environ.get('SITE_OUT', '/tmp/quebec-francais-content')
