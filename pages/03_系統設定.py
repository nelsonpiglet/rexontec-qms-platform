"""
REXONTEC 力科 OQC — 系統設定
管理：機種清單、客戶、檢驗員、製造組別、ESC/Motor 檢驗項目
"""
import streamlit as st
import copy
from datetime import datetime

from utils.style import QMS_CSS, topbar, page_header
from utils.inspection_data import get_config, save_config, _DEFAULT_CONFIG
from utils.iqc_data import get_parts, save_parts
from utils.ipqc import (
    load_config as ipqc_load, save_config as ipqc_save,
    get_models as ipqc_models, delete_model as ipqc_del_model,
    add_station, delete_station, add_item, delete_item, update_item,
)
from utils.auth import (
    require_login, user_info_bar,
    get_auto_login_admin, set_auto_login_admin,
    get_all_users,
)

# ── 頁面設定 ────────────────────────────────────────
st.set_page_config(
    page_title="REXONTEC 力科 | OQC 系統設定",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()   # 所有登入使用者皆可進入
user_info_bar()

# ── 導覽列 ──────────────────────────────────────────
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 5])
with col_nav1:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with col_nav2:
    if st.button("📋 檢驗輸入", use_container_width=True):
        st.switch_page("pages/01_出廠檢驗輸入.py")
with col_nav3:
    if st.button("📊 儀表板", use_container_width=True):
        st.switch_page("pages/02_儀表板.py")

st.markdown(page_header("系統設定", "機種 / 客戶 / 檢驗員 / 檢驗項目管理", "SET"),
            unsafe_allow_html=True)

# ── 額外 CSS ────────────────────────────────────────
st.markdown("""
<style>
.set-section {
  background:#fff; border:1px solid var(--border); border-radius:8px;
  padding:16px 18px; margin-bottom:14px; box-shadow:var(--sh);
}
.set-label {
  font-size:13px; font-weight:700; color:var(--navy); margin-bottom:10px;
  display:flex; align-items:center; gap:8px;
}
.tag-chip {
  display:inline-flex; align-items:center; gap:6px;
  background:var(--bg); border:1px solid var(--border2);
  border-radius:20px; padding:3px 10px 3px 12px;
  font-size:12px; color:var(--text); margin:3px;
}
.item-row {
  background:#fafbfc; border:1px solid var(--border);
  border-radius:6px; padding:10px 14px; margin-bottom:6px;
}
.item-num { font-size:11px; color:var(--muted); }
.item-name { font-size:13px; font-weight:700; color:var(--navy); }
.item-spec { font-size:11.5px; color:var(--muted); margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ── 讀取設定 ─────────────────────────────────────────
cfg = get_config()

# ── helper：儲存並重跑 ─────────────────────────────────
def _save_and_rerun(new_cfg: dict):
    save_config(new_cfg)
    st.rerun()

# ═══════════════════════════════════════════════════
# Tab 切換
# ═══════════════════════════════════════════════════
tab1, tab2, tab3, tab3b, tab4, tab5, tab6 = st.tabs([
    "⚙️ 基本設定",
    "⚡ 電調 ESC 檢驗項目",
    "🔧 馬達 Motor 檢驗項目",
    "📋 OQC 成檢表模板",
    "🔬 IQC 零件庫",
    "🔐 登入設定",
    "📋 IPQC 巡檢設定",
])

# ───────────────────────────────────────────────────
# TAB 1：基本設定（機種、客戶、檢驗員、製造組別）
# ───────────────────────────────────────────────────
with tab1:
    def list_editor(label: str, icon: str, cfg_key: str, placeholder: str):
        """通用清單編輯器（新增 / 刪除）"""
        items: list = cfg.get(cfg_key, [])
        st.markdown(f'<div class="set-label">{icon} {label}</div>', unsafe_allow_html=True)

        # 顯示現有項目（每個後面有刪除按鈕）
        for idx, item in enumerate(items):
            c1, c2 = st.columns([8, 1])
            with c1:
                lock = "🔒 " if item == "其他" else ""
                st.markdown(
                    f'<div class="tag-chip">{lock}{item}</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if item != "其他":
                    if st.button("✕", key=f"del_{cfg_key}_{idx}", help=f"刪除 {item}"):
                        new_cfg = copy.deepcopy(cfg)
                        new_cfg[cfg_key].pop(idx)
                        _save_and_rerun(new_cfg)

        # 新增輸入框
        new_key = f"new_{cfg_key}"
        col_inp, col_add = st.columns([5, 1])
        with col_inp:
            new_val = st.text_input(
                f"新增 {label}", key=new_key, placeholder=placeholder,
                label_visibility="collapsed",
            )
        with col_add:
            if st.button("＋ 新增", key=f"add_{cfg_key}", use_container_width=True):
                nv = new_val.strip()
                if nv and nv not in items:
                    new_cfg = copy.deepcopy(cfg)
                    # 插入在「其他」之前
                    if "其他" in new_cfg[cfg_key]:
                        pos = new_cfg[cfg_key].index("其他")
                        new_cfg[cfg_key].insert(pos, nv)
                    else:
                        new_cfg[cfg_key].append(nv)
                    _save_and_rerun(new_cfg)
                elif not nv:
                    st.warning("請先輸入名稱")
                else:
                    st.warning(f"「{nv}」已存在")
        st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:12px 0'>",
                    unsafe_allow_html=True)

    list_editor("電調機種", "⚡", "esc_models",   "例：ES2000RX (80A)")
    list_editor("馬達機種", "🔧", "motor_models", "例：MD3005RX (28馬達)")
    list_editor("客戶",    "🏢", "customers",    "例：台灣虎航")
    list_editor("檢驗員",  "👤", "inspectors",   "例：彭碧霞")
    list_editor("主管(品保)","👔","supervisors",  "例：李副理")
    list_editor("製造組別","🏭", "mfg_groups",   "例：D 組")

    # 重設為預設值
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚠️ 危險操作 — 還原預設值"):
        st.warning("此操作將**清除所有自訂設定**，還原成出廠預設值，無法復原！")
        if st.button("🔄 還原所有設定為預設值", type="primary"):
            _save_and_rerun(copy.deepcopy(_DEFAULT_CONFIG))


# ───────────────────────────────────────────────────
# 共用：檢驗項目編輯器（ESC / Motor）
# ───────────────────────────────────────────────────
def inspection_item_editor(product_type: str, sections_key: str):
    cfg_local = get_config()          # 每次重新讀取
    sections: list = cfg_local.get(sections_key, [])

    # ── 新增 Section ──────────────────────────────
    with st.expander("➕ 新增檢驗類別（Section）", expanded=False):
        c1, c2, c3 = st.columns([2, 4, 4])
        with c1:
            new_sec_id    = st.text_input("代號", key=f"ns_id_{product_type}",
                                          placeholder="D", max_chars=4)
        with c2:
            new_sec_label = st.text_input("類別名稱", key=f"ns_lb_{product_type}",
                                          placeholder="例：電氣安規測試類")
        with c3:
            new_sec_sub   = st.text_input("副標題", key=f"ns_su_{product_type}",
                                          placeholder="例：高壓安規設備")
        if st.button("新增類別", key=f"ns_add_{product_type}", type="primary"):
            nid = new_sec_id.strip().upper()
            existing_ids = [s["id"] for s in sections]
            if not nid or not new_sec_label.strip():
                st.warning("代號與名稱不可空白")
            elif nid in existing_ids:
                st.warning(f"代號「{nid}」已存在")
            else:
                new_cfg = copy.deepcopy(cfg_local)
                new_cfg[sections_key].append({
                    "id": nid,
                    "label": new_sec_label.strip(),
                    "subtitle": new_sec_sub.strip(),
                    "items": [],
                })
                _save_and_rerun(new_cfg)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 各 Section ────────────────────────────────
    for sec_idx, sec in enumerate(sections):
        sec_id    = sec["id"]
        sec_label = sec["label"]
        items     = sec.get("items", [])

        # Section 標題列
        hcol1, hcol2, hcol3 = st.columns([7, 1, 1])
        with hcol1:
            st.markdown(
                f'<div style="font-size:14px;font-weight:700;color:var(--navy);'
                f'border-left:4px solid var(--blue2);padding-left:10px;margin-bottom:6px">'
                f'{sec_id}｜{sec_label}'
                f'<span style="font-size:11px;color:var(--muted);margin-left:8px">'
                f'{sec.get("subtitle","")}</span></div>',
                unsafe_allow_html=True,
            )
        with hcol2:
            # 刪除整個 Section（僅在無項目時）
            if not items:
                if st.button("刪除", key=f"del_sec_{product_type}_{sec_idx}",
                             help="刪除此空白類別"):
                    new_cfg = copy.deepcopy(cfg_local)
                    new_cfg[sections_key].pop(sec_idx)
                    _save_and_rerun(new_cfg)
            else:
                st.caption(f"{len(items)} 項")

        # 展開：顯示所有項目
        with st.expander(f"展開 {sec_id} 的 {len(items)} 個檢驗項目", expanded=False):

            # ── 現有項目 ──────────────────────────
            for item_idx, item in enumerate(items):
                iid   = item["id"]
                itype = item.get("type", "pf")

                with st.container():
                    _grade_var = {"CR": "cr", "MA": "ma", "MI": "mi"}.get(item["grade"], "mi")
                    st.markdown(
                        f'<div class="item-row">'
                        f'<div class="item-num">No.{item["no"]}  {iid}  '
                        f'<b style="color:var(--{_grade_var})">'
                        f'{item["grade"]}</b></div>'
                        f'<div class="item-name">{item["name"]}</div>'
                        f'<div class="item-spec">規格：{item["spec"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    ec1, ec2, ec3, ec4 = st.columns([3, 4, 1, 1])
                    with ec1:
                        new_name = st.text_input(
                            "項目名稱", value=item["name"],
                            key=f"ename_{product_type}_{sec_idx}_{item_idx}",
                            label_visibility="collapsed",
                        )
                    with ec2:
                        new_spec = st.text_input(
                            "規格標準", value=item["spec"],
                            key=f"espec_{product_type}_{sec_idx}_{item_idx}",
                            label_visibility="collapsed",
                        )
                    with ec3:
                        if st.button("✏️ 儲存", key=f"esave_{product_type}_{sec_idx}_{item_idx}",
                                     use_container_width=True):
                            new_cfg = copy.deepcopy(cfg_local)
                            new_cfg[sections_key][sec_idx]["items"][item_idx]["name"] = new_name.strip() or item["name"]
                            new_cfg[sections_key][sec_idx]["items"][item_idx]["spec"] = new_spec.strip() or item["spec"]
                            _save_and_rerun(new_cfg)
                    with ec4:
                        if st.button("🗑️ 刪除", key=f"edel_{product_type}_{sec_idx}_{item_idx}",
                                     use_container_width=True):
                            new_cfg = copy.deepcopy(cfg_local)
                            new_cfg[sections_key][sec_idx]["items"].pop(item_idx)
                            _save_and_rerun(new_cfg)

                    # 數值型項目：顯示 min/max 編輯
                    if itype == "num":
                        nc1, nc2, nc3, nc4 = st.columns([2, 2, 2, 2])
                        with nc1:
                            st.caption(f"單位：{item.get('unit','')}")
                        with nc2:
                            cur_min = "" if item.get("min") is None else str(item["min"])
                            new_min = st.text_input(
                                "最小值", value=cur_min,
                                key=f"emin_{product_type}_{sec_idx}_{item_idx}",
                                placeholder="無限制",
                                label_visibility="visible",
                            )
                        with nc3:
                            cur_max = "" if item.get("max") is None else str(item["max"])
                            new_max = st.text_input(
                                "最大值", value=cur_max,
                                key=f"emax_{product_type}_{sec_idx}_{item_idx}",
                                placeholder="無限制",
                                label_visibility="visible",
                            )
                        with nc4:
                            st.caption("")
                            if st.button("更新範圍", key=f"erange_{product_type}_{sec_idx}_{item_idx}"):
                                new_cfg = copy.deepcopy(cfg_local)
                                try:
                                    new_cfg[sections_key][sec_idx]["items"][item_idx]["min"] = \
                                        float(new_min) if new_min.strip() else None
                                    new_cfg[sections_key][sec_idx]["items"][item_idx]["max"] = \
                                        float(new_max) if new_max.strip() else None
                                    _save_and_rerun(new_cfg)
                                except ValueError:
                                    st.error("最小值/最大值請填入數字")

                st.markdown("---")

            # ── 新增項目表單 ───────────────────────
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:var(--blue2);margin-bottom:8px">'
                f'➕ 新增項目至 {sec_id}｜{sec_label}</div>',
                unsafe_allow_html=True,
            )
            f1, f2, f3, f4 = st.columns([3, 4, 1, 1])
            with f1:
                ni_name  = st.text_input("項目名稱*", key=f"ni_name_{product_type}_{sec_idx}",
                                         placeholder="例：絕緣電阻測試")
            with f2:
                ni_spec  = st.text_input("規格標準*", key=f"ni_spec_{product_type}_{sec_idx}",
                                         placeholder="例：≧100 MΩ")
            with f3:
                ni_grade = st.selectbox("等級", ["MA", "CR", "MI"],
                                        key=f"ni_grade_{product_type}_{sec_idx}")
            with f4:
                ni_type  = st.selectbox("類型", ["pf（通過/失敗）", "num（數值量測）"],
                                        key=f"ni_type_{product_type}_{sec_idx}")

            ni_tool = st.text_input("量測工具", key=f"ni_tool_{product_type}_{sec_idx}",
                                    placeholder="例：耐壓測試機")

            # 若選數值型，顯示額外欄位
            type_key = "num" if ni_type.startswith("num") else "pf"
            if type_key == "num":
                u1, u2, u3 = st.columns(3)
                with u1:
                    ni_unit = st.text_input("單位", key=f"ni_unit_{product_type}_{sec_idx}",
                                            placeholder="例：MΩ")
                with u2:
                    ni_min_s = st.text_input("最小值（空白=無限制）",
                                             key=f"ni_min_{product_type}_{sec_idx}")
                with u3:
                    ni_max_s = st.text_input("最大值（空白=無限制）",
                                             key=f"ni_max_{product_type}_{sec_idx}")
            else:
                ni_unit = ""; ni_min_s = ""; ni_max_s = ""

            if st.button(f"新增項目", key=f"ni_add_{product_type}_{sec_idx}", type="primary"):
                if not ni_name.strip() or not ni_spec.strip():
                    st.warning("項目名稱與規格標準不可空白")
                else:
                    # 自動編號：sec_id + (現有數量+1)
                    new_iid = f"{sec_id}{len(items)+1}"
                    new_no  = f"{len(items)+1}.0"
                    new_item = {
                        "id": new_iid, "no": new_no,
                        "name": ni_name.strip(),
                        "spec": ni_spec.strip(),
                        "grade": ni_grade,
                        "type": type_key,
                        "tool": ni_tool.strip(),
                    }
                    if type_key == "num":
                        new_item["unit"] = ni_unit.strip()
                        try:
                            new_item["min"] = float(ni_min_s) if ni_min_s.strip() else None
                            new_item["max"] = float(ni_max_s) if ni_max_s.strip() else None
                        except ValueError:
                            st.error("最小值/最大值請填入數字")
                            st.stop()
                    new_cfg = copy.deepcopy(cfg_local)
                    new_cfg[sections_key][sec_idx]["items"].append(new_item)
                    _save_and_rerun(new_cfg)

        st.markdown("<br>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────
# TAB 2：電調 ESC 檢驗項目（per-model 模板管理）
# ───────────────────────────────────────────────────
with tab2:
    st.markdown("""
<div style="font-size:12px;color:var(--muted);margin-bottom:14px;
            background:#f7f9fc;border:1px solid var(--border);
            border-left:4px solid #e67e22;border-radius:6px;padding:10px 14px">
  管理 ESC 電調各機種的檢驗項目模板。建立機種模板後，「出廠檢驗輸入」→ 電調 ESC 選取對應機種時，
  將自動套用該機種模板。<br>
  <span style="color:#888">尚未建立模板的機種，仍使用「⚙️ 基本設定」中的共用 ESC 預設項目。</span>
</div>
""", unsafe_allow_html=True)

    try:
        from utils.esc_template_db import (
            load_templates as _esc_load, save_templates as _esc_save_tpl,
            delete_template as _esc_del_tpl, upsert_template as _esc_upsert,
            list_models as _esc_list_models,
        )
        from utils.inspection_data import get_config as _get_cfg_esc
        import copy as _cp

        esc_templates = _esc_load()
        _esc_model_list = list(esc_templates.keys())

        # ── 從現有機種複製 ───────────────────────────
        if _esc_model_list:
            st.markdown(
                '<div style="font-size:11px;color:var(--muted);margin-bottom:6px">'
                '📋 快速複製現有機種模板作為新機種的起點：</div>',
                unsafe_allow_html=True,
            )
            _esc_copy_opts = {m: m for m in _esc_model_list}
            _ec1, _ec2 = st.columns([5, 1])
            with _ec1:
                _esc_copy_sel = st.selectbox(
                    "選擇來源機種",
                    options=_esc_model_list,
                    key="esc_copy_sel",
                    label_visibility="collapsed",
                )
            with _ec2:
                if st.button("🔁 複製此機種", use_container_width=True, key="esc_do_copy"):
                    _src_tpl = _cp.deepcopy(esc_templates[_esc_copy_sel])
                    _base    = _esc_copy_sel
                    _existing = set(_esc_model_list)
                    _suffix  = "-COPY"; _n = 2
                    while (_base + _suffix) in _existing:
                        _suffix = f"-COPY{_n}"; _n += 1
                    _new_key = _base + _suffix
                    _src_tpl["model"]      = _new_key
                    _src_tpl["created_at"] = datetime.now().strftime("%Y-%m-%d")
                    _src_tpl["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    _new_tpls = _cp.deepcopy(esc_templates)
                    _new_tpls[_new_key] = _src_tpl
                    _esc_save_tpl(_new_tpls)
                    st.rerun()

            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:10px 0'>",
                unsafe_allow_html=True,
            )

        # ── 新增全新機種模板 ─────────────────────────
        with st.expander("➕ 新增全新機種模板", expanded=False):
            _nm1, _nm2 = st.columns(2)
            with _nm1:
                _new_esc_name = st.text_input(
                    "機種名稱 *", key="esc_new_model_name",
                    placeholder="例：ES2000RX (150A)",
                )
            with _nm2:
                _new_esc_from_default = st.checkbox(
                    "從預設 ESC 共用項目複製（自動帶入 A、B 兩個 Section）",
                    key="esc_new_from_default",
                    value=True,
                )
            if st.button("✅ 建立機種模板", key="esc_new_model_add", type="primary"):
                _nm = _new_esc_name.strip()
                if not _nm:
                    st.warning("機種名稱不可空白")
                elif _nm in esc_templates:
                    st.warning(f"機種「{_nm}」已存在，請直接在下方編輯")
                else:
                    if _new_esc_from_default:
                        _init_secs = _cp.deepcopy(_get_cfg_esc().get("esc_sections", []))
                    else:
                        _init_secs = []
                    from datetime import datetime as _dt
                    _esc_upsert(_nm, _init_secs)
                    st.success(f"✅ 已建立「{_nm}」機種模板")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 各機種模板管理 ───────────────────────────
        if not _esc_model_list:
            st.markdown("""
<div style="background:#fafbfc;border:2px dashed #ddd;border-radius:10px;
            padding:40px;text-align:center;color:#bbb">
  <div style="font-size:32px;margin-bottom:8px">⚡</div>
  <div style="font-size:13px;font-weight:600;color:#aaa">尚無 ESC 機種模板</div>
  <div style="font-size:11px;margin-top:6px">請使用上方「新增全新機種模板」建立第一個機種</div>
</div>
""", unsafe_allow_html=True)

        for _esc_model_key, _esc_tpl in esc_templates.items():
            _esc_secs   = _esc_tpl.get("sections", [])
            _n_items    = sum(len(s.get("items", [])) for s in _esc_secs)
            _updated    = _esc_tpl.get("updated_at", _esc_tpl.get("created_at", "─"))

            with st.expander(
                f"⚡  **{_esc_model_key}**  ·  {len(_esc_secs)} 區段  ·  {_n_items} 項目  ·  更新：{_updated}",
                expanded=False,
            ):
                # 機種操作列
                _op1, _op2 = st.columns([8, 1])
                with _op2:
                    if st.button("🗑️ 刪除", key=f"esc_del_{_esc_model_key}",
                                 help="刪除此機種模板（無法復原）"):
                        if _esc_del_tpl(_esc_model_key):
                            st.success(f"已刪除「{_esc_model_key}」模板")
                            st.rerun()

                # ── 新增 Section ──────────────────────
                with st.expander("➕ 新增檢驗類別（Section）", expanded=False):
                    _sc1, _sc2, _sc3 = st.columns([2, 4, 4])
                    with _sc1:
                        _ns_id  = st.text_input("代號", key=f"esc_ns_id_{_esc_model_key}",
                                                placeholder="C", max_chars=4)
                    with _sc2:
                        _ns_lb  = st.text_input("類別名稱", key=f"esc_ns_lb_{_esc_model_key}",
                                                placeholder="例：電氣安規測試類")
                    with _sc3:
                        _ns_sub = st.text_input("副標題", key=f"esc_ns_sub_{_esc_model_key}",
                                                placeholder="例：高壓安規設備")
                    if st.button("新增類別", key=f"esc_ns_add_{_esc_model_key}", type="primary"):
                        _nid = _ns_id.strip().upper()
                        _existing_ids = [s["id"] for s in _esc_secs]
                        if not _nid or not _ns_lb.strip():
                            st.warning("代號與名稱不可空白")
                        elif _nid in _existing_ids:
                            st.warning(f"代號「{_nid}」已存在")
                        else:
                            _new_tpls = _cp.deepcopy(esc_templates)
                            _new_tpls[_esc_model_key]["sections"].append({
                                "id": _nid, "label": _ns_lb.strip(),
                                "subtitle": _ns_sub.strip(), "items": [],
                            })
                            _new_tpls[_esc_model_key]["updated_at"] = \
                                datetime.now().strftime("%Y-%m-%d %H:%M")
                            _esc_save_tpl(_new_tpls)
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

                # ── 各 Section ────────────────────────
                for _si, _sec in enumerate(_esc_secs):
                    _sec_id    = _sec["id"]
                    _sec_label = _sec["label"]
                    _sec_items = _sec.get("items", [])

                    _sh1, _sh2, _sh3 = st.columns([7, 1, 1])
                    with _sh1:
                        st.markdown(
                            f'<div style="font-size:14px;font-weight:700;color:var(--navy);'
                            f'border-left:4px solid #e67e22;padding-left:10px;margin-bottom:6px">'
                            f'{_sec_id}｜{_sec_label}'
                            f'<span style="font-size:11px;color:var(--muted);margin-left:8px">'
                            f'{_sec.get("subtitle","")}</span></div>',
                            unsafe_allow_html=True,
                        )
                    with _sh2:
                        if not _sec_items:
                            if st.button("刪除", key=f"esc_del_sec_{_esc_model_key}_{_si}",
                                         help="刪除此空白類別"):
                                _new_tpls = _cp.deepcopy(esc_templates)
                                _new_tpls[_esc_model_key]["sections"].pop(_si)
                                _new_tpls[_esc_model_key]["updated_at"] = \
                                    datetime.now().strftime("%Y-%m-%d %H:%M")
                                _esc_save_tpl(_new_tpls)
                                st.rerun()
                        else:
                            st.caption(f"{len(_sec_items)} 項")

                    with st.expander(
                        f"展開 {_sec_id} 的 {len(_sec_items)} 個檢驗項目", expanded=False
                    ):
                        # 現有項目
                        for _ii, _item in enumerate(_sec_items):
                            _itype = _item.get("type", "pf")
                            _gc    = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}.get(
                                _item.get("grade", "MA"), "#888")
                            st.markdown(
                                f'<div style="background:#fafbfc;border:1px solid var(--border);'
                                f'border-left:3px solid {_gc};border-radius:5px;'
                                f'padding:5px 10px;margin-bottom:3px;font-size:11.5px">'
                                f'<span style="background:{_gc};color:#fff;padding:1px 6px;'
                                f'border-radius:3px;font-size:9px;font-weight:800;margin-right:6px">'
                                f'{_item.get("grade","MA")}</span>'
                                f'<b>{_item["name"]}</b>'
                                f'<span style="color:var(--muted);font-size:10.5px;margin-left:8px">'
                                f'規格：{_item["spec"][:40]}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            _ec1, _ec2, _ec3, _ec4 = st.columns([3, 4, 1, 1])
                            with _ec1:
                                _new_name = st.text_input(
                                    "項目名稱",
                                    value=_item["name"],
                                    key=f"esc_ename_{_esc_model_key}_{_si}_{_ii}",
                                    label_visibility="collapsed",
                                )
                            with _ec2:
                                _new_spec = st.text_input(
                                    "規格標準",
                                    value=_item["spec"],
                                    key=f"esc_espec_{_esc_model_key}_{_si}_{_ii}",
                                    label_visibility="collapsed",
                                )
                            with _ec3:
                                if st.button("✏️ 儲存",
                                             key=f"esc_esave_{_esc_model_key}_{_si}_{_ii}",
                                             use_container_width=True):
                                    _new_tpls = _cp.deepcopy(esc_templates)
                                    _tgt = _new_tpls[_esc_model_key]["sections"][_si]["items"][_ii]
                                    _tgt["name"] = _new_name.strip() or _item["name"]
                                    _tgt["spec"] = _new_spec.strip() or _item["spec"]
                                    _new_tpls[_esc_model_key]["updated_at"] = \
                                        datetime.now().strftime("%Y-%m-%d %H:%M")
                                    _esc_save_tpl(_new_tpls)
                                    st.rerun()
                            with _ec4:
                                if st.button("🗑️ 刪除",
                                             key=f"esc_edel_{_esc_model_key}_{_si}_{_ii}",
                                             use_container_width=True):
                                    _new_tpls = _cp.deepcopy(esc_templates)
                                    _new_tpls[_esc_model_key]["sections"][_si]["items"].pop(_ii)
                                    _new_tpls[_esc_model_key]["updated_at"] = \
                                        datetime.now().strftime("%Y-%m-%d %H:%M")
                                    _esc_save_tpl(_new_tpls)
                                    st.rerun()

                            # 數值型項目額外欄位
                            if _itype == "num":
                                _nc1, _nc2, _nc3, _nc4 = st.columns([2, 2, 2, 2])
                                with _nc1:
                                    st.caption(f"單位：{_item.get('unit','')}")
                                with _nc2:
                                    _cur_min = "" if _item.get("min") is None else str(_item["min"])
                                    _new_min = st.text_input(
                                        "最小值",
                                        value=_cur_min,
                                        key=f"esc_emin_{_esc_model_key}_{_si}_{_ii}",
                                        placeholder="無限制",
                                    )
                                with _nc3:
                                    _cur_max = "" if _item.get("max") is None else str(_item["max"])
                                    _new_max = st.text_input(
                                        "最大值",
                                        value=_cur_max,
                                        key=f"esc_emax_{_esc_model_key}_{_si}_{_ii}",
                                        placeholder="無限制",
                                    )
                                with _nc4:
                                    st.caption("")
                                    if st.button("更新範圍",
                                                 key=f"esc_erange_{_esc_model_key}_{_si}_{_ii}"):
                                        _new_tpls = _cp.deepcopy(esc_templates)
                                        _tgt = _new_tpls[_esc_model_key]["sections"][_si]["items"][_ii]
                                        try:
                                            _tgt["min"] = float(_new_min) if _new_min.strip() else None
                                            _tgt["max"] = float(_new_max) if _new_max.strip() else None
                                            _new_tpls[_esc_model_key]["updated_at"] = \
                                                datetime.now().strftime("%Y-%m-%d %H:%M")
                                            _esc_save_tpl(_new_tpls)
                                            st.rerun()
                                        except ValueError:
                                            st.error("最小值/最大值請填入數字")

                            st.markdown("---")

                        # ── 新增項目表單 ─────────────────
                        st.markdown(
                            f'<div style="font-size:12px;font-weight:700;color:#e67e22;'
                            f'margin-bottom:8px">➕ 新增項目至 {_sec_id}｜{_sec_label}</div>',
                            unsafe_allow_html=True,
                        )
                        _f1, _f2, _f3, _f4 = st.columns([3, 4, 1, 1])
                        with _f1:
                            _ni_name = st.text_input(
                                "項目名稱*",
                                key=f"esc_ni_name_{_esc_model_key}_{_si}",
                                placeholder="例：絕緣電阻測試",
                            )
                        with _f2:
                            _ni_spec = st.text_input(
                                "規格標準*",
                                key=f"esc_ni_spec_{_esc_model_key}_{_si}",
                                placeholder="例：≧100 MΩ",
                            )
                        with _f3:
                            _ni_grade = st.selectbox(
                                "等級", ["MA", "CR", "MI"],
                                key=f"esc_ni_grade_{_esc_model_key}_{_si}",
                            )
                        with _f4:
                            _ni_type = st.selectbox(
                                "類型", ["pf（通過/失敗）", "num（數值量測）"],
                                key=f"esc_ni_type_{_esc_model_key}_{_si}",
                            )
                        _ni_tool = st.text_input(
                            "量測工具",
                            key=f"esc_ni_tool_{_esc_model_key}_{_si}",
                            placeholder="例：耐壓測試機",
                        )
                        _type_key = "num" if _ni_type.startswith("num") else "pf"
                        if _type_key == "num":
                            _u1, _u2, _u3 = st.columns(3)
                            with _u1:
                                _ni_unit = st.text_input(
                                    "單位",
                                    key=f"esc_ni_unit_{_esc_model_key}_{_si}",
                                    placeholder="例：MΩ",
                                )
                            with _u2:
                                _ni_min_s = st.text_input(
                                    "最小值（空白=無限制）",
                                    key=f"esc_ni_min_{_esc_model_key}_{_si}",
                                )
                            with _u3:
                                _ni_max_s = st.text_input(
                                    "最大值（空白=無限制）",
                                    key=f"esc_ni_max_{_esc_model_key}_{_si}",
                                )
                        else:
                            _ni_unit = ""; _ni_min_s = ""; _ni_max_s = ""

                        if st.button(
                            "新增項目",
                            key=f"esc_ni_add_{_esc_model_key}_{_si}",
                            type="primary",
                        ):
                            if not _ni_name.strip() or not _ni_spec.strip():
                                st.warning("項目名稱與規格標準不可空白")
                            else:
                                _new_iid  = f"{_sec_id}{len(_sec_items)+1}"
                                _new_no   = f"{len(_sec_items)+1}.0"
                                _new_item = {
                                    "id": _new_iid, "no": _new_no,
                                    "name": _ni_name.strip(),
                                    "spec": _ni_spec.strip(),
                                    "grade": _ni_grade,
                                    "type": _type_key,
                                    "tool": _ni_tool.strip(),
                                }
                                if _type_key == "num":
                                    _new_item["unit"] = _ni_unit.strip()
                                    try:
                                        _new_item["min"] = float(_ni_min_s) if _ni_min_s.strip() else None
                                        _new_item["max"] = float(_ni_max_s) if _ni_max_s.strip() else None
                                    except ValueError:
                                        st.error("最小值/最大值請填入數字")
                                        st.stop()
                                _new_tpls = _cp.deepcopy(esc_templates)
                                _new_tpls[_esc_model_key]["sections"][_si]["items"].append(_new_item)
                                _new_tpls[_esc_model_key]["updated_at"] = \
                                    datetime.now().strftime("%Y-%m-%d %H:%M")
                                _esc_save_tpl(_new_tpls)
                                st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)

        # ── 共用預設項目（always-visible fallback） ──
        st.markdown(
            "<hr style='border:none;border-top:1px solid var(--border);margin:20px 0'>",
            unsafe_allow_html=True,
        )
        with st.expander("⚙️ 共用預設 ESC 檢驗項目（未建立機種模板時使用）", expanded=False):
            st.markdown(
                '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'
                '以下為所有未建立機種模板時使用的共用預設項目，可在「基本設定」→「共用項目」中修改。</div>',
                unsafe_allow_html=True,
            )
            inspection_item_editor("esc", "esc_sections")

    except Exception as _e:
        st.error(f"❌ ESC 模板管理發生錯誤：{_e}")
        import traceback; st.code(traceback.format_exc())

# ───────────────────────────────────────────────────
# TAB 3：馬達 Motor 檢驗項目
# ───────────────────────────────────────────────────
with tab3:
    inspection_item_editor("motor", "motor_sections")


# ───────────────────────────────────────────────────
# TAB 3B：OQC 成檢表模板管理
# ───────────────────────────────────────────────────
with tab3b:
    st.markdown("""
<div style="font-size:12px;color:var(--muted);margin-bottom:14px;
            background:#f7f9fc;border:1px solid var(--border);
            border-left:4px solid #6a1b9a;border-radius:6px;padding:10px 14px">
  管理從 Excel 匯入的 OQC 成檢表模板。模板建立後，「出廠檢驗輸入」→ 馬達 Motor
  頁面選取對應機種時，將自動套用此模板的檢驗項目。<br>
  如需新增模板，請至「<b>📥 文件匯入中心</b> → OQC 成檢表匯入」上傳 Excel。
</div>
""", unsafe_allow_html=True)

    try:
        from utils.oqc_template_db import load_templates, delete_template as _del_tpl, upsert_template
        import copy as _copy_mod

        oqc_templates = load_templates()

        if not oqc_templates:
            st.markdown("""
<div style="background:#fafbfc;border:2px dashed #ddd;border-radius:10px;
            padding:40px;text-align:center;color:#bbb">
  <div style="font-size:32px;margin-bottom:8px">📋</div>
  <div style="font-size:13px;font-weight:600;color:#aaa">尚無 OQC 成檢表模板</div>
  <div style="font-size:11px;margin-top:6px">請先至「文件匯入中心」上傳 Excel 成檢表</div>
</div>
""", unsafe_allow_html=True)
            if st.button("📥 前往文件匯入中心", use_container_width=True, key="goto_import_oqc"):
                st.switch_page("pages/50_📥_文件匯入中心.py")
        else:
            # ── 模板清單 ─────────────────────────────────
            for model_key, tpl in oqc_templates.items():
                sections  = tpl.get("sections", [])
                n_items   = sum(len(s.get("items", [])) for s in sections)
                updated   = tpl.get("updated_at", tpl.get("created_at", "─"))
                doc_no    = tpl.get("doc_no", "─")
                rev       = tpl.get("rev", "─")
                src_file  = tpl.get("source_file", "─")

                with st.expander(
                    f"📋  **{model_key}**  ·  {len(sections)} 區段  ·  {n_items} 項目  ·  更新：{updated}",
                    expanded=False,
                ):
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        st.caption(f"文件編號：{doc_no}")
                        st.caption(f"版次：{rev}")
                    with mc2:
                        st.caption(f"來源檔：{src_file}")
                        st.caption(f"建立：{tpl.get('created_at', '─')}")
                    with mc3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ 刪除此模板", key=f"del_oqc_{model_key}",
                                     help="刪除後無法復原，如需重新使用請再次匯入 Excel"):
                            if _del_tpl(model_key):
                                st.success(f"已刪除「{model_key}」模板")
                                st.rerun()

                    # 展開各 section 預覽
                    for sec in sections:
                        st.markdown(
                            f'<div style="font-size:12px;font-weight:700;color:var(--navy);'
                            f'border-left:3px solid var(--blue2);padding-left:8px;margin:8px 0 4px">'
                            f'{sec["id"]}｜{sec["label"]}</div>',
                            unsafe_allow_html=True,
                        )
                        for it in sec.get("items", []):
                            gc = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}.get(it.get("grade", "MA"), "#888")
                            type_badge = (
                                '<span style="background:#e3f2fd;color:#1565c0;'
                                'padding:1px 6px;border-radius:3px;font-size:9.5px;font-weight:700;margin-right:4px">'
                                f'{"PF" if it["type"]=="pf" else "NUM"}</span>'
                            )
                            st.markdown(
                                f'<div style="background:#fafbfc;border:1px solid var(--border);'
                                f'border-left:3px solid {gc};border-radius:5px;'
                                f'padding:5px 10px;margin-bottom:3px;font-size:11.5px">'
                                f'{type_badge}'
                                f'<span style="background:{gc};color:#fff;padding:1px 6px;'
                                f'border-radius:3px;font-size:9px;font-weight:800;margin-right:6px">'
                                f'{it.get("grade","MA")}</span>'
                                f'<b>{it["name"][:40]}</b>'
                                f'<span style="color:var(--muted);font-size:10.5px;margin-left:8px">'
                                f'規格：{it["spec"][:25]}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📥 前往文件匯入中心（新增模板）", use_container_width=True, key="goto_import_oqc2"):
                st.switch_page("pages/50_📥_文件匯入中心.py")

    except ImportError:
        st.error("❌ 缺少 utils/oqc_template_db.py，請確認檔案存在。")
    except Exception as _e:
        st.error(f"❌ 模板管理發生錯誤：{_e}")


# ───────────────────────────────────────────────────
# TAB 4：IQC 零件庫管理
# ───────────────────────────────────────────────────
with tab4:
    st.markdown("""
<div style="font-size:12px;color:var(--muted);margin-bottom:14px;
            background:#f7f9fc;border:1px solid var(--border);
            border-left:4px solid #1565c0;border-radius:6px;padding:10px 14px">
  管理 IQC 進料檢驗零件庫：新增 / 修改零件基本資料、檢驗 Section、檢驗項目與量測欄位
</div>
""", unsafe_allow_html=True)

    iqc_parts = get_parts()

    def _iqc_save(new_parts):
        save_parts(new_parts)
        st.rerun()

    # ── 從現有零件複製新增 ──────────────────────
    if iqc_parts:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);margin-bottom:6px">'
            '📋 快速複製現有零件作為新零件的起點：</div>',
            unsafe_allow_html=True,
        )
        copy_options = {f"{p.get('icon','📦')} {p['name']}  ({p['id']})": i
                        for i, p in enumerate(iqc_parts)}
        cc1, cc2 = st.columns([5, 1])
        with cc1:
            copy_sel = st.selectbox(
                "選擇來源零件",
                options=list(copy_options.keys()),
                key="iqc_copy_sel",
                label_visibility="collapsed",
            )
        with cc2:
            if st.button("🔁 複製此零件", use_container_width=True, key="iqc_do_copy"):
                src_idx  = copy_options[copy_sel]
                new_p    = copy.deepcopy(iqc_parts[src_idx])
                base_id  = new_p["id"]
                existing = {p["id"] for p in iqc_parts}
                suffix   = "-COPY"
                n = 2
                while (base_id + suffix) in existing:
                    suffix = f"-COPY{n}"; n += 1
                new_p["id"]   = base_id + suffix
                new_p["name"] = "（複製）" + new_p["name"]
                _iqc_save(iqc_parts + [new_p])

        st.markdown(
            "<hr style='border:none;border-top:1px solid var(--border);margin:10px 0'>",
            unsafe_allow_html=True,
        )

    # ── 新增全新零件 ────────────────────────────
    with st.expander("➕ 新增全新零件", expanded=False):
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            np_group  = st.text_input("群組", key="np_group", placeholder="例：機構件")
            np_id     = st.text_input("零件ID*", key="np_id", placeholder="例：PJ2-COVER")
        with pc2:
            np_name   = st.text_input("零件名稱*", key="np_name", placeholder="例：上蓋")
            np_pn     = st.text_input("料號", key="np_pn", placeholder="例：1332-000-00099")
        with pc3:
            np_vendor = st.text_input("供應商", key="np_vendor", placeholder="例：志泰")
            np_machine= st.text_input("機種", key="np_machine", placeholder="例：PJ2 GPS")
        pc4, pc5, pc6 = st.columns(3)
        with pc4:
            np_doc    = st.text_input("文件編號", key="np_doc", placeholder="ISO-QC3006-XX")
        with pc5:
            np_std    = st.text_input("抽樣標準", key="np_std", placeholder="MIL-STD-105E S-4")
        with pc6:
            np_icon   = st.text_input("圖示(emoji)", key="np_icon", placeholder="🔩", max_chars=4)
        aql_c1, aql_c2, aql_c3 = st.columns(3)
        with aql_c1:
            np_aql_cr = st.number_input("AQL CR", value=0.0, step=0.1, format="%.2f", key="np_aql_cr")
        with aql_c2:
            np_aql_ma = st.number_input("AQL MA", value=0.65, step=0.05, format="%.2f", key="np_aql_ma")
        with aql_c3:
            np_aql_mi = st.number_input("AQL MI", value=1.5,  step=0.1,  format="%.2f", key="np_aql_mi")
        np_alert = st.text_area("警示文字", key="np_alert", height=60, placeholder="前批病歷說明…")

        if st.button("✅ 新增零件", key="np_add", type="primary"):
            pid = np_id.strip().upper()
            if not pid or not np_name.strip():
                st.warning("零件ID 與名稱不可空白")
            elif any(p["id"] == pid for p in iqc_parts):
                st.warning(f"零件ID「{pid}」已存在")
            else:
                new_p = {
                    "group": np_group.strip() or "其他",
                    "id": pid,
                    "name": np_name.strip(),
                    "pn": np_pn.strip(),
                    "machine": np_machine.strip(),
                    "vendor": np_vendor.strip(),
                    "icon": np_icon.strip() or "📦",
                    "docNo": np_doc.strip(),
                    "samplingStd": np_std.strip(),
                    "aql": {"cr": np_aql_cr, "ma": np_aql_ma, "mi": np_aql_mi},
                    "alert": np_alert.strip(),
                    "sections": [],
                }
                _iqc_save(iqc_parts + [new_p])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 各零件管理 ───────────────────────────────
    for p_idx, p in enumerate(iqc_parts):
        with st.expander(
            f"{p.get('icon','📦')}  {p['name']}  ·  {p['pn']}  ·  {p.get('group','')}",
            expanded=False,
        ):
            # ── 基本資料編輯 ────────────────────
            st.markdown(
                '<div style="font-size:11.5px;font-weight:700;color:var(--blue2);'
                'margin-bottom:8px">基本資料</div>',
                unsafe_allow_html=True,
            )
            bi1, bi2, bi3 = st.columns(3)
            with bi1:
                e_name   = st.text_input("零件名稱", value=p["name"],
                                         key=f"e_name_{p_idx}")
                e_pn     = st.text_input("料號",     value=p.get("pn",""),
                                         key=f"e_pn_{p_idx}")
            with bi2:
                e_vendor = st.text_input("供應商",   value=p.get("vendor",""),
                                         key=f"e_vendor_{p_idx}")
                e_machine= st.text_input("機種",     value=p.get("machine",""),
                                         key=f"e_machine_{p_idx}")
            with bi3:
                e_doc    = st.text_input("文件編號", value=p.get("docNo",""),
                                         key=f"e_doc_{p_idx}")
                e_std    = st.text_input("抽樣標準", value=p.get("samplingStd",""),
                                         key=f"e_std_{p_idx}")
            e_alert = st.text_input("警示文字", value=p.get("alert",""),
                                    key=f"e_alert_{p_idx}")
            bc1, bc2, bc3 = st.columns([4, 1, 1])
            with bc1:
                if st.button("💾 儲存基本資料", key=f"e_save_{p_idx}"):
                    new_parts = copy.deepcopy(iqc_parts)
                    new_parts[p_idx].update({
                        "name": e_name.strip() or p["name"],
                        "pn": e_pn.strip(),
                        "vendor": e_vendor.strip(),
                        "machine": e_machine.strip(),
                        "docNo": e_doc.strip(),
                        "samplingStd": e_std.strip(),
                        "alert": e_alert.strip(),
                    })
                    _iqc_save(new_parts)
            with bc2:
                if st.button("🔁 複製", key=f"e_copy_{p_idx}",
                             help="複製此零件（含所有檢驗項目）作為新零件"):
                    new_p   = copy.deepcopy(p)
                    base_id = p["id"]
                    existing = {pp["id"] for pp in iqc_parts}
                    suffix = "-COPY"; n = 2
                    while (base_id + suffix) in existing:
                        suffix = f"-COPY{n}"; n += 1
                    new_p["id"]   = base_id + suffix
                    new_p["name"] = "（複製）" + p["name"]
                    _iqc_save(iqc_parts + [new_p])
            with bc3:
                if st.button("🗑️ 刪除", key=f"e_del_{p_idx}",
                             help="刪除此零件（無法復原）"):
                    new_parts = copy.deepcopy(iqc_parts)
                    new_parts.pop(p_idx)
                    _iqc_save(new_parts)

            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:10px 0'>",
                unsafe_allow_html=True,
            )

            # ── 新增 Section ────────────────────
            st.markdown(
                '<div style="font-size:11.5px;font-weight:700;color:var(--blue2);'
                'margin-bottom:8px">檢驗類別 (Sections)</div>',
                unsafe_allow_html=True,
            )
            with st.expander("➕ 新增檢驗類別", expanded=False):
                ns1, ns2, ns3 = st.columns(3)
                with ns1:
                    ns_id  = st.text_input("類別代號", key=f"ns_id_{p_idx}",
                                           placeholder="例：dim")
                with ns2:
                    ns_lb  = st.text_input("類別名稱", key=f"ns_lb_{p_idx}",
                                           placeholder="例：尺寸規格檢驗")
                with ns3:
                    ns_sub = st.text_input("副標題",   key=f"ns_sub_{p_idx}",
                                           placeholder="例：量測工具：游標卡尺")
                if st.button("新增類別", key=f"ns_add_{p_idx}", type="primary"):
                    if not ns_id.strip() or not ns_lb.strip():
                        st.warning("代號與名稱不可空白")
                    else:
                        new_parts = copy.deepcopy(iqc_parts)
                        new_parts[p_idx]["sections"].append({
                            "id": ns_id.strip(),
                            "label": ns_lb.strip(),
                            "sublabel": ns_sub.strip(),
                            "items": [],
                        })
                        _iqc_save(new_parts)

            # ── 各 Section ──────────────────────
            for s_idx, sec in enumerate(p.get("sections", [])):
                sec_items = sec.get("items", [])
                with st.expander(
                    f"  {sec.get('id','')}｜{sec['label']}  ({len(sec_items)} 項)",
                    expanded=False,
                ):
                    # Section 標題編輯
                    sl1, sl2, sl3, sl4 = st.columns([2, 3, 3, 1])
                    with sl1:
                        e_sid = st.text_input("代號", value=sec.get("id",""),
                                              key=f"e_sid_{p_idx}_{s_idx}")
                    with sl2:
                        e_slb = st.text_input("名稱", value=sec["label"],
                                              key=f"e_slb_{p_idx}_{s_idx}")
                    with sl3:
                        e_sub = st.text_input("副標題", value=sec.get("sublabel",""),
                                              key=f"e_sub_{p_idx}_{s_idx}")
                    with sl4:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾", key=f"s_save_{p_idx}_{s_idx}",
                                     help="儲存類別標題"):
                            new_parts = copy.deepcopy(iqc_parts)
                            new_parts[p_idx]["sections"][s_idx].update({
                                "id": e_sid.strip() or sec.get("id",""),
                                "label": e_slb.strip() or sec["label"],
                                "sublabel": e_sub.strip(),
                            })
                            _iqc_save(new_parts)

                    if not sec_items:
                        if st.button("🗑️ 刪除此空白類別",
                                     key=f"s_del_{p_idx}_{s_idx}"):
                            new_parts = copy.deepcopy(iqc_parts)
                            new_parts[p_idx]["sections"].pop(s_idx)
                            _iqc_save(new_parts)

                    # 現有項目
                    for i_idx, item in enumerate(sec_items):
                        _gc = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}.get(
                            item.get("grade", "MA"), "#888")
                        st.markdown(
                            f'<div style="background:#fafbfc;border:1px solid var(--border);'
                            f'border-left:3px solid {_gc};border-radius:6px;'
                            f'padding:8px 12px;margin-bottom:4px">'
                            f'<span style="background:{_gc};color:#fff;padding:1px 7px;'
                            f'border-radius:4px;font-size:9.5px;font-weight:800;margin-right:8px">'
                            f'{item.get("grade","MA")}</span>'
                            f'<b>{item["name"]}</b>  '
                            f'<span style="color:var(--muted);font-size:11px">{item["spec"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        ic1, ic2, ic3, ic4 = st.columns([3, 4, 1, 1])
                        with ic1:
                            e_iname = st.text_input(
                                "項目名稱", value=item["name"],
                                key=f"e_iname_{p_idx}_{s_idx}_{i_idx}",
                                label_visibility="collapsed")
                        with ic2:
                            e_ispec = st.text_input(
                                "規格", value=item["spec"],
                                key=f"e_ispec_{p_idx}_{s_idx}_{i_idx}",
                                label_visibility="collapsed")
                        with ic3:
                            if st.button("💾", key=f"i_save_{p_idx}_{s_idx}_{i_idx}",
                                         use_container_width=True):
                                new_parts = copy.deepcopy(iqc_parts)
                                new_parts[p_idx]["sections"][s_idx]["items"][i_idx]["name"] = \
                                    e_iname.strip() or item["name"]
                                new_parts[p_idx]["sections"][s_idx]["items"][i_idx]["spec"] = \
                                    e_ispec.strip() or item["spec"]
                                _iqc_save(new_parts)
                        with ic4:
                            if st.button("🗑️", key=f"i_del_{p_idx}_{s_idx}_{i_idx}",
                                         use_container_width=True):
                                new_parts = copy.deepcopy(iqc_parts)
                                new_parts[p_idx]["sections"][s_idx]["items"].pop(i_idx)
                                _iqc_save(new_parts)

                        # Inputs 管理（量測欄位）
                        inp_defs = item.get("inputs", [])
                        if inp_defs:
                            st.markdown(
                                '<div style="font-size:10px;color:var(--muted);'
                                'margin:2px 0 4px 4px">量測欄位：' +
                                " ｜ ".join(
                                    f'{ip["label"]}({ip["unit"]})'
                                    f'{"  " + str(ip.get("min","")) + "~" + str(ip.get("max","")) if ip.get("min") is not None else ""}'
                                    for ip in inp_defs
                                ) + '</div>',
                                unsafe_allow_html=True,
                            )
                            # 刪除某個 input
                            for ip_idx, ip in enumerate(inp_defs):
                                ipc1, ipc2 = st.columns([8, 1])
                                with ipc1:
                                    st.caption(
                                        f"　key={ip['key']}  label={ip['label']}"
                                        f"  unit={ip['unit']}"
                                        f"  min={ip.get('min','-')}  max={ip.get('max','-')}"
                                    )
                                with ipc2:
                                    if st.button("✕", key=f"ip_del_{p_idx}_{s_idx}_{i_idx}_{ip_idx}",
                                                 help="刪除此量測欄位"):
                                        new_parts = copy.deepcopy(iqc_parts)
                                        new_parts[p_idx]["sections"][s_idx]["items"][i_idx]["inputs"].pop(ip_idx)
                                        _iqc_save(new_parts)

                        # 新增 input
                        with st.expander(f"  ＋ 新增量測欄位",
                                         expanded=False):
                            ip1, ip2, ip3 = st.columns(3)
                            with ip1:
                                new_ip_key   = st.text_input(
                                    "key(英文)",
                                    key=f"nip_key_{p_idx}_{s_idx}_{i_idx}",
                                    placeholder="例：d1")
                                new_ip_label = st.text_input(
                                    "標籤",
                                    key=f"nip_lbl_{p_idx}_{s_idx}_{i_idx}",
                                    placeholder="例：量測值 #1")
                            with ip2:
                                new_ip_unit  = st.text_input(
                                    "單位",
                                    key=f"nip_unt_{p_idx}_{s_idx}_{i_idx}",
                                    placeholder="例：mm")
                                new_ip_min   = st.text_input(
                                    "最小值(空白=無)",
                                    key=f"nip_min_{p_idx}_{s_idx}_{i_idx}")
                            with ip3:
                                new_ip_max   = st.text_input(
                                    "最大值(空白=無)",
                                    key=f"nip_max_{p_idx}_{s_idx}_{i_idx}")
                                new_ip_af    = st.checkbox(
                                    "autoFail（超出範圍自動判NG）",
                                    key=f"nip_af_{p_idx}_{s_idx}_{i_idx}")
                            if st.button("新增量測欄位",
                                         key=f"nip_add_{p_idx}_{s_idx}_{i_idx}",
                                         type="primary"):
                                k = new_ip_key.strip()
                                if not k or not new_ip_label.strip():
                                    st.warning("key 與標籤不可空白")
                                else:
                                    new_inp = {
                                        "key": k, "label": new_ip_label.strip(),
                                        "unit": new_ip_unit.strip(),
                                    }
                                    try:
                                        if new_ip_min.strip():
                                            new_inp["min"] = float(new_ip_min)
                                        if new_ip_max.strip():
                                            new_inp["max"] = float(new_ip_max)
                                    except ValueError:
                                        st.error("最小/最大值請填數字")
                                        st.stop()
                                    new_parts = copy.deepcopy(iqc_parts)
                                    new_parts[p_idx]["sections"][s_idx]["items"][i_idx]["inputs"].append(new_inp)
                                    if new_ip_af:
                                        new_parts[p_idx]["sections"][s_idx]["items"][i_idx]["autoFail"] = True
                                    _iqc_save(new_parts)

                        st.markdown(
                            "<div style='height:4px'></div>", unsafe_allow_html=True
                        )

                    # 新增項目表單
                    st.markdown("---")
                    st.markdown(
                        f'<div style="font-size:11px;font-weight:700;'
                        f'color:var(--blue2);margin-bottom:6px">'
                        f'➕ 新增項目至「{sec["label"]}」</div>',
                        unsafe_allow_html=True,
                    )
                    ni1, ni2, ni3, ni4 = st.columns([3, 4, 1, 1])
                    with ni1:
                        ni_name  = st.text_input(
                            "項目名稱*",
                            key=f"ni_name_{p_idx}_{s_idx}", placeholder="例：孔徑尺寸")
                    with ni2:
                        ni_spec  = st.text_input(
                            "規格標準*",
                            key=f"ni_spec_{p_idx}_{s_idx}", placeholder="例：φ 2.2mm ± 0.05mm")
                    with ni3:
                        ni_grade = st.selectbox(
                            "等級", ["MA", "CR", "MI"],
                            key=f"ni_grade_{p_idx}_{s_idx}")
                    with ni4:
                        ni_af    = st.checkbox(
                            "autoFail",
                            key=f"ni_af_{p_idx}_{s_idx}",
                            help="有量測欄位且超出範圍時自動判 NG")
                    ni_tool   = st.text_input(
                        "量測工具",
                        key=f"ni_tool_{p_idx}_{s_idx}", placeholder="例：游標卡尺")
                    ni_detail = st.text_input(
                        "規格補充說明",
                        key=f"ni_det_{p_idx}_{s_idx}", placeholder="例：允許範圍 2.15~2.25mm")
                    ni_alert_t= st.text_input(
                        "項目警示",
                        key=f"ni_alert_{p_idx}_{s_idx}", placeholder="例：前批病歷說明")

                    if st.button("新增項目", key=f"ni_add_{p_idx}_{s_idx}",
                                 type="primary"):
                        if not ni_name.strip() or not ni_spec.strip():
                            st.warning("項目名稱與規格不可空白")
                        else:
                            # 計算新 id（全零件最大 id + 1）
                            all_existing_ids = [
                                it["id"]
                                for s in p.get("sections", [])
                                for it in s.get("items", [])
                                if isinstance(it.get("id"), int)
                            ]
                            new_id = (max(all_existing_ids) + 1) if all_existing_ids else 1
                            new_item = {
                                "id": new_id,
                                "grade": ni_grade,
                                "name": ni_name.strip(),
                                "spec": ni_spec.strip(),
                                "specDetail": ni_detail.strip(),
                                "tool": ni_tool.strip(),
                                "alert": ni_alert_t.strip(),
                                "autoFail": ni_af,
                                "inputs": [],
                            }
                            new_parts = copy.deepcopy(iqc_parts)
                            new_parts[p_idx]["sections"][s_idx]["items"].append(new_item)
                            _iqc_save(new_parts)

        st.markdown("<br>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────
# TAB 5：登入設定（免登入模式 / 存取控制）
# ───────────────────────────────────────────────────
with tab5:
    st.markdown("""
<div style="font-size:12px;color:var(--muted);margin-bottom:14px;
            background:#fff8e1;border:1px solid #ffe082;
            border-left:4px solid #f0a500;border-radius:8px;padding:12px 16px">
  ⚠️ 此頁面設定影響所有使用者的存取方式，請謹慎操作。
</div>
""", unsafe_allow_html=True)

    # ── 免登入模式 ──────────────────────────────────
    st.markdown('<div class="set-label">🔓 免登入模式</div>', unsafe_allow_html=True)

    auto_admin = get_auto_login_admin()
    is_auto    = bool(auto_admin)

    st.markdown(f"""
<div style="background:#fff;border:1px solid var(--border);border-radius:8px;
            padding:16px 18px;margin-bottom:14px;box-shadow:var(--sh)">
  <div style="font-size:12.5px;color:var(--text);margin-bottom:8px">
    目前狀態：{"<b style='color:#e74c3c'>⚠️ 免登入模式已開啟</b> — 任何人打開系統都不需要輸入帳號密碼" if is_auto else "<b style='color:#27ae60'>✅ 需要登入</b> — 每位使用者必須輸入帳號與密碼"}
  </div>
  {"<div style='font-size:11.5px;color:#e74c3c;background:#fdedec;border:1px solid #f5b7b1;border-radius:6px;padding:8px 12px'>目前自動以 <b>" + auto_admin + "</b> 帳號免登入，所有人均可直接存取全部功能。<br>若系統開放給同事或對外分享，建議立即關閉。</div>" if is_auto else ""}
</div>
""", unsafe_allow_html=True)

    col_on, col_off = st.columns(2)
    with col_on:
        # 選擇哪個 admin 帳號作為免登入帳號
        admin_users = [u["username"] for u in get_all_users()
                       if u["role"] == "admin" and u["status"] == "active"]
        sel_admin = st.selectbox(
            "選擇免登入管理員帳號",
            admin_users,
            index=admin_users.index(auto_admin) if auto_admin in admin_users else 0,
            key="auto_login_sel",
            disabled=(len(admin_users) == 0),
        )
        if st.button("🔓 開啟免登入", use_container_width=True,
                     disabled=(len(admin_users) == 0),
                     help="開啟後任何人打開系統都不需要登入"):
            set_auto_login_admin(sel_admin)
            st.success(f"✅ 已開啟免登入模式（{sel_admin}）")
            st.rerun()

    with col_off:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 關閉免登入（強制登入）", use_container_width=True,
                     type="primary" if is_auto else "secondary",
                     help="關閉後所有人必須輸入帳號密碼才能進入系統"):
            set_auto_login_admin("")
            st.success("✅ 已關閉免登入，所有使用者需要輸入帳號密碼登入")
            st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:16px 0'>",
                unsafe_allow_html=True)

    # ── 說明 ─────────────────────────────────────────
    st.markdown('<div class="set-label">💡 使用說明</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#fff;border:1px solid var(--border);border-radius:8px;
            padding:16px 18px;box-shadow:var(--sh);font-size:12.5px;
            color:var(--text);line-height:2">
  <b>🔒 需要登入模式（建議）</b><br>
  &nbsp;&nbsp;&nbsp;• 每位使用者必須輸入自己的帳號密碼<br>
  &nbsp;&nbsp;&nbsp;• 系統會記錄是哪位檢驗員操作<br>
  &nbsp;&nbsp;&nbsp;• 適合多人共用、對外分享的情況<br>
  <br>
  <b>🔓 免登入模式</b><br>
  &nbsp;&nbsp;&nbsp;• 打開系統即自動以指定管理員帳號登入<br>
  &nbsp;&nbsp;&nbsp;• 適合只有您一個人使用、不對外分享的情況<br>
  &nbsp;&nbsp;&nbsp;• 系統初次設定時預設為此模式<br>
  <br>
  <b>👥 新增同事帳號</b> → 請前往「<a href="/04_帳號管理" target="_self">帳號管理</a>」頁面
</div>
""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────
# TAB 6：IPQC 巡檢設定
# ───────────────────────────────────────────────────
with tab6:
    st.markdown("""
<div style="font-size:12px;color:var(--muted);margin-bottom:14px;
            background:#f7f9fc;border:1px solid var(--border);
            border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px">
  管理 IPQC 製程巡檢機種：新增機種、設定巡檢工序與檢查項目、設定首台FAI確認項目。
  完成後可至「📋 IPQC 巡檢」頁面填寫表單並生成PDF。
</div>
""", unsafe_allow_html=True)

    ipqc_cfg = ipqc_load()
    ipqc_model_list = ipqc_cfg.get("models", [])

    def _ipqc_save_rerun(new_cfg):
        ipqc_save(new_cfg)
        st.rerun()

    # ── 新增機種 ─────────────────────────────────────
    with st.expander("➕ 新增巡檢機種", expanded=False):
        nc1, nc2, nc3, nc4 = st.columns([2, 2, 2, 2])
        with nc1:
            new_mid   = st.text_input("機種ID*（英數字底線）", key="ni_mid",
                                      placeholder="例：PJ3_UHF")
        with nc2:
            new_mname = st.text_input("機種名稱*", key="ni_mname",
                                      placeholder="例：PJ3 UHF")
        with nc3:
            new_docno = st.text_input("文件編號", key="ni_docno",
                                      placeholder="例：PJ3-QC-PR3005")
        with nc4:
            new_freq  = st.text_input("巡查頻率", key="ni_freq",
                                      value="每4小時巡查1次")
        nv1, nv2 = st.columns(2)
        with nv1:
            new_ver  = st.text_input("版本", key="ni_ver", value="V1.0")
        with nv2:
            new_rel  = st.text_input("版次日期", key="ni_rel", placeholder="例：2026/05/13")
        if st.button("✅ 新增機種", key="ni_add_model", type="primary"):
            mid = new_mid.strip().upper().replace(" ", "_")
            if not mid or not new_mname.strip():
                st.warning("機種ID 與名稱不可空白")
            elif any(m["id"] == mid for m in ipqc_model_list):
                st.warning(f"機種ID「{mid}」已存在")
            else:
                new_cfg = copy.deepcopy(ipqc_cfg)
                new_cfg["models"].append({
                    "id": mid,
                    "name": new_mname.strip(),
                    "doc_no": new_docno.strip(),
                    "version": new_ver.strip() or "V1.0",
                    "released": new_rel.strip(),
                    "inspection_freq": new_freq.strip() or "每4小時巡查1次",
                    "patrol_stations": [],
                    "fai_stations": [],
                })
                _ipqc_save_rerun(new_cfg)

    # ── 複製機種 ───────────────────────────────────────
    if ipqc_model_list:
        with st.expander("🔁 複製現有機種（快速建立新機種）", expanded=False):
            copy_opts = {f"{m['name']} ({m['id']})": i for i, m in enumerate(ipqc_model_list)}
            cp1, cp2 = st.columns([5, 1])
            with cp1:
                cp_sel = st.selectbox("選擇來源機種", list(copy_opts.keys()),
                                      key="ipqc_copy_sel", label_visibility="collapsed")
            with cp2:
                if st.button("🔁 複製", use_container_width=True, key="ipqc_do_copy"):
                    src = copy.deepcopy(ipqc_model_list[copy_opts[cp_sel]])
                    base = src["id"]
                    existing = {m["id"] for m in ipqc_model_list}
                    suffix = "-COPY"; n2 = 2
                    while (base + suffix) in existing:
                        suffix = f"-COPY{n2}"; n2 += 1
                    src["id"]   = base + suffix
                    src["name"] = "（複製）" + src["name"]
                    new_cfg = copy.deepcopy(ipqc_cfg)
                    new_cfg["models"].append(src)
                    _ipqc_save_rerun(new_cfg)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 各機種管理 ────────────────────────────────────
    GRADE_OPTIONS = ["CR", "MA", "MI"]

    for m_idx, mdl in enumerate(ipqc_model_list):
        mid   = mdl["id"]
        mname = mdl["name"]

        with st.expander(f"**{mname}**　({mid})  ·  {mdl.get('doc_no','')}  {mdl.get('version','')}",
                         expanded=False):

            # ── 基本資料 ────────────────────────────
            st.markdown('<div style="font-size:11.5px;font-weight:700;color:var(--blue2);'
                        'margin-bottom:8px">基本資料</div>', unsafe_allow_html=True)
            bi1, bi2, bi3 = st.columns(3)
            with bi1:
                e_name = st.text_input("機種名稱", value=mname,   key=f"ipqc_name_{m_idx}")
                e_doc  = st.text_input("文件編號", value=mdl.get("doc_no",""), key=f"ipqc_doc_{m_idx}")
            with bi2:
                e_ver  = st.text_input("版本",     value=mdl.get("version",""),  key=f"ipqc_ver_{m_idx}")
                e_rel  = st.text_input("版次日期", value=mdl.get("released",""), key=f"ipqc_rel_{m_idx}")
            with bi3:
                e_freq = st.text_input("巡查頻率", value=mdl.get("inspection_freq",""), key=f"ipqc_freq_{m_idx}")
            bic1, bic2 = st.columns([3, 1])
            with bic1:
                if st.button("💾 儲存基本資料", key=f"ipqc_save_meta_{m_idx}"):
                    new_cfg = copy.deepcopy(ipqc_cfg)
                    new_cfg["models"][m_idx].update({
                        "name": e_name.strip() or mname,
                        "doc_no": e_doc.strip(),
                        "version": e_ver.strip(),
                        "released": e_rel.strip(),
                        "inspection_freq": e_freq.strip(),
                    })
                    _ipqc_save_rerun(new_cfg)
            with bic2:
                if st.button("🗑️ 刪除機種", key=f"ipqc_del_{m_idx}",
                             help="刪除此機種（含所有工序與項目，無法復原）"):
                    new_cfg = copy.deepcopy(ipqc_cfg)
                    new_cfg["models"].pop(m_idx)
                    _ipqc_save_rerun(new_cfg)

            st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:10px 0'>",
                        unsafe_allow_html=True)

            # ── 巡檢工序管理 ────────────────────────
            for stype, stype_label, stype_icon in [
                ("patrol_stations", "製程巡檢工序", "📋"),
                ("fai_stations",    "首台FAI確認工序", "🔬"),
            ]:
                stations = mdl.get(stype, [])
                st.markdown(
                    f'<div style="font-size:12px;font-weight:700;color:var(--navy);'
                    f'margin:12px 0 8px">{stype_icon} {stype_label}（{len(stations)} 個工序）</div>',
                    unsafe_allow_html=True,
                )

                # 新增工序
                with st.expander(f"➕ 新增 {stype_label} 工序", expanded=False):
                    as1, as2 = st.columns(2)
                    with as1:
                        ns_id   = st.text_input("工序ID*", key=f"ns_id_{m_idx}_{stype}",
                                                placeholder="例：ST-12")
                    with as2:
                        ns_name = st.text_input("工序名稱*", key=f"ns_nm_{m_idx}_{stype}",
                                                placeholder="例：總裝")
                    if st.button("新增工序", key=f"ns_add_{m_idx}_{stype}", type="primary"):
                        sid = ns_id.strip()
                        if not sid or not ns_name.strip():
                            st.warning("工序ID 與名稱不可空白")
                        elif any(s["id"] == sid for s in stations):
                            st.warning(f"工序「{sid}」已存在")
                        else:
                            new_cfg = copy.deepcopy(ipqc_cfg)
                            new_item_template = {"item": "", "grade": "MA"} if stype == "patrol_stations" \
                                                else {"item": "", "criteria": ""}
                            new_cfg["models"][m_idx][stype].append({
                                "id": sid, "name": ns_name.strip(), "items": []
                            })
                            _ipqc_save_rerun(new_cfg)

                # 各工序展開
                for s_idx, station in enumerate(stations):
                    s_id   = station["id"]
                    s_name = station["name"]
                    s_items = station.get("items", [])

                    with st.expander(
                        f"  {s_id}｜{s_name}  ({len(s_items)} 項)",
                        expanded=False,
                    ):
                        # 工序標題編輯
                        sh1, sh2, sh3 = st.columns([2, 3, 1])
                        with sh1:
                            e_sid  = st.text_input("工序ID", value=s_id,
                                                   key=f"e_sid_{m_idx}_{stype}_{s_idx}")
                        with sh2:
                            e_snm  = st.text_input("工序名稱", value=s_name,
                                                   key=f"e_snm_{m_idx}_{stype}_{s_idx}")
                        with sh3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("💾", key=f"s_sv_{m_idx}_{stype}_{s_idx}",
                                         help="儲存工序標題"):
                                new_cfg = copy.deepcopy(ipqc_cfg)
                                new_cfg["models"][m_idx][stype][s_idx].update({
                                    "id": e_sid.strip() or s_id,
                                    "name": e_snm.strip() or s_name,
                                })
                                _ipqc_save_rerun(new_cfg)

                        if not s_items:
                            if st.button("🗑️ 刪除此空白工序",
                                         key=f"s_del_{m_idx}_{stype}_{s_idx}"):
                                new_cfg = copy.deepcopy(ipqc_cfg)
                                new_cfg["models"][m_idx][stype].pop(s_idx)
                                _ipqc_save_rerun(new_cfg)

                        # 現有項目
                        for i_idx, item in enumerate(s_items):
                            gc = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}.get(
                                item.get("grade", "MA"), "#888")
                            grade_badge = (
                                f'<span style="background:{gc};color:#fff;padding:1px 7px;'
                                f'border-radius:4px;font-size:9.5px;font-weight:800;margin-right:8px">'
                                f'{item.get("grade","─")}</span>'
                            ) if stype == "patrol_stations" else ""
                            st.markdown(
                                f'<div style="background:#fafbfc;border:1px solid var(--border);'
                                f'border-radius:6px;padding:7px 12px;margin-bottom:4px">'
                                f'{grade_badge}<b>{item["item"]}</b>'
                                + (f'  <span style="color:var(--muted);font-size:11px">{item.get("criteria","")}</span>'
                                   if stype == "fai_stations" else "")
                                + '</div>',
                                unsafe_allow_html=True,
                            )
                            ic1, ic2, ic3, ic4 = st.columns([3, 3, 1, 1])
                            with ic1:
                                e_item = st.text_input(
                                    "檢查項目", value=item["item"],
                                    key=f"e_itm_{m_idx}_{stype}_{s_idx}_{i_idx}",
                                    label_visibility="collapsed")
                            with ic2:
                                if stype == "patrol_stations":
                                    e_grade = st.selectbox(
                                        "等級", GRADE_OPTIONS,
                                        index=GRADE_OPTIONS.index(item.get("grade","MA")),
                                        key=f"e_grd_{m_idx}_{stype}_{s_idx}_{i_idx}",
                                        label_visibility="collapsed")
                                else:
                                    e_crit = st.text_input(
                                        "判定基準", value=item.get("criteria",""),
                                        key=f"e_crt_{m_idx}_{stype}_{s_idx}_{i_idx}",
                                        label_visibility="collapsed")
                            with ic3:
                                if st.button("💾", key=f"i_sv_{m_idx}_{stype}_{s_idx}_{i_idx}",
                                             use_container_width=True):
                                    new_cfg = copy.deepcopy(ipqc_cfg)
                                    tgt = new_cfg["models"][m_idx][stype][s_idx]["items"][i_idx]
                                    tgt["item"] = e_item.strip() or item["item"]
                                    if stype == "patrol_stations":
                                        tgt["grade"] = e_grade
                                    else:
                                        tgt["criteria"] = e_crit.strip()
                                    _ipqc_save_rerun(new_cfg)
                            with ic4:
                                if st.button("🗑️", key=f"i_dl_{m_idx}_{stype}_{s_idx}_{i_idx}",
                                             use_container_width=True):
                                    new_cfg = copy.deepcopy(ipqc_cfg)
                                    new_cfg["models"][m_idx][stype][s_idx]["items"].pop(i_idx)
                                    _ipqc_save_rerun(new_cfg)

                        # 新增項目
                        st.markdown("---")
                        st.markdown(
                            f'<div style="font-size:11px;font-weight:700;color:var(--blue2);'
                            f'margin-bottom:6px">➕ 新增項目至 {s_id}｜{s_name}</div>',
                            unsafe_allow_html=True,
                        )
                        na1, na2, na3 = st.columns([4, 2, 1])
                        with na1:
                            ni_item = st.text_input(
                                "檢查項目*", key=f"ni_itm_{m_idx}_{stype}_{s_idx}",
                                placeholder="例：確認零件外觀無損傷")
                        with na2:
                            if stype == "patrol_stations":
                                ni_grade = st.selectbox(
                                    "等級", GRADE_OPTIONS,
                                    key=f"ni_grd_{m_idx}_{stype}_{s_idx}")
                            else:
                                ni_crit = st.text_input(
                                    "判定基準", key=f"ni_crt_{m_idx}_{stype}_{s_idx}",
                                    placeholder="例：無裂痕、無毛邊")
                        with na3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("＋", key=f"ni_add_{m_idx}_{stype}_{s_idx}",
                                         use_container_width=True, type="primary"):
                                if not ni_item.strip():
                                    st.warning("請填入檢查項目")
                                else:
                                    new_cfg = copy.deepcopy(ipqc_cfg)
                                    if stype == "patrol_stations":
                                        new_cfg["models"][m_idx][stype][s_idx]["items"].append(
                                            {"item": ni_item.strip(), "grade": ni_grade}
                                        )
                                    else:
                                        new_cfg["models"][m_idx][stype][s_idx]["items"].append(
                                            {"item": ni_item.strip(),
                                             "criteria": ni_crit.strip() if 'ni_crit' in dir() else ""}
                                        )
                                    _ipqc_save_rerun(new_cfg)

                st.markdown("<br>", unsafe_allow_html=True)

            # ── 快速跳轉 ────────────────────────────────
            if st.button(f"📋 前往填寫 {mname} 巡檢表",
                         key=f"goto_ipqc_{m_idx}", use_container_width=True):
                st.switch_page("pages/20_📋_IPQC巡檢.py")
