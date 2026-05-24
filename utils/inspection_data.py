"""
REXONTEC OQC — 檢驗項目定義
支援 JSON 設定檔（config/inspection_config.json）覆寫
若設定檔不存在則自動建立預設值
"""
import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'inspection_config.json')

# ─────────────────────────────────────────────────────
# 預設值（程式碼內建，作為備援）
# ─────────────────────────────────────────────────────
_DEFAULT_ESC_SECTIONS = [
    {
        "id": "A",
        "label": "電氣功能測試類",
        "subtitle": "飛行控制器 + 電調測試台",
        "items": [
            {
                "id": "A1", "no": "1.0",
                "name": "上電初始化自檢",
                "spec": "啟動音正常 (3+2聲響)，無異常報警音",
                "grade": "MA", "type": "pf",
                "tool": "目視/耳聽",
            },
            {
                "id": "A2", "no": "2.0",
                "name": "失控保護 (Failsafe)",
                "spec": "訊號丟失後立即停轉，並發出連續警告音",
                "grade": "MA", "type": "pf",
                "tool": "RC 接收機斷訊測試",
            },
            {
                "id": "A3", "no": "3.0",
                "name": "低油門平順測試",
                "spec": "20%~40% 油門區間運轉平滑，無異響或抖動",
                "grade": "MA", "type": "pf",
                "tool": "飛控腳本",
            },
            {
                "id": "A4", "no": "4.0",
                "name": "高載荷測試",
                "spec": "80% 高油門運轉 10s，輸出電流符合腳本區間",
                "grade": "MA", "type": "pf",
                "tool": "飛行運轉腳本",
            },
            {
                "id": "A5", "no": "5.0",
                "name": "瞬態響應線性度",
                "spec": "40%↔70% 快速切換，響應即時且無失步",
                "grade": "MA", "type": "pf",
                "tool": "飛控腳本",
            },
            {
                "id": "A6", "no": "6.0",
                "name": "主動剎車 (E-Brake)",
                "spec": "油門歸零後馬達迅速減速並精準停止",
                "grade": "MA", "type": "pf",
                "tool": "飛控腳本",
            },
            {
                "id": "A7", "no": "7.0",
                "name": "運行溫升監測",
                "spec": "電調表面最高溫度 ≦ 50°C",
                "grade": "MA", "type": "num",
                "unit": "°C", "min": None, "max": 50,
                "tool": "非接觸式溫度計",
            },
            {
                "id": "A8", "no": "8.0",
                "name": "線材端子溫升",
                "spec": "線材端子處最高溫度 ≦ 40°C，監測焊點是否異常",
                "grade": "CR", "type": "num",
                "unit": "°C", "min": None, "max": 40,
                "tool": "熱像儀 / 非接觸溫度計",
            },
            {
                "id": "A9", "no": "9.0",
                "name": "韌體版本核對",
                "spec": "確認燒錄 V4 (或 V3) 正確版本",
                "grade": "CR", "type": "pf",
                "tool": "Betaflight / 設定軟體",
            },
        ],
    },
    {
        "id": "B",
        "label": "外觀包裝類",
        "subtitle": "目視 + 參考樣品",
        "items": [
            {
                "id": "B1", "no": "1.0",
                "name": "外殼完整性",
                "spec": "上下蓋無劃傷、縮水、脫漆、污穢或毛邊",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "B2", "no": "2.0",
                "name": "線材與焊接品質",
                "spec": "線皮無損，焊點飽滿無虛焊，無導線裸露",
                "grade": "CR", "type": "pf",
                "tool": "目視 + 放大鏡",
            },
            {
                "id": "B3", "no": "3.0",
                "name": "端子規格檢查",
                "spec": "金屬部分無氧化、無變形，Pin 針無偏斜",
                "grade": "MA", "type": "pf",
                "tool": "目視 + 卡規",
            },
            {
                "id": "B4", "no": "4.0",
                "name": "防水灌封工藝",
                "spec": "底部封膠平整且完全覆蓋，無氣泡或溢膠",
                "grade": "MA", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "B5", "no": "5.0",
                "name": "SN碼 / QR Code 標籤檢視",
                "spec": "QR Code 與序號位置正確、清晰、無歪斜",
                "grade": "MI", "type": "pf",
                "tool": "目視 + 掃碼器",
            },
            {
                "id": "B6", "no": "6.0",
                "name": "包裝防護確認",
                "spec": "外箱/緩衝材無破損、髒污或受擠壓痕跡",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
        ],
    },
]

_DEFAULT_MOTOR_SECTIONS = [
    {
        "id": "A",
        "label": "外觀",
        "subtitle": "目視 + 參考樣品",
        "items": [
            {
                "id": "A1", "no": "1.0",
                "name": "不可撞傷、斷裂、變形",
                "spec": "本體無撞傷、裂紋或永久變形",
                "grade": "MA", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "A2", "no": "2.0",
                "name": "表面不可生銹、變色",
                "spec": "金屬面無銹蝕、異常氧化或大面積變色",
                "grade": "MA", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "A3", "no": "3.0",
                "name": "序號標籤字體清晰",
                "spec": "標籤貼附平整，SN 印刷清晰可辨識",
                "grade": "MI", "type": "pf",
                "tool": "目視 + 掃碼器",
            },
            {
                "id": "A4", "no": "4.0",
                "name": "不可污穢、脫漆",
                "spec": "外表面無油脂污染、脫漆或嚴重刮傷",
                "grade": "MA", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "A5", "no": "5.0",
                "name": "不可毛邊",
                "spec": "加工面無影響手感或配合的毛邊",
                "grade": "MI", "type": "pf",
                "tool": "目視 + 手觸",
            },
            {
                "id": "A6", "no": "6.0",
                "name": "槳夾鎖孔需正確",
                "spec": "槳夾安裝孔位正確，螺牙無損傷",
                "grade": "MA", "type": "pf",
                "tool": "目視 + 試鎖",
            },
        ],
    },
    {
        "id": "B",
        "label": "功能測試",
        "subtitle": "電機測試台 (50V DC 電源)",
        "items": [
            {
                "id": "B1", "no": "1.0",
                "name": "空載啟動運轉測試",
                "spec": "馬達正常啟動，無異響、無異常振動",
                "grade": "MA", "type": "pf",
                "tool": "電機測試台",
            },
            {
                "id": "B2", "no": "2.0",
                "name": "空載電壓",
                "spec": "49.8 ～ 50.2 V",
                "grade": "MA", "type": "num",
                "unit": "V", "min": 49.8, "max": 50.2,
                "tool": "電機測試台",
            },
            {
                "id": "B3", "no": "3.0",
                "name": "空載電流",
                "spec": "≦ 1.65 A",
                "grade": "MA", "type": "num",
                "unit": "A", "min": None, "max": 1.65,
                "tool": "電機測試台",
            },
            {
                "id": "B4", "no": "4.0",
                "name": "空載轉速",
                "spec": "3700 ～ 3900 RPM",
                "grade": "MA", "type": "num",
                "unit": "RPM", "min": 3700, "max": 3900,
                "tool": "電機測試台",
            },
            {
                "id": "B5", "no": "5.0",
                "name": "震動測試",
                "spec": "≦ 5.0 mm/s",
                "grade": "MA", "type": "num",
                "unit": "mm/s", "min": None, "max": 5.0,
                "tool": "震動計",
            },
            {
                "id": "B6", "no": "6.0",
                "name": "噪音測試",
                "spec": "≦ 70 dB",
                "grade": "MA", "type": "num",
                "unit": "dB", "min": None, "max": 70,
                "tool": "噪音計 (距30cm)",
            },
        ],
    },
    {
        "id": "C",
        "label": "包材部份",
        "subtitle": "目視檢查",
        "items": [
            {
                "id": "C1", "no": "1.0",
                "name": "紙箱",
                "spec": "無破損、潮濕或嚴重變形",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "C2", "no": "2.0",
                "name": "氣泡袋",
                "spec": "完整無破損，馬達包裹良好",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "C3", "no": "3.0",
                "name": "標籤",
                "spec": "標籤字跡清晰，內容與出貨單一致",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
            {
                "id": "C4", "no": "4.0",
                "name": "內襯紙板",
                "spec": "內襯完整，無壓壞或缺失",
                "grade": "MI", "type": "pf",
                "tool": "目視",
            },
        ],
    },
]

_DEFAULT_ESC_MODELS   = ["ES1002RX (100A)", "ES1000RX (30A)", "ES1000RX (50A)", "其他"]
_DEFAULT_MOTOR_MODELS = ["MD1001RX (18馬達)", "MD1001RX (24馬達)", "MD2004RX (18馬達)", "其他"]
_DEFAULT_CUSTOMERS    = ["長榮", "中華航空", "立航", "力山科技", "其他"]
_DEFAULT_INSPECTORS   = ["蔡承叡", "彭碧霞", "其他"]
_DEFAULT_SUPERVISORS  = ["蔡承叡", "張啟明", "黃偉倫", "其他"]
_DEFAULT_MFG_GROUPS   = ["A 組", "B 組", "C 組", "─"]

_DEFAULT_CONFIG = {
    "esc_models":     _DEFAULT_ESC_MODELS,
    "motor_models":   _DEFAULT_MOTOR_MODELS,
    "customers":      _DEFAULT_CUSTOMERS,
    "inspectors":     _DEFAULT_INSPECTORS,
    "supervisors":    _DEFAULT_SUPERVISORS,
    "mfg_groups":     _DEFAULT_MFG_GROUPS,
    "esc_sections":   _DEFAULT_ESC_SECTIONS,
    "motor_sections": _DEFAULT_MOTOR_SECTIONS,
}


# ─────────────────────────────────────────────────────
# JSON 設定檔讀寫
# ─────────────────────────────────────────────────────
def get_config() -> dict:
    """讀取設定檔；不存在時自動建立預設設定檔並回傳"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        # 補齊缺少的欄位（升級保護）
        for k, v in _DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except FileNotFoundError:
        save_config(_DEFAULT_CONFIG)
        return _DEFAULT_CONFIG
    except Exception:
        return _DEFAULT_CONFIG


def save_config(config: dict) -> None:
    """儲存設定至 JSON 檔案"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────
# 公開 getter（每次呼叫皆讀取最新設定）
# ─────────────────────────────────────────────────────
def get_sections(product_type: str) -> list:
    cfg = get_config()
    return cfg.get('esc_sections', _DEFAULT_ESC_SECTIONS) \
           if product_type == 'esc' \
           else cfg.get('motor_sections', _DEFAULT_MOTOR_SECTIONS)


def get_esc_models() -> list:
    return get_config().get('esc_models', _DEFAULT_ESC_MODELS)

def get_motor_models() -> list:
    return get_config().get('motor_models', _DEFAULT_MOTOR_MODELS)

def get_customers() -> list:
    return get_config().get('customers', _DEFAULT_CUSTOMERS)

def get_inspectors() -> list:
    return get_config().get('inspectors', _DEFAULT_INSPECTORS)

def get_supervisors() -> list:
    return get_config().get('supervisors', _DEFAULT_SUPERVISORS)

def get_mfg_groups() -> list:
    return get_config().get('mfg_groups', _DEFAULT_MFG_GROUPS)


def get_all_items(sections: list) -> list:
    """展開所有 section 的 items 成一維 list"""
    return [item for sec in sections for item in sec["items"]]


# ─────────────────────────────────────────────────────
# 向下相容別名（靜態值，供已有程式碼使用）
# ─────────────────────────────────────────────────────
ESC_SECTIONS   = _DEFAULT_ESC_SECTIONS
MOTOR_SECTIONS = _DEFAULT_MOTOR_SECTIONS
ESC_MODELS     = _DEFAULT_ESC_MODELS
MOTOR_MODELS   = _DEFAULT_MOTOR_MODELS
CUSTOMERS      = _DEFAULT_CUSTOMERS
INSPECTORS     = _DEFAULT_INSPECTORS
SUPERVISORS    = _DEFAULT_SUPERVISORS
MFG_GROUPS     = _DEFAULT_MFG_GROUPS
