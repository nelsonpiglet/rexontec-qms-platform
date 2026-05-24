"""
REXONTEC 力科 — 維修系統 Google Drive 照片上傳工具
照片存放結構：REXONTEC_維修照片 / {RMA_ID} / {檔名}
"""
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

ROOT_FOLDER = "REXONTEC_維修照片"


def _drive_service():
    from utils.rma_gsheet import get_client
    creds = get_client().auth
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_or_create_folder(svc, name: str, parent_id: str = None) -> str:
    q = (f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
         f" and trashed=false")
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = svc.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_photos(uploaded_files: list, rma_id: str) -> list[str]:
    if not uploaded_files:
        return []
    try:
        svc        = _drive_service()
        root_id    = _get_or_create_folder(svc, ROOT_FOLDER)
        rma_folder = _get_or_create_folder(svc, rma_id, parent_id=root_id)

        urls = []
        for f in uploaded_files:
            mime = f.type or "image/jpeg"
            media = MediaIoBaseUpload(
                io.BytesIO(f.read()),
                mimetype=mime,
                resumable=False,
            )
            obj = svc.files().create(
                body={"name": f.name, "parents": [rma_folder]},
                media_body=media,
                fields="id",
            ).execute()
            fid = obj["id"]
            svc.permissions().create(
                fileId=fid,
                body={"type": "anyone", "role": "reader"},
            ).execute()
            urls.append(f"https://drive.google.com/uc?export=view&id={fid}")
        return urls

    except Exception as e:
        print(f"[Drive] 上傳失敗：{e}")
        return []


def get_folder_link(rma_id: str) -> str | None:
    try:
        svc     = _drive_service()
        root_id = _get_or_create_folder(svc, ROOT_FOLDER)
        fid     = _get_or_create_folder(svc, rma_id, parent_id=root_id)
        return f"https://drive.google.com/drive/folders/{fid}"
    except Exception:
        return None
