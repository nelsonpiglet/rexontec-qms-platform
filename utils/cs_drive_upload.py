"""
REXONTEC 力科 — 客訴8D附件 Google Drive 上傳工具
"""
import io
import streamlit as st
from google.oauth2.service_account import Credentials

ROOT_FOLDER = "REXONTEC_客訴8D附件"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    HAS_DRIVE = True
except ImportError:
    HAS_DRIVE = False


def _get_drive_service():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
        )
    except (KeyError, FileNotFoundError):
        creds = Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, parent_id, name: str) -> str:
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = service.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_8d_files(uploaded_files, d8_id: str, subfolder: str = "") -> list:
    """
    上傳附件到 Google Drive
    uploaded_files : list of st.UploadedFile
    d8_id          : '8D-2026-0001'
    subfolder      : '照片' / '驗證附件' / '熱像圖' / '測試資料'
    return         : list of Drive file URLs
    """
    if not uploaded_files or not HAS_DRIVE:
        return []
    urls = []
    try:
        service  = _get_drive_service()
        root_id  = _get_or_create_folder(service, None, ROOT_FOLDER)
        d8_fid   = _get_or_create_folder(service, root_id, d8_id)
        target   = _get_or_create_folder(service, d8_fid, subfolder) if subfolder else d8_fid

        for f in uploaded_files:
            raw   = f.read()
            mime  = f.type or "application/octet-stream"
            meta  = {"name": f.name, "parents": [target]}
            media = MediaIoBaseUpload(io.BytesIO(raw), mimetype=mime, resumable=False)
            created = service.files().create(
                body=meta, media_body=media, fields="id"
            ).execute()
            fid = created["id"]
            service.permissions().create(
                fileId=fid,
                body={"role": "reader", "type": "anyone"},
            ).execute()
            urls.append(f"https://drive.google.com/file/d/{fid}/view")
    except Exception as e:
        st.warning(f"⚠️ Google Drive 上傳失敗：{e}\n請改手動填入連結。")
    return urls


def get_folder_link(d8_id: str) -> str:
    """取得 8D 資料夾的 Drive 分享連結"""
    if not HAS_DRIVE:
        return ""
    try:
        service = _get_drive_service()
        root_id = _get_or_create_folder(service, None, ROOT_FOLDER)
        d8_fid  = _get_or_create_folder(service, root_id, d8_id)
        service.permissions().create(
            fileId=d8_fid,
            body={"role": "reader", "type": "anyone"},
        ).execute()
        return f"https://drive.google.com/drive/folders/{d8_fid}"
    except Exception:
        return ""
