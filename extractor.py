"""
Sdilene funkce pro extrakci tabulek ze stranek PROTC_OTISK.

Klicova myslenka: neopiram se o konkretni CSS tridy webu (ty se mohou zmenit),
ale o strukturu - najdu vsechny <table>, k nim nejblizsi predchazejici nadpis
(= nazev sekce) a vytahnu bunky + odkazy z kazdeho radku.
"""

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Vychozi nastaveni z config.txt (viz sekce nize)
# ---------------------------------------------------------------------------
CONFIG_FILE = Path(__file__).parent / "config.txt"


def load_config():
    """Nacte vychozi nastaveni z config.txt vedle skriptu - jednoduchy
    textovy soubor 'klic = hodnota' na radek. '#' na zacatku radku = komentar,
    prazdne radky se ignoruji. Kdyz config.txt neexistuje (nebo je klic
    prazdny/chybi), pouziji se vestavene defaulty v snapshot.py - config.txt
    je cely volitelny. Vraci dict {klic: retezec_hodnoty}."""
    cfg = {}
    if not CONFIG_FILE.exists():
        return cfg
    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        cfg[key.strip()] = value.strip()
    return cfg


def cfg_bool(cfg, key, default=False):
    """Precte true/false hodnotu z dict vraceneho load_config()."""
    v = cfg.get(key)
    if not v:
        return default
    return v.strip().lower() in ("1", "true", "ano", "yes")


# ---------------------------------------------------------------------------
# Barvy a banner - decentni grafika na startu snapshot.py/login.py
# ---------------------------------------------------------------------------
GREEN = "\033[32m"
BOLD_GREEN = "\033[1;32m"
DIM = "\033[2m"
RESET = "\033[0m"


def enable_ansi():
    """Na Windows povoli zpracovani ANSI escape kodu (VT100 rezim) v konzoli -
    bez toho by se barvy/progress bar vypisovaly jako syrove escape sekvence
    misto barev. Na Mac/Linux ANSI funguje uz z principu, tam se nic nedela.
    Kdyz se to na starsim Windows nepodari povolit, jede se dal bez barev -
    nic se tim nerozbije."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass


def _c(code):
    """Vrati ANSI kod, jen kdyz stdout je opravdovy terminal - jinak prazdny
    retezec, aby se pri presmerovani vystupu do souboru/roury nepletly syrove
    escape sekvence do textu."""
    return code if sys.stdout.isatty() else ""


def print_banner():
    """Male decentni ASCII logo na startu behu - jen jednou, na konzoli."""
    enable_ansi()
    g, bg, d, r = _c(GREEN), _c(BOLD_GREEN), _c(DIM), _c(RESET)
    print(f"{g}   ___{r}")
    print(f"{g}  /   \\{r}    {bg}PROTC_OTISK{r}")
    print(f"{g} | * * |{r}   otisk dokumentace tepelnych cerpadel")
    print(f"{g}  \\___/{r}    {d}by Kotrsal{r}")
    print()


# ---------------------------------------------------------------------------
# JS, ktery bezi primo ve strance a vrati syrova data vsech tabulek
# ---------------------------------------------------------------------------
JS_EXTRACT_TABLES = r"""
() => {
  const H = ['H1','H2','H3','H4','H5','H6'];

  // najde nejblizsi nadpis PRED danym elementem (prochazi sourozence i predky)
  function prevHeading(el) {
    let cur = el;
    while (cur && cur !== document.body) {
      let sib = cur.previousElementSibling;
      while (sib) {
        if (H.includes(sib.tagName)) {
          const t = (sib.innerText || '').replace(/\s+/g, ' ').trim();
          if (t) return t;
        }
        const inner = sib.querySelectorAll('h1,h2,h3,h4,h5,h6');
        if (inner.length) {
          const t = (inner[inner.length - 1].innerText || '').replace(/\s+/g, ' ').trim();
          if (t) return t;
        }
        sib = sib.previousElementSibling;
      }
      cur = cur.parentElement;
    }
    return '';
  }

  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const out = [];

  document.querySelectorAll('table').forEach((table, ti) => {
    const rows = [];
    table.querySelectorAll('tr').forEach((tr) => {
      const cellEls = Array.from(tr.querySelectorAll('th, td'));
      const cells = cellEls.map(td => clean(td.innerText));
      const links = Array.from(tr.querySelectorAll('a')).map(a => ({
        text: clean(a.innerText),
        href: a.getAttribute('href') || '',
        abs:  a.href || '',
        title: a.getAttribute('title') || ''
      }));
      if (cells.length === 0 && links.length === 0) return;
      rows.push({ cells, links });
    });
    if (rows.length) {
      out.push({ table_index: ti, section: prevHeading(table), rows });
    }
  });

  return {
    url: location.href,
    title: clean(document.title),
    h1: clean((document.querySelector('h1') || {}).innerText || ''),
    tables: out
  };
}
"""

# ---------------------------------------------------------------------------
# Pomocne funkce
# ---------------------------------------------------------------------------

SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(B|kB|KB|MB|GB)\b")


def find_size(text):
    """Vytahne velikost souboru z textu bunky, napr. '167 kB'."""
    m = SIZE_RE.search(text or "")
    return m.group(0).replace("\xa0", " ").strip() if m else ""


def header_index(rows):
    """
    Vrati (index_radku_s_hlavickou, {nazev_sloupce_lower: index}).
    Hlavicku hleda podle znamych popisku, ne podle <th>.
    """
    known = (
        "popis dokumentu", "znacka", "značka", "typ",
        "dokument ke stazeni", "dokument ke stažení", "poznamka", "poznámka",
        "vykon", "výkon", "objem", "popis", "komentar", "komentář",
        "dimenze potrubi", "dimenze potrubí", "funkce", "umisteni", "umístění",
        "material", "materiál", "max. teplota",
    )
    for i, row in enumerate(rows[:3]):
        cells = [c.lower() for c in row.get("cells", [])]
        hits = sum(1 for c in cells if c in known)
        if hits >= 2:
            return i, {c: idx for idx, c in enumerate(cells) if c}
    return -1, {}


def cell(row, mapping, *names):
    """Vrati obsah bunky podle nazvu sloupce (zkousi vice variant)."""
    cells = row.get("cells", [])
    for n in names:
        idx = mapping.get(n.lower())
        if idx is not None and idx < len(cells):
            return cells[idx]
    return ""


def is_locked(href):
    """Odkaz na zamceny / nedostupny soubor."""
    h = (href or "").strip().lower()
    return (
        h in ("", "#")
        or h.startswith("javascript:")
    )


def is_download(href):
    """Je to odkaz na skutecne stazeni souboru?"""
    h = (href or "").lower()
    return "download=" in h or h.endswith((".pdf", ".dwg", ".zip", ".xlsx", ".docx", ".doc", ".xls", ".dxf"))


CHECK_URL = "https://www.projektuj-tepelna-cerpadla.cz/cz/ivt-geo-700-zeme-voda"


def check_session(page, check_url=CHECK_URL):
    """
    Otevre znamou produktovou stranku (GEO 700) a spocita zamcene ('javascript:;')
    vs. stazitelne ('download=') odkazy - podle pomeru pozna, jestli je session
    (porad) platna. Pouziva login.py (hned po prihlaseni) i snapshot.py
    (pred zacatkem cele crawlky, aby se predeslo zbytecnemu behu naprazdno).

    Vraci dict {"locked": int, "downloads": int, "ok": bool}.
    """
    page.goto(check_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    locked = page.evaluate(
        "() => Array.from(document.querySelectorAll('a'))"
        ".filter(a => (a.getAttribute('href')||'').startsWith('javascript:;')).length"
    )
    downloads = page.evaluate(
        "() => Array.from(document.querySelectorAll('a'))"
        ".filter(a => (a.getAttribute('href')||'').includes('download=')).length"
    )
    ok = not (locked > 5 and downloads < 10)
    return {"locked": locked, "downloads": downloads, "ok": ok}


def file_path_from_href(abs_href):
    """
    Z '...?download=_/product.82/technicky_list.pdf' udela
    '_/product.82/technicky_list.pdf' - to je stabilni identifikator souboru.
    """
    if not abs_href:
        return ""
    m = re.search(r"[?&]download=([^&]+)", abs_href)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1))
    return ""
