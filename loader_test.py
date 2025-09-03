# loader_test.py — testa leitura do catalog.txt

import os, re
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
CATALOG_TXT = os.path.join(BASE, "catalog.txt")

# regex para capturar campos
RE_CODE     = re.compile(r"^\s*codigo\s*>\s*([0-9]+)", re.IGNORECASE | re.MULTILINE)
RE_TIPO     = re.compile(r"^\s*tipo\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_SUBTIPO  = re.compile(r"^\s*subtipo\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_DISP     = re.compile(r"^\s*dispon[ií]vel\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_PRECO    = re.compile(r"^\s*pre[cç]o\s*:\s*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE | re.MULTILINE)

def parse_bool(s: str) -> bool:
    s = (s or "").strip().lower()
    return s in {"sim","true","1","yes","y","ok"}

def norm_price(s: str) -> float:
    if not s: return 0.0
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def mask_code(code: str) -> str:
    return code[:6] + ("*" * max(0, len(code) - 6))

def load_catalog(path: str):
    raw = open(path, "r", encoding="utf-8").read()
    blocks = [b.strip() for b in raw.split("---") if b.strip()]
    items = []
    for blk in blocks:
        m_code = RE_CODE.search(blk)
        m_tipo = RE_TIPO.search(blk)
        m_sub  = RE_SUBTIPO.search(blk)
        if not (m_code and m_tipo and m_sub):
            continue
        code = m_code.group(1).strip()
        tipo = m_tipo.group(1).strip()
        sub  = m_sub.group(1).strip()
        disp = True
        m_disp = RE_DISP.search(blk)
        if m_disp: disp = parse_bool(m_disp.group(1))
        m_preco = RE_PRECO.search(blk)
        preco = norm_price(m_preco.group(1) if m_preco else "")
        items.append({
            "type": tipo,
            "subtype": sub,
            "code": code,
            "masked": mask_code(code),
            "available": disp,
            "price": preco,
            "raw": blk
        })
    return items

if __name__ == "__main__":
    items = load_catalog(CATALOG_TXT)
    print("=== Tipos e Subtipos Encontrados ===")
    tipos = defaultdict(set)
    for it in items:
        if it["available"]:
            tipos[it["type"]].add(it["subtype"])
    for t, subs in tipos.items():
        print(f"Tipo: {t} -> Subtipos: {', '.join(subs)}")

    print("\n=== Exemplo de código (primeiro disponível de cada tipo/subtipo) ===")
    seen = set()
    for it in items:
        key = (it["type"], it["subtype"])
        if it["available"] and key not in seen:
            seen.add(key)
            print(f"\n[{it['type']} / {it['subtype']}]")
            print(f" Código mascarado: {it['masked']}")
            print(" Texto completo:")
            print(it["raw"])

