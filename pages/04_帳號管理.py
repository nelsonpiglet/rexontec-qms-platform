"""
REXONTEC 力科 OQC — 帳號管理（管理員專用）
"""
import streamlit as st
from utils.style import QMS_CSS, topbar, page_header
from utils.auth import (
    require_login, user_info_bar,
    get_all_users, approve_user, reject_user,
    delete_user, update_role, change_password,
    create_user, get_auto_login_admin, set_auto_login_admin,
)

st.set_page_config(
    page_title="REXONTEC 力科 | OQC 帳號管理",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)

require_login(admin_only=True)
user_info_bar()

# ── 導覽列 ─────────────────────────────────────────────
col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 1, 1, 4])
with col_nav1:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with col_nav2:
    if st.button("📋 檢驗輸入", use_container_width=True):
        st.switch_page("pages/01_出廠檢驗輸入.py")
with col_nav3:
    if st.button("📊 儀表板", use_container_width=True):
        st.switch_page("pages/02_儀表板.py")
with col_nav4:
    if st.button("⚙️ 系統設定", use_container_width=True):
        st.switch_page("pages/03_系統設定.py")

st.markdown(page_header("帳號管理", "使用者審核 / 權限設定 / 密碼重設", "USR"),
            unsafe_allow_html=True)

# ── 額外 CSS ─────────────────────────────────────────────
st.markdown("""
<style>
.user-card {
  background:#fff; border:1px solid var(--border); border-radius:8px;
  padding:14px 16px; margin-bottom:8px; box-shadow:var(--sh);
  display:flex; align-items:center; gap:16px; flex-wrap:wrap;
}
.user-avatar {
  width:42px; height:42px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:18px; font-weight:700;
}
.avatar-admin    { background:#e3f2fd; color:var(--accent); }
.avatar-pending  { background:#fef9e7; color:var(--orange); }
.avatar-inspector{ background:#eafaf1; color:var(--teal); }
.user-info { flex:1; min-width:180px; }
.user-name { font-size:13px; font-weight:700; color:var(--navy); }
.user-meta { font-size:11px; color:var(--muted); margin-top:2px; }
.badge-admin    { background:var(--accent); color:#fff; padding:1px 8px; border-radius:10px; font-size:10px; font-weight:700; margin-left:6px; }
.badge-inspector{ background:var(--teal);   color:#fff; padding:1px 8px; border-radius:10px; font-size:10px; font-weight:700; margin-left:6px; }
.badge-pending  { background:var(--orange); color:#fff; padding:1px 8px; border-radius:10px; font-size:10px; font-weight:700; margin-left:6px; }
.badge-rejected { background:var(--cr);     color:#fff; padding:1px 8px; border-radius:10px; font-size:10px; font-weight:700; margin-left:6px; }
</style>
""", unsafe_allow_html=True)

me = st.session_state.get("oqc_username", "")
all_users = get_all_users()

# ── 統計摘要 ──────────────────────────────────────────
pending   = [u for u in all_users if u["status"] == "pending"]
active    = [u for u in all_users if u["status"] == "active"]
rejected  = [u for u in all_users if u["status"] == "rejected"]

sc1, sc2, sc3, sc4 = st.columns(4)
def stat_card(col, value, label, cls=""):
    col.markdown(
        f'<div class="stat-card {cls}">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div></div>',
        unsafe_allow_html=True,
    )
stat_card(sc1, len(all_users), "全部帳號")
stat_card(sc2, len(active),   "啟用中",   "sc-green")
stat_card(sc3, len(pending),  "待審核",   "sc-orange")
stat_card(sc4, len(rejected), "已拒絕",   "sc-red")

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    f"⏳ 待審核申請 {'🔴' if pending else ''}（{len(pending)}）",
    f"✅ 啟用帳號（{len(active)}）",
    "📋 全部帳號",
    "🔑 新增帳號 / 我的密碼",
])

# ═══════════════════════════════════════════════════
# Tab 1：待審核申請
# ═══════════════════════════════════════════════════
with tab1:
    if not pending:
        st.success("目前沒有待審核的申請。")
    else:
        st.info(f"共有 {len(pending)} 個帳號申請等待審核。")

    for u in pending:
        uname = u["username"]
        with st.container():
            st.markdown(
                f'<div class="user-card">'
                f'<div class="user-avatar avatar-pending">⏳</div>'
                f'<div class="user-info">'
                f'<div class="user-name">{u["display_name"]}'
                f'<span class="badge-pending">待審核</span></div>'
                f'<div class="user-meta">帳號：{uname}　申請時間：{u.get("created_at","─")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            a1, a2, a3, a4 = st.columns([2, 2, 1, 1])
            with a1:
                role_sel = st.selectbox(
                    "授予角色", ["inspector（檢驗員）", "admin（管理員）"],
                    key=f"role_sel_{uname}",
                    label_visibility="collapsed",
                )
            with a2:
                st.caption(f"申請者：{u['display_name']}")
            with a3:
                if st.button("✅ 核准", key=f"approve_{uname}",
                             use_container_width=True, type="primary"):
                    role = "admin" if "admin" in role_sel else "inspector"
                    approve_user(uname, by=me, role=role)
                    st.success(f"已核准「{u['display_name']}」（{role}）")
                    st.rerun()
            with a4:
                if st.button("❌ 拒絕", key=f"reject_{uname}",
                             use_container_width=True):
                    reject_user(uname)
                    st.warning(f"已拒絕「{u['display_name']}」的申請")
                    st.rerun()

# ═══════════════════════════════════════════════════
# Tab 2：啟用帳號管理
# ═══════════════════════════════════════════════════
with tab2:
    if not active:
        st.warning("目前沒有啟用中的帳號。")

    for u in active:
        uname = u["username"]
        role  = u["role"]
        is_me = (uname == me)

        badge_cls = "badge-admin" if role == "admin" else "badge-inspector"
        badge_txt = "管理員" if role == "admin" else "檢驗員"
        avatar_cls= "avatar-admin" if role == "admin" else "avatar-inspector"
        avatar_ic = "👑" if role == "admin" else "👤"

        st.markdown(
            f'<div class="user-card">'
            f'<div class="user-avatar {avatar_cls}">{avatar_ic}</div>'
            f'<div class="user-info">'
            f'<div class="user-name">{u["display_name"]}'
            f'<span class="{badge_cls}">{badge_txt}</span>'
            f'{"  <span style=\"font-size:10px;color:var(--orange)\">(你)</span>" if is_me else ""}'
            f'</div>'
            f'<div class="user-meta">'
            f'帳號：{uname}　核准者：{u.get("approved_by","─")}　'
            f'建立：{u.get("created_at","─")}'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        b1, b2, b3 = st.columns([3, 1, 1])
        with b1:
            new_role = st.selectbox(
                "角色", ["inspector（檢驗員）", "admin（管理員）"],
                index=1 if role == "admin" else 0,
                key=f"edit_role_{uname}",
                label_visibility="collapsed",
                disabled=is_me,  # 不能改自己的角色
            )
        with b2:
            if not is_me:
                if st.button("更新角色", key=f"upd_role_{uname}", use_container_width=True):
                    nr = "admin" if "admin" in new_role else "inspector"
                    update_role(uname, nr)
                    st.success(f"已更新「{u['display_name']}」角色為 {nr}")
                    st.rerun()
        with b3:
            if not is_me:
                if st.button("🗑 刪除帳號", key=f"del_{uname}", use_container_width=True):
                    delete_user(uname)
                    st.warning(f"已刪除「{u['display_name']}」")
                    st.rerun()

        st.markdown("---")

# ═══════════════════════════════════════════════════
# Tab 3：全部帳號總覽
# ═══════════════════════════════════════════════════
with tab3:
    import pandas as pd
    rows = []
    for u in all_users:
        rows.append({
            "帳號":     u["username"],
            "姓名":     u["display_name"],
            "角色":     {"admin": "管理員", "inspector": "檢驗員"}.get(u["role"], u["role"]),
            "狀態":     {"active": "✅ 啟用", "pending": "⏳ 待審核",
                         "rejected": "❌ 拒絕"}.get(u["status"], u["status"]),
            "核准者":   u.get("approved_by", "─"),
            "建立時間": u.get("created_at", "─"),
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("目前尚無任何帳號。")

    # 已拒絕帳號管理
    if rejected:
        st.markdown("---")
        st.markdown("**已拒絕帳號（可重新開放或刪除）**")
        for u in rejected:
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(
                    f'`{u["username"]}`　{u["display_name"]}　'
                    f'<span class="badge-rejected">已拒絕</span>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("重新啟用", key=f"reopen_{u['username']}", use_container_width=True):
                    approve_user(u["username"], by=me, role="inspector")
                    st.rerun()
            with c3:
                if st.button("永久刪除", key=f"perm_del_{u['username']}", use_container_width=True):
                    delete_user(u["username"])
                    st.rerun()

# ═══════════════════════════════════════════════════
# Tab 4：新增帳號 / 修改密碼
# ═══════════════════════════════════════════════════
with tab4:
    # ── 管理員免登入設定 ─────────────────────────────
    st.markdown("#### 🔓 管理員免登入設定")
    current_auto = get_auto_login_admin()
    admin_users  = [u for u in all_users
                    if u["role"] == "admin" and u["status"] == "active"]

    st.markdown("""
<div style="background:#fff;border:1px solid var(--border);border-left:4px solid var(--orange);
            border-radius:8px;padding:14px 18px;margin-bottom:16px;box-shadow:var(--sh)">
  <div style="font-size:13px;font-weight:700;color:var(--navy);margin-bottom:6px">
    💡 說明
  </div>
  <div style="font-size:12px;color:var(--muted);line-height:1.8">
    啟用後，指定的管理員帳號在開啟系統時<b>自動登入</b>，不需輸入帳號密碼。<br>
    其他使用者（檢驗員）仍需正常登入。<br>
    <b>建議</b>：系統架設在您自己的電腦上時使用，若部署到公共伺服器請關閉此功能。
  </div>
</div>
""", unsafe_allow_html=True)

    al1, al2, al3 = st.columns([3, 2, 2])
    with al1:
        admin_options = ["（停用免登入）"] + [
            f"{u['display_name']} ({u['username']})" for u in admin_users
        ]
        # 找出目前選項的 index
        cur_idx = 0
        if current_auto:
            for i, u in enumerate(admin_users, start=1):
                if u["username"] == current_auto:
                    cur_idx = i
                    break
        sel_auto = st.selectbox(
            "免登入管理員帳號",
            admin_options,
            index=cur_idx,
            key="auto_login_sel",
        )
    with al2:
        st.markdown("<br>", unsafe_allow_html=True)
        if current_auto:
            cur_u = next((u for u in admin_users if u["username"] == current_auto), None)
            cur_disp = f"目前：{cur_u['display_name']}" if cur_u else "目前：已停用"
        else:
            cur_disp = "目前：已停用"
        st.caption(cur_disp)
    with al3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("儲存設定", key="save_auto_login",
                     type="primary", use_container_width=True):
            if sel_auto == "（停用免登入）":
                set_auto_login_admin("")
                # 清除目前 session 的 auto_login 標記
                st.session_state.pop("oqc_auto_login", None)
                st.success("✅ 免登入已停用，所有使用者需重新登入")
            else:
                new_uname = sel_auto.split("(")[-1].rstrip(")")
                set_auto_login_admin(new_uname)
                st.session_state.oqc_auto_login = True
                new_disp = sel_auto.split(" (")[0]
                st.success(f"✅ 已設定「{new_disp}」為免登入管理員")
            st.rerun()

    st.markdown("---")
    col_add, col_pwd = st.columns(2)

    with col_add:
        st.markdown("#### ➕ 直接新增帳號（管理員操作，不需審核）")
        with st.form("admin_add_user"):
            na_uname = st.text_input("帳號 *", placeholder="例：john_wang")
            na_dname = st.text_input("姓名 *", placeholder="例：王大明")
            na_role  = st.selectbox("角色", ["inspector（檢驗員）", "admin（管理員）"])
            na_p1    = st.text_input("密碼 *（至少 6 碼）", type="password")
            na_p2    = st.text_input("確認密碼 *", type="password")
            if st.form_submit_button("新增帳號", type="primary", use_container_width=True):
                if not na_uname.strip() or not na_dname.strip():
                    st.error("帳號與名稱不可空白")
                elif na_p1 != na_p2:
                    st.error("兩次密碼不一致")
                else:
                    role = "admin" if "admin" in na_role else "inspector"
                    ok, msg = create_user(na_uname.strip(), na_dname.strip(),
                                          na_p1, role=role, status="active")
                    if ok:
                        st.success(f"✅ 帳號「{na_dname.strip()}」建立成功")
                        st.rerun()
                    else:
                        st.error(msg)

    with col_pwd:
        st.markdown("#### 🔑 重設任意帳號密碼")
        user_options = [f"{u['display_name']} ({u['username']})"
                        for u in all_users if u["status"] == "active"]
        if user_options:
            with st.form("reset_pwd_form"):
                sel_user = st.selectbox("選擇帳號", user_options)
                new_p1   = st.text_input("新密碼 *（至少 6 碼）", type="password")
                new_p2   = st.text_input("確認新密碼 *", type="password")
                if st.form_submit_button("重設密碼", type="primary", use_container_width=True):
                    if new_p1 != new_p2:
                        st.error("兩次密碼不一致")
                    else:
                        uname_sel = sel_user.split("(")[-1].rstrip(")")
                        ok, msg = change_password(uname_sel, new_p1)
                        if ok:
                            st.success(f"✅ 密碼已重設")
                        else:
                            st.error(msg)
        else:
            st.info("目前無啟用中的帳號可重設密碼。")

        st.markdown("---")
        st.markdown("#### 🔐 修改我的密碼")
        with st.form("my_pwd_form"):
            my_p1 = st.text_input("新密碼 *（至少 6 碼）", type="password",
                                   key="my_new_pwd")
            my_p2 = st.text_input("確認新密碼 *", type="password",
                                   key="my_new_pwd2")
            if st.form_submit_button("修改密碼", use_container_width=True):
                if my_p1 != my_p2:
                    st.error("兩次密碼不一致")
                else:
                    ok, msg = change_password(me, my_p1)
                    if ok:
                        st.success("✅ 密碼修改成功！")
                    else:
                        st.error(msg)
