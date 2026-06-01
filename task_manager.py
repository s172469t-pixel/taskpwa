"""
タスク管理 CLI — Google Drive の tasks.json を読み書きします。

セットアップ:
  1. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  2. Google Cloud Console でプロジェクトを作成し Drive API を有効化
  3. OAuth 2.0 クライアントID（デスクトップアプリ）を作成して
     credentials.json をこのファイルと同じ場所に置く
  4. 初回実行時にブラウザでGoogleアカウントのログインが求められます
     (token.json が生成され、以降は自動ログイン)
"""

import os
import io
import json
import sys
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES        = ['https://www.googleapis.com/auth/drive.file']
CREDS_FILE    = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE    = os.path.join(os.path.dirname(__file__), 'token.json')
DRIVE_FNAME   = 'tasks.json'


# ── 認証 ──────────────────────────────────────────────────────────

def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                print(f'[エラー] {CREDS_FILE} が見つかりません。')
                print('Google Cloud Console から credentials.json をダウンロードして')
                print(f'{os.path.dirname(__file__)} に配置してください。')
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)


# ── Drive ファイル操作 ─────────────────────────────────────────────

def find_file_id(service):
    q = f"name='{DRIVE_FNAME}' and trashed=false"
    res = service.files().list(q=q, fields='files(id)', spaces='drive').execute()
    files = res.get('files', [])
    return files[0]['id'] if files else None


def load_tasks(service):
    fid = find_file_id(service)
    if not fid:
        return []
    req = service.files().get_media(fileId=fid)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    return json.loads(buf.read().decode('utf-8'))


def save_tasks(service, tasks):
    fid  = find_file_id(service)
    body = json.dumps(tasks, ensure_ascii=False, indent=2).encode('utf-8')
    media = MediaIoBaseUpload(io.BytesIO(body), mimetype='application/json', resumable=False)
    if fid:
        service.files().update(fileId=fid, media_body=media).execute()
    else:
        metadata = {'name': DRIVE_FNAME, 'mimeType': 'application/json'}
        service.files().create(body=metadata, media_body=media, fields='id').execute()
    print('[同期] Google Drive の tasks.json を更新しました。')


# ── 表示ヘルパー ──────────────────────────────────────────────────

DEADLINE_LABEL = {
    'asap': 'ASAP', 'today': '今日中', 'fri': '今週中(金)',
    'sun': '今週中(日)', 'datetime': '日時指定', 'none': 'なし',
}

def fmt_dt(iso):
    if not iso:
        return ''
    try:
        d = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return d.strftime('%Y/%m/%d %H:%M')
    except Exception:
        return iso

def print_task(t, idx):
    status = '✓' if t.get('done') else '○'
    dl = DEADLINE_LABEL.get(t.get('deadlineType', ''), '')
    if t.get('deadlineIso') and t.get('deadlineType') == 'datetime':
        dl = fmt_dt(t['deadlineIso'])
    protect = ' 🔒' if t.get('protect') else ''
    note    = f"  備考: {t['note']}" if t.get('note') else ''
    start   = f"  開始: {fmt_dt(t['startIso'])}" if t.get('startIso') else ''
    print(f"  [{idx}] {status} {t['title']}{protect}  期限:{dl or 'なし'}{start}{note}")


def list_tasks(tasks, show_done=False):
    pending = [t for t in tasks if not t.get('done')]
    done    = [t for t in tasks if t.get('done')]
    print(f'\n── 未完了タスク ({len(pending)}件) ──')
    if pending:
        for i, t in enumerate(pending):
            print_task(t, i)
    else:
        print('  (なし)')
    if show_done and done:
        print(f'\n── 完了済み ({len(done)}件) ──')
        for i, t in enumerate(done):
            print_task(t, len(pending) + i)
    print()


# ── タスク操作 ────────────────────────────────────────────────────

def add_task(tasks):
    title = input('タイトル: ').strip()
    if not title:
        print('タイトルは必須です。'); return tasks
    print('期限 [1:ASAP 2:今日中 3:今週(金) 4:今週(日) 5:なし]: ', end='')
    dl_map = {'1': 'asap', '2': 'today', '3': 'fri', '4': 'sun', '5': 'none'}
    dl_type = dl_map.get(input().strip(), 'none')
    protect = input('完了後も保持? [y/N]: ').strip().lower() == 'y'
    note    = input('備考 (任意): ').strip()
    tasks.append({
        'id':           int(datetime.now().timestamp() * 1000),
        'title':        title,
        'deadlineType': dl_type,
        'deadlineIso':  None,
        'startIso':     None,
        'protect':      protect,
        'notifyHours':  24,
        'note':         note or None,
        'done':         False,
        'createdAt':    datetime.now().isoformat(),
    })
    print(f'追加: {title}')
    return tasks


def complete_task(tasks):
    pending = [t for t in tasks if not t.get('done')]
    if not pending:
        print('未完了タスクがありません。'); return tasks
    list_tasks(tasks)
    try:
        idx = int(input('完了にするタスク番号: '))
        t   = pending[idx]
    except (ValueError, IndexError):
        print('無効な番号です。'); return tasks
    if t.get('protect'):
        t['done']   = True
        t['doneAt'] = datetime.now().isoformat()
        print(f'完了（保護): {t["title"]}')
    else:
        tasks = [x for x in tasks if x['id'] != t['id']]
        print(f'完了・削除: {t["title"]}')
    return tasks


def delete_task(tasks):
    list_tasks(tasks, show_done=True)
    all_t = [t for t in tasks if not t.get('done')] + [t for t in tasks if t.get('done')]
    try:
        idx = int(input('削除するタスク番号: '))
        t   = all_t[idx]
    except (ValueError, IndexError):
        print('無効な番号です。'); return tasks
    confirm = input(f'"{t["title"]}" を削除しますか? [y/N]: ').strip().lower()
    if confirm == 'y':
        tasks = [x for x in tasks if x['id'] != t['id']]
        print(f'削除: {t["title"]}')
    return tasks


# ── メインループ ──────────────────────────────────────────────────

def main():
    print('Googleアカウントに接続中...')
    service = get_service()
    print('接続完了。Google Drive からタスクを読み込んでいます...')
    tasks = load_tasks(service)
    print(f'{len(tasks)} 件読み込みました。')

    while True:
        print('─' * 40)
        print('[1] タスク一覧  [2] 追加  [3] 完了  [4] 削除  [5] 同期  [0] 終了')
        cmd = input('> ').strip()
        if cmd == '0':
            break
        elif cmd == '1':
            list_tasks(tasks, show_done=True)
        elif cmd == '2':
            tasks = add_task(tasks)
            save_tasks(service, tasks)
        elif cmd == '3':
            tasks = complete_task(tasks)
            save_tasks(service, tasks)
        elif cmd == '4':
            tasks = delete_task(tasks)
            save_tasks(service, tasks)
        elif cmd == '5':
            print('Drive から最新データを取得中...')
            tasks = load_tasks(service)
            print(f'{len(tasks)} 件読み込みました。')
        else:
            print('無効なコマンドです。')

    print('終了します。')


if __name__ == '__main__':
    main()
