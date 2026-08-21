# PROTC_OTISK — otisk dokumentace tepelných čerpadel

Kontext pro Claude Code. Přečti celý soubor před tím než cokoliv děláš.

## Co projekt dělá

Scraper webu `projektuj-tepelna-cerpadla.cz` (sekce Dokumentace ke stažení).
Projde všechny produktové stránky, zaznamená každý dokument (kde je, jak se
jmenuje popis, název souboru, typ, velikost) a uloží do Excelu a/nebo CSV
(volba `--format`), aby se dal otisk snadno zpracovat i mimo Excel — třeba
naimportovat do jiné aplikace..

Porovnávání dvou otisků (bývalý `compare.py`) bylo **odstraněno** — nástroj
teď dělá jen otisk, žádný diff. Identita řádku (kdyby ji chtěl spočítat
někdo jiný navazující nástroj) je pozice: produkt + sekce + pořadí v sekci —
web dokumenty **nepřidává**, jen je **přejmenovává**.

## Jak web vypadá — DOM struktura (ověřeno živým prohlížečem)

### Rozcestník `/cz/dokumentace-ke-stazeni`

Produkty jsou v `<div>` layoutu, **ne v `<table>`**. Každý produkt má odkaz
s textem „Vybrat" (`href="/cz/nazev-produktu"`). JS skript `JS_INDEX` v
`snapshot.py` sbírá právě tyto odkazy.

Kategorie (nadpisy nad skupinami produktů):
- VZDUCH/VODA pro jednoduché instalace v menších budovách 4 až 20 kW
- VZDUCH/VODA pro větší budovy nebo složitější instalace 10 až 1 300 kW
- ZEMĚ/VODA pro jednoduché instalace v menších budovách 4 až 20 kW
- ZEMĚ/VODA a VODA/VODA pro větší budovy… 10 až 4 000 kW
- Vysokoteplotní VZDUCH/VODA, VZDUCH/VZDUCH, Plynové MIKROKOGENERAČNÍ
- Zásobníky teplé vody, Akumulátory topné a chladicí vody
- Podlahové vytápění, Primární okruhy, Ostatní

### Produktová stránka (např. `/cz/ivt-geo-700-zeme-voda`)

**Klíčové zjištění:** Stránka nepoužívá `<table><tr><td>` — dokumenty jsou
v `<div class="toggle-block-trow">` s dětskými divy:

```
div.toggle-block-trow          ← jeden řádek dokumentu
  div                          ← Popis dokumentu (první div)
  div                          ← Typ (PDF / DWG / ...)
  div.url                      ← odkaz ke stažení
    a[href="/?download=..."]   ← přihlášený: reálný odkaz
    a[href="javascript:;"]     ← nepřihlášený: zámek
  div.note                     ← Poznámka
```

Hlavičkové řádky (`Popis dokumentu | Typ | Dokument ke stažení | Poznámka`)
jsou taky `.toggle-block-trow` — filtrujeme je podle toho že první div = "Popis dokumentu".

Každý odkaz má vedle sebe ikonkový prázdný `<a>` se stejným `href` —
filtrujeme přes `clean(a.innerText) !== ''`.

Sekce dokumentů jsou uvozeny nadpisy (`h2`, `h3`, `h4`) nad skupinou řádků.
Reálné sekce u GEO 700 (ověřeno):
1. Nejvyhledávanější dokumenty
2. Technické listy
3. Návody pro obsluhu a instalaci
4. Projekční podklady a provozní parametry
5. Elektro a MaR podklady
6. Doporučená schémata hydraulického zapojení DWG/PDF
7. (+ někdy prezentace bez nadpisu sekce)

Schémata hydraulického zapojení mají v jednom řádku **dva soubory** (PDF + DWG)
→ `poradi_v_sekci` je celé číslo počítané per soubor, ne per řádek, takže
takový řádek dostane dvě po sobě jdoucí celá čísla (např. `12` a `13`),
ne desetinný zápis.

GEO 700 má celkem ~57 unikátních dokumentů (114 odkazů celkem včetně ikonek).

### Přihlášení

- Nepřihlášený: zamčené dokumenty mají `href="javascript:;"`, velikost chybí
- Přihlášený: všechny dokumenty mají `href="/?download=cesta/soubor.pdf"`
- Session se ukládá do `session.json` přes Playwright `storage_state`

Formáty download odkazů:
- `/?download=_/product.82/technicky_list_ivt_geo700.pdf` — soubor specifický pro produkt
- `/?download=Kalle/IVT/Manualy/nazev.pdf` — sdílený soubor napříč produkty

## Soubory projektu

```
protc_otisk.py        — univerzalni CLI vstupni bod: `python protc_otisk.py login|snapshot`
snapshot.py           — hlavní crawler (rozcestník + produktové stránky → xlsx/csv)
extractor.py          — pomocné Python funkce (find_size, is_locked, file_path_from_href, check_session, print_banner, load_config)
login.py              — otevře prohlížeč, uživatel se ručně přihlásí → session.json
config.txt            — volitelné výchozí hodnoty pro snapshot (format, types, filtry, ...) — viz níže
requirements.txt

START-mac.command     — dvojklik ve Finderu na Mac (.sh se dvojklikem jen otevře v editoru, .command se spustí);
                        aktivuje/vytvoří .venv a nechá terminál otevřený pro ruční příkaz
START-windows.bat     — dvojklik v Exploreru na Windows (aktivuje/vytvoří .venv, předá argumenty do protc_otisk.py)
START-linux.sh        — terminál na Linuxu i Macu: `./START-linux.sh <příkaz>` (aktivuje/vytvoří .venv, předá argumenty)

.gitignore     — obsahuje session.json, exports/, logs/, .venv/, .DS_Store (nesmí do repozitáře)
exports/       — výstupy snapshot.py: snapshot_RRRRMMDD_HHMMSS.xlsx a/nebo .csv
logs/          — log každého běhu snapshot.py/login.py, vč. tracebacků chyb
```

Každý běh `snapshot.py` vytvoří dvojici stejně pojmenovaných souborů se
shodným časovým razítkem — `exports/snapshot_<timestamp>.xlsx` a
`logs/snapshot_<timestamp>.log` — takže když je s otiskem problém, dá se
přesně dohledat, co se při jeho vzniku dělo (log obsahuje i plný traceback
chyb přes `logger.exception`, ne jen text výjimky).

### Klíčové funkce v snapshot.py

**`JS_INDEX`** — JS spuštěný na rozcestníku. Sbírá všechny `<a>` s textem
„Vybrat", k nim hledá kategorii z předcházejícího nadpisu.

**`JS_PRODUCT`** — JS spuštěný na produktové stránce. Projde všechny
`.toggle-block-trow` divy, vytáhne popis / typ / odkaz / poznámku.
Filtruje hlavičkové řádky a prázdné ikonkové duplikáty.

**`scrape_index(page)`** — načte rozcestník, vrátí seznam produktů
`{kategorie, znacka, typ_produktu, produkt_url}`.

**`scrape_product(page, product)`** — načte produktovou stránku, vrátí
seznam dokumentů jako dict odpovídající sloupcům xlsx.

**`write_xlsx(records, path)`** — zapíše otisk do Excelu se zmrazeným
prvním řádkem a autofiltery. **`write_csv(records, path)`** — totéž jako
prosté CSV (`;` oddělovač, `utf-8-sig` kódování).

Filtr `--types` (výchozí `all`, jinak čárkou oddělený seznam jako `pdf,dwg`)
se aplikuje v `main()` až po scrapu celého webu — porovnává `typ_souboru`
(velkými písmeny) proti zadané množině a v logu vypíše, kolik řádků
odfiltroval. Doba trvání každého produktu i celého běhu se měří přes
`time.perf_counter()` a loguje se v souhrnu „Hotovo" (`celkovy cas behu`);
detailní řádek s časem a ETA za každý produkt jde jen do log souboru (viz
progress bar níže).

**`ProgressBar`** (třída v `snapshot.py`) — jednořádkový progress bar
v konzoli, přepisovaný přes `\r` (`update()`), přeskočí se úplně, když
`sys.stdout` není terminál (`isatty()` False, typicky při přesměrování
výstupu). Detailní `logger.info` řádek za každý produkt (počet dokumentů,
čas, ETA) se loguje s `extra={"file_only": True}` — `_ConsoleFilter` na
konzolovém handleru ho vynechá, takže na konzoli je jen bar, ale v log
souboru zůstává vše jako předtím. Před `logger.warning`/`logger.exception`
uprostřed běhu (retry, chyba produktu) se volá `bar.interrupt()`, aby zpráva
nerozbila rozepsaný řádek baru. Vyplněná část baru je zelená
(`extractor.GREEN`/`RESET`).

**Banner a barvy** (`extractor.py`) — `print_banner()` vypíše malé ASCII
logo + `PROTC_OTISK` + `by Kotrsal`. Volá se **jen** z `protc_otisk.py`
(cesta bez podpříkazu/`--help`/neznámý příkaz) — `login.py` a `snapshot.py`
ho ve svém `main()` už nevolají, aby se banner neopakoval při každém
jednotlivém příkazu v jedné terminálové seanci (typicky `START-mac.command`),
jen jednou při "nahození" nástroje. `enable_ansi()` na Windows povolí
zpracování ANSI escape sekvencí přes `ctypes`/`SetConsoleMode`
(`ENABLE_VIRTUAL_TERMINAL_PROCESSING`) — bez závislosti na `colorama`; na
Mac/Linux se nic nedělá, ANSI tam funguje odjakživa. Interní `_c(code)`
vrátí barevný kód, jen když `sys.stdout.isatty()` je pravda — jinak prázdný
řetězec, aby se při přesměrování výstupu (log soubor, roura) nepletly
syrové escape sekvence do textu. Selže-li `enable_ansi()` na starším
Windows, jede se dál bez barev, nic se nerozbije (`except Exception: pass`).

**`load_config()` / `cfg_bool()`** (`extractor.py`) — načte `config.txt`
(prosté `klic = hodnota` řádky, `#` komentář, chybějící soubor = prázdný
dict) a vrátí `dict[str, str]`. `snapshot.py` ho volá na začátku `main()` a
použije jako `default=` pro odpovídající `argparse` volby (`format`,
`types`, `category`, `brand`, `product_type`, `section`, a přes `cfg_bool()`
i boolean `headed`/`no_session`/`dry_run`) — CLI volba zadaná přímo v
příkazu argparse default přebije, config.txt je tedy jen výchozí hodnota.
`build_usage()` v `protc_otisk.py` volá `load_config()` znovu, aby v
nápovědě zobrazil skutečně nastavený `--format`/`--types` default, ne
natvrdo napsaný text.

**`check_session(page, check_url)`** (v `extractor.py`, sdílené s `login.py`)
— otevře stránku GEO 700, spočítá zamčené (`javascript:;`) vs. stažitelné
(`download=`) odkazy, vrátí `{"locked", "downloads", "ok"}`. `snapshot.py`
ji volá hned po otevření prohlížeče (pokud není `--no-session`) a při
`ok=False` skončí okamžitě, aniž by četl rozcestník.

**Filtry `--category`/`--brand`/`--product-type`** (substring, přes funkci
`normalize()` bez ohledu na velikost písmen i diakritiku — `unicodedata.
normalize("NFKD", ...)` + odstranění kombinujících znaků + `.lower()`,
čárkou oddělené varianty) filtrují `products` hned po `scrape_index`, tedy
**před** otevřením jednotlivých produktových stránek — šetří to čas,
protože se nenačítají stránky, které by se stejně zahodily. **`--section`**
funguje stejně (stejná `normalize()`/`matches_any()`), ale aplikuje se až na
`records` po scrapu — sekce se pozná teprve na produktové stránce, takže dřív
filtrovat nejde.

Pokus o produkt, který spadne, se v `main()` opakuje až 3× (`MAX_POKUSU`,
s `page.wait_for_timeout(1500)` mezi pokusy) — teprve poslední neúspěšný
pokus se počítá do `chyby` a loguje se s tracebackem.

**`--dry-run`** přeskočí `write_xlsx`/`write_csv` úplně — scrape i filtry
proběhnou normálně, jen se nikam nezapíše.

**`--nejvyhledavanejsi`** — sekce „Nejvyhledávanější dokumenty" (viz seznam
sekcí GEO 700 výše) obsahuje dokumenty, které jsou zároveň i v jiných sekcích
níž na stránce (jsou to jen zkratky/výběr), takže se ve `scrape_product`
ve výchozím stavu zahazují stejně jako `EXCLUDED_SECTIONS` (`div.toggle-block-
title-text` == `NEJVYHLEDAVANEJSI_SECTION`), aby otisk neobsahoval
duplicitní řádky. `--nejvyhledavanejsi` (i `nejvyhledavanejsi = true` v
`config.txt`) tohle zahazování vypne a sekce se zaznamená jako kterákoliv
jiná — `scrape_product` bere `include_nejvyhledavanejsi` jako parametr,
`main()` mu předává `args.nejvyhledavanejsi`.

**`--no-dwg`** — nezávislá zkratka vedle `--types` pro vypnutí zaznamenávání
DWG souborů (výchozí zapnuto/zaznamenávat). Filtruje se v `main()` hned za
filtrem `--types`, na `records` po scrapu (`r["typ_souboru"].upper() !=
"DWG"`), takže funguje i nezávisle na tom, co je zadané v `--types` (tedy
`--types all --no-dwg` je jinak zapsané totéž jako `--types pdf`, jen bez
nutnosti vyjmenovávat, co všechno kromě DWG chci).

**Napovídání překlepů** (`difflib.get_close_matches`) — `protc_otisk.py`
ho použije na neznámý podpříkaz (`COMMANDS = ("login", "snapshot")`,
`snpashot` → „Možná jsi myslel: 'snapshot'?"). `snapshot.py` volá
`ap.parse_known_args()` místo `ap.parse_args()`, aby u neznámé volby mohl
sám navrhnout nejbližší platnou (`--tyeps` → „možná jsi myslel '--types'?")
místo obecné argparse hlášky. Pozor: argparse defaultně povoluje zkrácené
dlouhé volby (`--forma` se tiše vyhodnotí jako `--format`), takže tohle
nechytí — je to platná zkratka, ne překlep.

**`START-mac.command` a `clear`** — po vypsání banneru+nápovědy nahradí
`exec "$SHELL"` uvnitř dočasného shell profilu (`mktemp`), který navíc
předefinuje `clear` jako funkci `command clear; python protc_otisk.py`
— takže `clear` v tomhle jednom terminálovém okně kromě smazání obrazovky
znovu ukáže banner+nápovědu. Pro zsh přes dočasný `ZDOTDIR`, pro bash přes
`--rcfile`; pro cokoliv jiného spadne zpátky na obyčejný `exec "$SHELL"`.

### Sloupce xlsx/csv

Pozn.: `klic`, `produkt`, `produkt_url`, `cesta_souboru` a `dostupnost` se
počítají v `scrape_product`, ale do samotného xlsx/csv se nezapisují — nejsou
v `COLUMNS`. `klic` (`produkt_url|sekce|pořadí`) je stabilní identita řádku
pro případ, že by ji chtěl použít nějaký navazující nástroj.

| sloupec | popis |
|---|---|
| `kategorie` | nadpis skupiny produktů na rozcestníku |
| `znacka`, `typ_produktu` | IVT / GEO 700 |
| `sekce` | Technické listy / Návody... / atd. |
| `poradi_v_sekci` | celé číslo 1, 2, 3...; řádek s víc soubory dostane dvě po sobě jdoucí čísla, ne desetinné |
| `popis_dokumentu` | první div v toggle-block-trow |
| `typ_souboru` | PDF / DWG |
| `nazev_souboru` | text odkazu, např. `technicky_list_ivt_geo700` |
| `velikost` | např. `167 kB` (z textu řádku) |
| `poznamka` | div.note |
| `url_stazeni` | reálná URL ke stažení, prázdné když je dokument zamčený |

## Spuštění

Nejjednodušší je přes `START-mac.command` (Mac, dvojklik) / `START-windows.bat`
(Windows, dvojklik) / `START-linux.sh` (Linux, terminál) — jméno rovnou říká,
pro který systém je který. Terminálové varianty (`START-linux.sh`,
`START-windows.bat`) samy aktivují (poprvé i vytvoří) `.venv` a předají
argumenty do `protc_otisk.py`:

```bash
./START-linux.sh login              # Windows: START-windows.bat login
./START-linux.sh snapshot           # Windows: START-windows.bat snapshot
```

Ruční varianta (bez `START-*` skriptů):

```bash
# Instalace (jednou)
pip install -r requirements.txt
playwright install chromium

# Přihlášení (jednou za čas, session vyprší)
python protc_otisk.py login          # nebo: python login.py

# Otisk celého webu (do exports/, xlsx podle výchozí volby --format)
python protc_otisk.py snapshot       # nebo: python snapshot.py

# Test (jen 3 produkty, viditelný prohlížeč)
python protc_otisk.py snapshot --limit 3 --headed

# Otisk do CSV i xlsx zaroveň
python protc_otisk.py snapshot --format both

# Otisk jen vybranych typu souboru (--types, vychozi "all")
python protc_otisk.py snapshot --types pdf
python protc_otisk.py snapshot --types pdf,dwg

# Filtr produktu podle kategorie/znacky/typu produktu + filtr sekce dokumentu
python protc_otisk.py snapshot --category "vzduch/voda" --brand ivt
python protc_otisk.py snapshot --section "Technické listy"

# Zkusebni beh bez zapisu vystupu (jen souhrn v konzoli/logu)
python protc_otisk.py snapshot --dry-run

# Zaznamenat i sekci "Nejvyhledavanejsi dokumenty" (vychozi vypnuto)
python protc_otisk.py snapshot --nejvyhledavanejsi

# Bez DWG souboru (vychozi zaznamenavat)
python protc_otisk.py snapshot --no-dwg
```

`protc_otisk.py` je jen tenký CLI obal (subcommand dispatcher) nad `login.py` a
`snapshot.py` — dá se volat i každý skript zvlášť, chová se stejně.

Výchozí hodnoty voleb (`format`, `types`, filtry, ...) se dají nastavit
trvale v [config.txt](config.txt), aniž by bylo nutné je psát pokaždé do
příkazové řádky — viz [README.md](README.md#výchozí-nastavení-configtxt).

## Známé problémy a jejich řešení

**`nalezeno 0 produktu`** — JS_INDEX nenašel žádné odkazy „Vybrat".
Pravděpodobně se změnil layout rozcestníku. Spusť s `--headed` a zkontroluj
co je na stránce.

**`-> 0 dokumentu`** u všech produktů — JS_PRODUCT nenachází `.toggle-block-trow`.
Buď se změnily CSS třídy, nebo stránka vyžaduje přihlášení a session vypršela.
Zkontroluj `login.py` znovu.

**Hodně `zamceno / nedostupne`** — session vypršela. Spusť `login.py`.
`snapshot.py` (bez `--no-session`) teď navíc session ověří **hned na
začátku** přes `check_session()` (`extractor.py`, sdílené i s `login.py`) —
pokud je mrtvá, skončí okamžitě s chybou, ne až po projetí všech produktů.

**Prohlížeč se sám otvírá při každém běhu** — zkontroluj `headed` v
`config.txt`. Když je tam `headed = true`, KAŽDÝ běh `snapshot` (i bez
`--headed` v příkazu) otevře viditelné okno prohlížeče, protože config.txt
je jen výchozí hodnota pro `--headed`. Vrať na `headed = false`, pokud to
nebylo záměrné.

**Produkt selhal při scrapovani** — `scrape_product` se automaticky zkusí
znovu (celkem 3 pokusy s pauzou 1,5 s mezi nimi), teprve po vyčerpání všech
se počítá jako chyba a loguje se traceback.

**Duplikáty** — každý soubor má v DOM dva `<a>` (jeden s textem = název souboru,
jeden prázdný = ikonka). Filtrujeme přes `clean(a.innerText) !== ''`.

**Cokoliv jiného spadlo** — mrkni do `logs/snapshot_<timestamp>.log` (nebo
`logs/login_<timestamp>.log`) odpovídajícího běhu. Chyby při scrapování
jednotlivých produktů i fatální pády jsou tam zalogované přes
`logger.exception()`, tedy i s celým Python tracebackem, ne jen textem chyby.

## Co se může dál zlepšit

- ~~Retry na selhaný produkt~~ — hotovo (`MAX_POKUSU=3` v `main()`)
- ~~Detekce vypršelé session před celým během~~ — hotovo (`check_session()`)
- ~~Progress s ETA~~ — hotovo, jako vizuální progress bar v konzoli
  (`ProgressBar`), detail za produkt jen v logu
- ~~Filtry necitlivé na diakritiku/velikost písmen~~ — hotovo (`normalize()`)
- ~~`--dry-run`~~ — hotovo
- ~~Filtr podle kategorie/značky/typu produktu/sekce~~ — hotovo
  (`--category`, `--brand`, `--product-type`, `--section`)
- ~~Jednodušší spouštění na Mac i Windows~~ — hotovo (`START-mac.command`/
  `START-windows.bat`/`START-linux.sh`, pojmenované podle systému)
- ~~Decentní grafika (banner, barevný progress bar)~~ — hotovo
  (`print_banner()`, zelený `ProgressBar`)
- ~~Konfigurovatelné výchozí hodnoty (`--format` atd.) bez psaní do CLI~~ —
  hotovo (`config.txt`, `load_config()`), nápověda je zobrazuje dynamicky
- ~~Volitelné zaznamenání sekce "Nejvyhledávanější dokumenty"~~ — hotovo
  (`--nejvyhledavanejsi` / `nejvyhledavanejsi = true` v `config.txt`,
  výchozí vypnuto)
- ~~Vypnutí zaznamenávání DWG souborů bez psaní `--types`~~ — hotovo
  (`--no-dwg` / `no_dwg = true` v `config.txt`, výchozí zapnuto/zaznamenávat)
- SHA-256 hash stažených souborů → poznat přejmenování bez změny obsahu
  (vyžaduje reálně stahovat soubory, ne jen zaznamenávat metadata — zatím
  vědomě odloženo)
- Rotace/archivace starých `exports/`+`logs/` souborů, ať složka neroste do nekonečna
- Cron / scheduled task → automatické spouštění
- Znovu promyslet porovnávání otisků (bylo odstraněno) — pokud bude potřeba,
  bude to nejspíš samostatný nástroj nad `exports/*.csv`, ne součást `snapshot.py`
