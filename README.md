# PROTC_OTISK — otisk dokumentace tepelných čerpadel

Nástroj, který udělá "otisk" webu **projektuj-tepelna-cerpadla.cz** (sekce
Dokumentace ke stažení) — zaznamená, kde se který dokument nachází, jak se
jmenuje jeho popis a jak se jmenuje soubor — a uloží to do Excelu a/nebo CSV.

Tenhle dokument popisuje **jak nástroj ovládat**. Jak funguje uvnitř (proč je
udělaný zrovna takhle, co dělá který soubor) je popsáno v
[JAK_TO_FUNGUJE.md](JAK_TO_FUNGUJE.md).

## Jak to vypadá

```ansi
[32m   ___[0m
[32m  /   \[0m    [1;32mPROTC_OTISK[0m
[32m | * * |[0m   otisk dokumentace tepelnych cerpadel
[32m  \___/[0m    [2mby Kotrsal[0m

Log tohoto behu: logs/snapshot_20260819_100530.log
Overuji session...
  session OK (stazitelnych: 124, zamcenych: 0)

Ctu rozcestnik dokumentace...
  nalezeno 72 produktu / podstranek


  [[32m###########[0m-----------------]  40%  29/72  ETA ~48s
```

## Rychlý start

Ve složce jsou tři spouštěcí soubory — podle jména rovnou poznáš, který je
pro tvůj systém, žádné hádání:

| soubor | systém | jak spustit |
|---|---|---|
| **`START-mac.command`** | macOS | dvojklik ve Finderu |
| **`START-windows.bat`** | Windows | dvojklik v Exploreru |
| **`START-linux.sh`** | Linux (i Mac z terminálu) | `./START-linux.sh <příkaz>` |

Všechny tři dělají totéž — samy aktivují `.venv` (a při úplně prvním
spuštění ho i vytvoří a nainstalují závislosti), takže se nemusí ručně
psát `source .venv/bin/activate` před každým během. `START-mac.command`
navíc po dvojkliku rovnou ukáže nápovědu a nechá terminál otevřený, abys
tam mohl/a napsat příkaz ručně.

Terminálové použití (`START-linux.sh` na Mac/Linuxu, `START-windows.bat` na
Windows) — obě jen předají argumenty do `protc_otisk.py`, dají se použít
stejně jako `python protc_otisk.py ...`, jen bez ruční aktivace prostředí:

```bash
cd protc_otisk
./START-linux.sh login              # Mac/Linux, jednorazove prihlaseni
./START-linux.sh snapshot           # Mac/Linux, vytvori otisk
./START-linux.sh snapshot --limit 3 --headed

START-windows.bat login             # Windows, jednorazove prihlaseni
START-windows.bat snapshot          # Windows, vytvori otisk
```

### Proč `.sh` nejde spustit dvojklikem na Macu

Dvojklik přímo na `START-linux.sh` ve Finderu ho **nespustí** — macOS `.sh`
soubory standardně jen otevře v textovém editoru (bezpečnostní chování
systému, ne chyba skriptu). Proto pro Mac existuje zvlášť
`START-mac.command`, které Finder skutečně spustí (otevře Terminál).

### Ruční varianta (bez `START-*` skriptů)

```bash
cd protc_otisk                  # slozka s projektem
source .venv/bin/activate       # aktivuje virtualni prostredi (poprve viz nize)
python protc_otisk.py login           # jednorazove prihlaseni
python protc_otisk.py snapshot        # vytvori otisk
```

## Instalace (jen poprvé)

Přes kterýkoliv `START-*` soubor se instalace řeší automaticky při prvním
spuštění. Ručně (nebo když chceš vidět, co se přesně děje):

```bash
cd protc_otisk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Instaluje se do vlastního `.venv`, aby se to nepletlo se systémovým Pythonem.
`.venv` už v projektu pravděpodobně existuje — pak stačí jen `source
.venv/bin/activate`, instalaci přeskoč.

## Každodenní použití

Celý nástroj se ovládá přes jeden vstupní bod `protc_otisk.py` s **podpříkazy**
(stejný princip jako `git commit`, `git push`):

```bash
./START-linux.sh <příkaz> [volby]      # Mac/Linux, aktivuje .venv samo
START-windows.bat <příkaz> [volby]     # Windows, aktivuje .venv samo
python protc_otisk.py <příkaz> [volby] # rucni varianta, potrebuje aktivni .venv
```

Pokud jedeš ruční variantou (bez `START-*` skriptů), ujisti se, že máš
aktivní `.venv` (v terminálu vidíš `(.venv)` na začátku řádku). Pokud ne:

```bash
cd "/Users/simonkotrsal/Desktop/protc_otisk"
source .venv/bin/activate
```

### `python protc_otisk.py login`

Otevře viditelný prohlížeč na přihlašovací stránce webu. **Přihlásíš se tam
ručně** (jméno + heslo) — skript heslo nezná, neukládá a nikam neposílá. Pak
se vrátíš do terminálu a zmáčkneš Enter. Uloží se `session.json` a od teď
`snapshot.py` může stahovat i zamčené (přihlášením podmíněné) dokumenty.

Spusť znovu, kdykoliv `snapshot.py` hlásí hodně `zamceno / nedostupne` —
session časem vyprší.

### `python protc_otisk.py snapshot`

Projde rozcestník dokumentace, otevře každou produktovou stránku a
zaznamená všechny dokumenty. Výstup:

- `exports/snapshot_RRRRMMDD_HHMMSS.xlsx` (a/nebo `.csv`) — samotný otisk
- `logs/snapshot_RRRRMMDD_HHMMSS.log` — log běhu se **stejným** časovým
  razítkem, takže k výstupu vždycky dohledáš, co přesně se při jeho vzniku
  dělo (viz [Ladění a logy](#ladění-a-logy) níže)

Volby:

| volba | co dělá |
|---|---|
| `--format {xlsx,csv,both}` | formát výstupu (výchozí `xlsx`) |
| `--limit N` | zpracuje jen prvních N produktů — pro rychlý test |
| `--headed` | ukáže prohlížeč při běhu, vidíš co se děje |
| `--out zaklad_nazvu` | vlastní název/umístění výstupu (bez přípony) |
| `--no-session` | běží bez přihlášení, otiskne jen veřejně dostupnou část |
| `--dry-run` | provede celý scrape, ale nic nezapíše — jen ukáže souhrn (kolik řádků, zamčených, chyb) |
| `--types typ1,typ2` | uloží jen dané typy souboru (např. `pdf` nebo `pdf,dwg`), výchozí `all` = všechny |
| `--category text,text` | filtr produktů podle kategorie z rozcestníku (substring, čárkou oddělené varianty) |
| `--brand text,text` | filtr produktů podle značky (substring) |
| `--product-type text,text` | filtr produktů podle typu produktu (substring) |
| `--section text,text` | filtr dokumentů podle sekce (substring) — na rozdíl od předchozích tří se aplikuje až po načtení produktové stránky |

Filtry jsou substring match a nezáleží u nich ani na velikosti písmen, ani
na diakritice — `--section "technicke listy"` najde i `Technické listy`.
`--category`/`--brand`/`--product-type` navíc filtrují produkty ještě před
otevřením jejich stránky, takže běh je i rychlejší.

### Výchozí nastavení (`config.txt`)

Většina těch voleb se dá nastavit jako výchozí i bez psaní do příkazové
řádky — v textovém souboru `config.txt` v kořeni projektu:

```
format = csv
types = pdf,dwg
category = vzduch/voda
```

Cokoliv zadané přímo v příkazové řádce (`--format xlsx` apod.) config pro
daný běh přebije — je to jen výchozí hodnota. Prázdný řádek/klíč = žádné
omezení (chová se jako kdyby tam nic nebylo). Řádky začínající `#` jsou
komentář. Soubor je celý volitelný — bez něj platí vestavěné výchozí
hodnoty (`format=xlsx`, `types=all`, žádné filtry). Nápověda
(`python protc_otisk.py`) rovnou ukazuje, jaký je aktuálně nastavený
výchozí `--format`/`--types` podle `config.txt`.

Příklady:

```bash
python protc_otisk.py snapshot --limit 3 --headed        # rychlý test na 3 produktech
python protc_otisk.py snapshot --format both             # xlsx i csv naráz
python protc_otisk.py snapshot --out muj_export --format csv
# -> muj_export.csv (mimo exports/, protoze --out zada vlastni cestu)
python protc_otisk.py snapshot --types pdf                # jen PDF dokumenty
python protc_otisk.py snapshot --types pdf,dwg             # jen PDF a DWG
python protc_otisk.py snapshot --category "vzduch/voda" --brand ivt   # jen IVT vzduch/voda
python protc_otisk.py snapshot --section "Technické listy"            # jen jedna sekce
python protc_otisk.py snapshot --dry-run                   # jen souhrn, nic se nezapise
```

Malý banner (`PROTC_OTISK — by Kotršál`) se ukáže jen **jednou**, když
nástroj „naskočí" — bez podpříkazu (`python protc_otisk.py`), na `--help`,
nebo v `START-mac.command` po dvojkliku — ne při každém jednotlivém `login`/
`snapshot`, ať se v terminálu neopakuje. V `START-mac.command` navíc `clear`
kromě smazání obrazovky rovnou znovu ukáže banner + nápovědu, hodí se to
jako připomínka, jak se nástroj ovládá.

Běh na celý web trvá řádově několik minut (naposledy ~72 produktů, ~2400
dokumentů). V konzoli se postup ukazuje jako **zelený progress bar**
(`[####------]  40%  29/72  ETA ~48s`), který se přepisuje na místě —
detailní řádek s časem a počtem dokumentů za každý produkt jde jen do log
souboru. Barvy fungují na Macu/Linuxu automaticky a na Windows 10+ se
zapnou samy; na starším Windows nebo při přesměrování výstupu do souboru se
prostě vypíše bez barev, nic se tím nerozbije. Než se rozeběhne celý crawl,
`snapshot.py` (pokud nemáš `--no-session`) nejdřív ověří, že `session.json`
ještě platí — díky tomu neběží zbytečně přes všechny produkty s vypršenou
session. Když produkt při scrapování selže, zkusí se to ještě 2× znovu,
teprve pak se počítá jako chyba.

Při překlepu ve volbě nebo podpříkazu (`--tyeps` místo `--types`, `snpashot`
místo `snapshot`) nástroj sám navrhne nejbližší platnou variantu.

## Ladění a logy

Ke každému běhu `snapshot.py` (i `login.py`) vzniká log v `logs/` se stejným
časovým razítkem jako má výstup. V logu je:

- postup běhu (kolik produktů nalezeno, kolik dokumentů u každého, jak
  dlouho to trvalo, ETA) — tyhle detailní řádky jdou jen do souboru, na
  konzoli místo nich běží progress bar,
- **plný Python traceback** u každé chyby — ať už selhal jeden produkt po
  vyčerpání všech pokusů, nebo spadl celý běh.

Když něco nesedí (0 produktů, 0 dokumentů, pád uprostřed běhu), nejdřív se
podívej do odpovídajícího souboru v `logs/` — tam je vidět přesně, co a kde
selhalo.

## Výstupní sloupce

| sloupec | co obsahuje |
|---|---|
| `kategorie` | nadpis skupiny produktů na rozcestníku, např. *ZEMĚ/VODA pro jednoduché instalace v menších budovách 4 až 20 kW* |
| `znacka`, `typ_produktu` | např. IVT / GEO 700 |
| `sekce` | *Technické listy*, *Návody pro obsluhu a instalaci*, … |
| `poradi_v_sekci` | 1, 2, 3… (celé číslo; řádek s víc soubory dostane dvě po sobě jdoucí čísla, ne desetinné) |
| `popis_dokumentu` | popis dokumentu z webu, např. *NKS 21 \| Technický list* |
| `typ_souboru` | PDF / DWG |
| `nazev_souboru` | text odkazu, např. `technicky_list_ivt_nks21` |
| `velikost` | např. `95,1 kB` |
| `poznamka` | poznámka u dokumentu, pokud nějaká je |
| `url_stazeni` | skutečná URL ke stažení; prázdné = dokument je zamčený |

Podrobnosti o tom, jak se tyhle hodnoty ze stránky vytahují, jsou v
[JAK_TO_FUNGUJE.md](JAK_TO_FUNGUJE.md).

## Co nástroj neumí (zatím)

- **Neporovnává** dva otisky mezi sebou — dřívější `compare.py` byl
  odstraněný, nástroj teď dělá jen otisk. Kdyby bylo potřeba sledovat
  změny v čase, dá se to postavit nad výstupní CSV soubory samostatně.
- **Nestahuje** samotné PDF/DWG soubory, jen zaznamenává metadata (kde jsou,
  jak se jmenují, jak jsou velké).

## Zásady

- `session.json` se negituje do repozitáře (obsahuje přihlašovací cookies).
- `exports/` a `logs/` se taky negitují — je to lokálně vygenerovaná data.
- `.venv/` se negituje — je to lokální virtuální prostředí (desítky-stovky
  MB), po naklonování si ho každý vytvoří sám (`python3 -m venv .venv`
  nebo prostě první spuštění `START-*` skriptu).
- Mezi požadavky na web nech rozumné tempo, nespouštěj to zbytečně často.
