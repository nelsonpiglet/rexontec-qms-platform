"""
REXONTEC OQC — 帳號認證模組
儲存位置：config/users.json
密碼：SHA-256 + 隨機 salt
角色：admin（管理員）/ inspector（檢驗員）
狀態：active / pending（待審核）/ rejected（已拒絕）
"""
import os, json, hashlib, secrets, copy
from datetime import datetime
import streamlit as st

USERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'users.json')


# ══════════════════════════════════════════════════
# 密碼工具
# ══════════════════════════════════════════════════
def _hash_pw(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return h, salt


# ══════════════════════════════════════════════════
# 資料讀寫
# ══════════════════════════════════════════════════
def _load() -> dict:
    try:
        with open(USERS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        d = {"users": []}
        _dump(d)
        return d
    except Exception:
        return {"users": []}

def _dump(data: dict):
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    with open(USERS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════
# User CRUD
# ══════════════════════════════════════════════════
def get_all_users() -> list:
    return _load().get("users", [])

def find_user(username: str) -> dict:
    for u in get_all_users():
        if u["username"] == username:
            return u
    return None

def has_admin() -> bool:
    return any(u["role"] == "admin" and u["status"] == "active"
               for u in get_all_users())

def create_user(username: str, display_name: str, password: str,
                role: str = "inspector", status: str = "pending") -> tuple:
    """回傳 (success: bool, message: str)"""
    # 空格自動轉底線，並移除頭尾空白
    username = username.strip().replace(" ", "_")
    if len(username) < 2:
        return False, "帳號至少需 2 個字元"
    if len(password) < 6:
        return False, "密碼至少需 6 個字元"
    if find_user(username):
        return False, f"帳號「{username}」已存在"

    h, salt = _hash_pw(password)
    data = _load()

    # 若目前無任何帳號 → 第一個帳號自動升為 admin/active
    if not data["users"]:
        role, status = "admin", "active"

    data["users"].append({
        "username":      username,
        "display_name":  display_name,
        "password_hash": h,
        "salt":          salt,
        "role":          role,
        "status":        status,
        "created_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "approved_by":   "system" if not data["users"] or role == "admin" else "",
    })
    _dump(data)
    return True, "ok"

def verify_login(username: str, password: str) -> tuple:
    u = find_user(username)
    if not u:
        return False, "帳號不存在"
    if u["status"] == "pending":
        return False, "帳號尚待管理員審核，請耐心等候"
    if u["status"] == "rejected":
        return False, "帳號申請已被拒絕，請聯絡管理員"
    if u["status"] != "active":
        return False, "帳號狀態異常"
    h, _ = _hash_pw(password, u["salt"])
    if h != u["password_hash"]:
        return False, "密碼錯誤"
    return True, "ok"

def approve_user(username: str, by: str, role: str = "inspector"):
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            u["status"]      = "active"
            u["role"]        = role
            u["approved_by"] = by
            u["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _dump(data)

def reject_user(username: str):
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            u["status"] = "rejected"
    _dump(data)

def delete_user(username: str):
    data = _load()
    data["users"] = [u for u in data["users"] if u["username"] != username]
    _dump(data)

def update_role(username: str, new_role: str):
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            u["role"] = new_role
    _dump(data)

def change_password(username: str, new_pw: str) -> tuple:
    if len(new_pw) < 6:
        return False, "密碼至少需 6 個字元"
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            h, salt = _hash_pw(new_pw)
            u["password_hash"] = h
            u["salt"]          = salt
    _dump(data)
    return True, "ok"


# ══════════════════════════════════════════════════
# 管理員免登入設定
# ══════════════════════════════════════════════════
def get_auto_login_admin() -> str:
    """回傳免登入管理員帳號名稱，空字串代表停用"""
    return _load().get("auto_login_admin", "")

def set_auto_login_admin(username: str):
    """設定免登入管理員（空字串 = 停用）"""
    data = _load()
    data["auto_login_admin"] = username
    _dump(data)


# ══════════════════════════════════════════════════
# Streamlit UI 元件
# ══════════════════════════════════════════════════
def require_login(admin_only: bool = False):
    """
    每頁 set_page_config + CSS + topbar 之後立即呼叫。
    - 若尚無管理員帳號 → 顯示初始設定畫面
    - 若啟用免登入模式 → 自動以指定管理員身分進入
    - 其他使用者 → 顯示登入畫面
    admin_only=True 且非 admin → 顯示禁止畫面
    """
    if not has_admin():
        _ui_first_run()
        st.stop()

    # ── 管理員免登入自動驗證 ──────────────────────────
    if not st.session_state.get("oqc_logged_in", False):
        auto_uname = get_auto_login_admin()
        if auto_uname:
            u = find_user(auto_uname)
            if u and u["role"] == "admin" and u["status"] == "active":
                st.session_state.oqc_logged_in  = True
                st.session_state.oqc_username   = u["username"]
                st.session_state.oqc_display    = u["display_name"]
                st.session_state.oqc_role       = u["role"]
                st.session_state.oqc_auto_login = True   # 標記為免登入模式

    if not st.session_state.get("oqc_logged_in", False):
        _ui_login()
        st.stop()

    if admin_only and st.session_state.get("oqc_role") != "admin":
        st.error("⛔ 此頁面僅限管理員存取")
        if st.button("🏠 返回首頁"):
            st.switch_page("app.py")
        st.stop()


def user_info_bar():
    """在 topbar 下方顯示：目前使用者資訊（管理員免登入模式無登出按鈕）"""
    disp       = st.session_state.get("oqc_display", "")
    role       = st.session_state.get("oqc_role", "")
    auto_login = st.session_state.get("oqc_auto_login", False)
    rl         = "管理員 👑" if role == "admin" else "檢驗員"
    color      = "var(--accent)" if role == "admin" else "var(--teal)"
    mode_tag   = (
        '<span style="background:#f0a500;color:#fff;padding:1px 8px;border-radius:10px;'
        'font-size:10px;margin-left:8px;font-weight:700">免登入</span>'
        if auto_login else ""
    )

    if auto_login:
        # 免登入模式：只顯示姓名 + 帳號管理，不顯示登出
        c_info, c_mgmt = st.columns([8, 1])
        with c_info:
            st.markdown(
                f'<p style="font-size:12px;color:var(--muted);margin:2px 0 6px;padding:0">'
                f'👤 <b style="color:var(--navy)">{disp}</b>'
                f'<span style="background:{color};color:#fff;padding:1px 8px;'
                f'border-radius:10px;font-size:10px;margin-left:8px;font-weight:700">{rl}</span>'
                f'{mode_tag}</p>',
                unsafe_allow_html=True,
            )
        with c_mgmt:
            if st.button("👥 帳號", key="_ub_acct", use_container_width=True):
                st.switch_page("pages/04_帳號管理.py")
    else:
        # 一般登入模式：顯示姓名 + 帳號管理 + 登出
        c_info, c_mgmt, c_out = st.columns([7, 1, 1])
        with c_info:
            st.markdown(
                f'<p style="font-size:12px;color:var(--muted);margin:2px 0 6px;padding:0">'
                f'👤 已登入：<b style="color:var(--navy)">{disp}</b>'
                f'<span style="background:{color};color:#fff;padding:1px 8px;'
                f'border-radius:10px;font-size:10px;margin-left:8px;font-weight:700">{rl}</span>'
                f'</p>',
                unsafe_allow_html=True,
            )
        with c_mgmt:
            if role == "admin":
                if st.button("👥 帳號", key="_ub_acct", use_container_width=True):
                    st.switch_page("pages/04_帳號管理.py")
        with c_out:
            if st.button("🚪 登出", key="_ub_out", use_container_width=True):
                for k in ["oqc_logged_in", "oqc_username", "oqc_display",
                          "oqc_role", "oqc_auto_login"]:
                    st.session_state.pop(k, None)
                st.rerun()

    # 待審核通知（管理員才看到）
    if role == "admin":
        pending = [u for u in get_all_users() if u["status"] == "pending"]
        if pending:
            st.warning(f"⏳ 有 **{len(pending)}** 個帳號申請待審核，請前往「👥 帳號」審核。",
                       icon="🔔")


# ══════════════════════════════════════════════════
# 內部 UI：首次設定 / 登入
# ══════════════════════════════════════════════════
def _ui_first_run():
    st.markdown("""
<div style="text-align:center;padding:30px 0 10px">
  <div style="font-size:48px">⚙️</div>
  <div style="font-size:20px;font-weight:900;color:var(--navy);margin-top:8px">系統初始設定</div>
  <div style="font-size:12.5px;color:var(--muted);margin-top:5px">
    請建立第一個管理員帳號以啟動系統
  </div>
</div>
""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("_first_run_form"):
            st.markdown("#### 建立管理員帳號")
            uname = st.text_input("帳號 *", placeholder="例：Nelson_tsai",
                                  help="可輸入英文、數字、空格；空格會自動轉為底線 _")
            dname = st.text_input("顯示名稱 *", placeholder="例：蔡承叡")
            p1    = st.text_input("密碼 *（至少 6 碼）", type="password")
            p2    = st.text_input("確認密碼 *", type="password")
            if st.form_submit_button("🚀 建立並啟動系統", type="primary",
                                     use_container_width=True):
                if not uname.strip() or not dname.strip():
                    st.error("帳號與名稱不可空白")
                elif p1 != p2:
                    st.error("兩次密碼不一致")
                else:
                    ok, msg = create_user(uname.strip(), dname.strip(), p1,
                                          role="admin", status="active")
                    if ok:
                        # 建立後自動啟用免登入（管理者不需每次登入）
                        set_auto_login_admin(uname.strip())
                        st.success(f"✅ 管理員「{dname.strip()}」建立成功！已自動啟用免登入模式。")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)


def _ui_login():
    st.markdown("""
<div style="text-align:center;margin:24px 0 16px">
  <div style="font-size:48px">🔬</div>
  <div style="font-size:20px;font-weight:900;color:var(--navy);margin-top:6px">
    REXONTEC QMS
  </div>
  <div style="font-size:12px;color:var(--muted);margin-top:4px">
    檢驗品質管制系統 — 請登入後使用
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_t, reg_t = st.tabs(["🔑 登入", "📝 申請帳號"])

        with login_t:
            with st.form("_login_form"):
                uname = st.text_input("帳號", placeholder="輸入您的帳號")
                pwd   = st.text_input("密碼", type="password", placeholder="輸入密碼")
                if st.form_submit_button("登入", type="primary", use_container_width=True):
                    ok, msg = verify_login(uname.strip(), pwd)
                    if ok:
                        u = find_user(uname.strip())
                        st.session_state.oqc_logged_in = True
                        st.session_state.oqc_username  = u["username"]
                        st.session_state.oqc_display   = u["display_name"]
                        st.session_state.oqc_role      = u["role"]
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        with reg_t:
            st.info("送出後需等候管理員審核通過，才可登入使用。")
            with st.form("_reg_form"):
                r_uname = st.text_input("帳號 *（英數字、底線）", placeholder="例：john_wang")
                r_dname = st.text_input("姓名 *", placeholder="例：王大明")
                r_p1    = st.text_input("密碼 *（至少 6 碼）", type="password")
                r_p2    = st.text_input("確認密碼 *", type="password")
                if st.form_submit_button("送出申請", use_container_width=True):
                    if not r_uname.strip() or not r_dname.strip():
                        st.error("帳號與名稱不可空白")
                    elif r_p1 != r_p2:
                        st.error("兩次密碼不一致")
                    else:
                        ok, msg = create_user(r_uname.strip(), r_dname.strip(), r_p1)
                        if ok:
                            st.success("✅ 申請已送出！請耐心等候管理員審核。")
                        else:
                            st.error(msg)
