# Jak PROTC_OTISK funguje uvnitř

Tenhle dokument vysvětluje **mechaniku** nástroje — proč je udělaný zrovna
takhle a co dělá který kus kódu. Jak ho ovládat je popsáno v
[README.md](README.md).

## Základní myšlenka

Web `projektuj-tepelna-cerpadla.cz` v sekci Dokumentace ke stažení nabízí u
každého produktu (tepelného čerpadla) sadu ke stažení dostupných dokumentů
— technické listy, návody, projekční podklady, schémata zapojení atd.
Časem se tyhle dokumenty **přejmenovávají** (např. `technicky_list_v1.pdf`
→ `technicky_list_v2.pdf`), ale nepřidávají se ani nemažou nijak často —
zůstávají na svém místě v sekci.

PROTC_OTISK prochází web jako běžný přihlášený uživatel (přes headless prohlížeč
Playwright, ne přes syrové HTTP požadavky, protože stránka je vykreslovaná
JavaScriptem) a pro každý dokument zaznamená: kde je (produkt + sekce +
pořadí v sekci), jak se jmenuje popis, jak se jmenuje soubor, jaký má typ,
velikost a poznámku. Výsledek uloží do Excelu/CSV.

Nástroj **sám o sobě dokumenty nesrovnává** ani nesleduje historii — jen
udělá jeden "otisk" aktuálního stavu. (Dřív k tomu existoval `compare.py`,
který uměl diff dvou otisků; byl odstraněný — viz [README.md](README.md#co-nástroj-neumí-zatím).)

## Soubory a jejich role

```
protc_otisk.py        tenký CLI dispatcher — "python protc_otisk.py login/snapshot"
login.py              KROK 1: rucni prihlaseni -> session.json
snapshot.py           KROK 2: crawler -> exports/*.xlsx, exports/*.csv, logs/*.log
extractor.py          sdilene pomocne funkce pro snapshot.py + login.py
config.txt            volitelne vychozi hodnoty pro snapshot (format, types, filtry, ...)
requirements.txt      zavislosti (playwright, openpyxl)

START-mac.command     spusteni na Mac dvojklikem ve Finderu
START-windows.bat     spusteni na Windows dvojklikem v Exploreru
START-linux.sh        spusteni na Linuxu (a na Macu z terminalu) prikazem ./START-linux.sh

.venv/                virtualni prostredi (lokalni, negituje se)
session.json          ulozene prihlasovaci cookies (negituje se)
exports/              vystupy snapshot.py
logs/                 logy behu snapshot.py a login.py
```

### `START-*` — spouštěcí skripty (jeden pro každý systém)

Tři soubory, jméno rovnou napovídá, pro koho je který — cíl je, aby si
kolega, co si stáhne složku poprvé, nemusel nic domýšlet a věděl na první
pohled, co spustit:

- **`START-mac.command`** — dvojklik ve Finderu na Mac.
- **`START-windows.bat`** — dvojklik v Exploreru na Windows.
- **`START-linux.sh`** — `./START-linux.sh <příkaz>` z terminálu; funguje i
  na Macu pro toho, kdo preferuje terminál před dvojklikem (dvojklik na
  `.sh` ve Finderu ho ale **nespustí** — macOS ho jen otevře v editoru,
  proto pro Mac existuje zvlášť `START-mac.command`).

`START-linux.sh`/`START-windows.bat` řeší dvě věci: (1) aktivaci `.venv`
(a při úplně prvním spuštění i jeho vytvoření + `pip install` +
`playwright install chromium`), (2) předání všech argumentů beze změny do
`python protc_otisk.py "$@"` (Bash) / `%*` (Batch). Díky tomu se dá psát
`./START-linux.sh snapshot --limit 3` místo `source .venv/bin/activate &&
python protc_otisk.py snapshot --limit 3`. Žádná vlastní logika navíc —
chová se identicky jako ruční varianta, jen s méně psaním. `START-linux.sh`
má nastavený spustitelný bit (`chmod +x`). `START-windows.bat` navíc na
konci přidá `pause`, ale **jen** když nedostal žádné argumenty (typicky
dvojklik) — jinak by se cmd okno po doběhnutí hned zavřelo a nešlo by
přečíst, co vypsalo; při spuštění s argumenty z už otevřeného terminálu se
`pause` přeskočí.

`START-mac.command` dělá skoro totéž co `START-linux.sh` — aktivuje/vytvoří
`.venv` — ale se dvěma rozdíly: (1) nemůže přijmout argumenty (dvojklik
žádné nepředá), takže po aktivaci `.venv` spustí `python protc_otisk.py`
bez argumentů — to vypíše celou nápovědu (`build_usage()` z `protc_otisk.py`,
viz níže), takže je hned vidět, jak se nástroj ovládá, (2) na konci
nahradí proces skriptu interaktivním shellem (viz „`START-mac.command` a
`clear`" níže), takže terminálové okno po doběhnutí "nezmizí" a jde v něm
rovnou psát příkazy s aktivním `.venv`. Taky má nastavený `chmod +x`.

Na úplném začátku `START-mac.command` je ještě jeden `osascript` příkaz —
zvětší okno Terminálu (`bounds of front window`) na `{80, 80, 1180, 800}`,
aby se po dvojkliku (Terminal.app defaultně otevírá menší okno) vešlo víc
textu najednou. Velikost písma se záměrně nemění, jede na uživatelském
defaultu. Funguje jen v `Terminal.app` (ne v jiných terminálech jako
iTerm), proto je zabalený v `|| true` — když selže, zbytek skriptu běží dál
beze změny.

### `protc_otisk.py` — vstupní bod

Nejtenčí vrstva celého nástroje. Nedělá žádnou vlastní logiku — jen se
podívá na první argument (`login` / `snapshot`), odstraní ho ze `sys.argv`
a zavolá `main()` z odpovídajícího souboru. Díky tomu zbylé argumenty
(`--limit`, `--headed`, …) doletí beze změny do `argparse` uvnitř
`snapshot.py`, jako by ses ho spustil přímo.

Nápověda (dřív statický řetězec `USAGE`) je teď funkce `build_usage()` —
zavolá `load_config()` a do textu vloží skutečně nastavený `--format`/
`--types` default z `config.txt` (`(vychozi: {format_default})`), takže
nápověda vždycky odpovídá tomu, jak se nástroj opravdu chová, ne natvrdo
napsanému textu. Volá se ze dvou míst: cesta bez podpříkazu/`--help` a
cesta s neznámým příkazem — ne z cesty, která dispatchuje do `login.py`/
`snapshot.py` (ty mají vlastní `print_banner()` ve svém `main()`, aby se
neduplikoval banner).

### `login.py` — přihlášení

Otevře **viditelný** prohlížeč (`headless=False`) na přihlašovací stránce a
počká, až se uživatel ručně přihlásí a stiskne v terminálu Enter. Skript
nikdy neuvidí heslo — jen si po přihlášení vezme stav prohlížeče
(`context.storage_state()`, tj. cookies a local storage) a uloží ho do
`session.json`. Tenhle soubor pak `snapshot.py` použije, aby otevíral
stránky už jako přihlášený uživatel, bez opětovného zadávání hesla.

Po přihlášení se skript ověří přes `check_session()` z `extractor.py` —
otevře stránku produktu GEO 700 a spočítá, kolik odkazů má
`href="javascript:;"` (zamčené) a kolik `download=` (reálné stažení).
Pokud je zamčených moc a stažení málo, přihlášení pravděpodobně nevyšlo a
skript to nahlásí. Stejnou funkci používá i `snapshot.py` — viz níže.

Session časem vyprší (web ji zneplatní) — pak stačí `login.py` spustit
znovu, přepíše se `session.json`.

### `extractor.py` — sdílené pomocné funkce

- `find_size(text)` — regexem vytáhne z textu řádku velikost souboru, např.
  `167 kB`.
- `is_locked(href)` / `is_download(href)` — pozná, jestli je odkaz zamčený
  (`javascript:;`, prázdný) nebo skutečné stažení.
- `file_path_from_href(abs_href)` — z absolutní URL typu
  `.../?download=_/product.82/soubor.pdf` vytáhne stabilní cestu
  `_/product.82/soubor.pdf` (bez domény a bez `?download=`), která
  jednoznačně identifikuje soubor napříč produkty.
- `check_session(page, check_url)` — otevře stránku GEO 700, spočítá
  zamčené (`javascript:;`) vs. stažitelné (`download=`) odkazy a vrátí
  `{"locked", "downloads", "ok"}`. Sdílí ji `login.py` (ověření hned po
  přihlášení) a `snapshot.py` (ověření před začátkem celého crawlu) — dřív
  měl každý skript vlastní kopii téhle logiky, teď je na jednom místě.
- `GREEN`/`BOLD_GREEN`/`DIM`/`RESET` — ANSI escape kódy pro barvy, `enable_ansi()`
  a `print_banner()` — viz samostatná sekce
  [Banner a barvy](#banner-a-barvy-print_banner-enable_ansi) níže.

Soubor obsahuje i `JS_EXTRACT_TABLES`, `header_index` a `cell` — to je
**stará, dnes nepoužívaná** cesta z doby, kdy web zobrazoval dokumenty v
`<table>`. `snapshot.py` ji dnes vůbec neimportuje. Nechává se tu pro
referenci, ale při čtení kódu ji lze ignorovat.

### `snapshot.py` — hlavní crawler

Tohle je jádro nástroje. Postup:

0. **Ověření session** (`check_session`) — pokud není `--no-session`, hned
   po otevření prohlížeče (ještě před čtením rozcestníku!) se ověří, že
   `session.json` platí. Při mrtvé session skript rovnou skončí chybou —
   nemá smysl čekat minuty na projetí desítek produktů, když jsou stejně
   všechny zamčené.

1. **Rozcestník** (`scrape_index`) — otevře
   `/cz/dokumentace-ke-stazeni` a v prohlížeči spustí JS `JS_INDEX`, který
   posbírá všechny odkazy s textem „Vybrat" (to jsou odkazy na produktové
   stránky). Ke každému dohledá kategorii (nejbližší nadpis skupiny nad
   ním) a značku/typ produktu ze sousedních polí v řádku. Vrátí seznam
   produktů `{kategorie, znacka, typ_produktu, produkt_url}`.

   Hned po `scrape_index` se (pokud jsou zadané) aplikují filtry
   `--category`/`--brand`/`--product-type` na seznam `products` — dřív, než
   se otevře jediná produktová stránka. Teprve pak přijde na řadu `--limit`.

2. **Produktová stránka** (`scrape_product`) — pro každý produkt otevře
   jeho stránku a spustí JS `JS_PRODUCT` (podrobnosti níže), který vrátí
   syrový seznam řádků dokumentů. Python kód je pak seskupí a očísluje —
   viz [Jak se skládá pořadí dokumentů](#jak-se-skládá-pořadí-dokumentů).
   Když `scrape_product` spadne, `main()` to zkusí ještě 2× (`MAX_POKUSU=3`
   celkem, s `page.wait_for_timeout(1500)` mezi pokusy) — teprve poslední
   neúspěšný pokus se počítá do `chyby` a loguje s tracebackem. U každého
   produktu se navíc loguje doba trvání a ETA (odhad zbývajícího času,
   spočtený z průměrné doby na produkt dosud) — ale jen **do log souboru**
   (viz `ProgressBar` níže).

3. **Filtry `--types`/`--section`** — na rozdíl od filtrů produktů (bod 1)
   se aplikují **až na hotové `records`**, protože `typ_souboru` (u
   víc-souborových řádků) i `sekce` se dopočítávají/zjišťují až při čtení
   produktové stránky, ne na rozcestníku.

4. **Zápis** (`write_xlsx` / `write_csv`) — podle volby `--format` zapíše
   posbírané záznamy do Excelu (`openpyxl`, s hlavičkou, barvami, filtrem a
   samostatným listem „Info") a/nebo do CSV (`;`-oddělovač,
   `utf-8-sig` kódování, aby se čeština správně otevřela i v Excelu na
   macOS). Volba `--dry-run` tenhle krok úplně přeskočí — scrape i filtry
   proběhnou normálně, jen se nikam nezapíše (hodí se na rychlou kontrolu
   počtů bez vytváření souboru).

5. **Logování** (`setup_logging`) — na začátku běhu se založí logger, který
   zapisuje současně do konzole i do souboru v `logs/`. Každá chyba při
   scrapování jednotlivého produktu i neočekávaný pád celého běhu se
   zaloguje přes `logger.exception(...)`, což do logu přidá **celý
   traceback** — proto se dá zpětně přesně dohledat, kde a proč to
   spadlo.

### Jak DOM na produktové stránce vypadá

Klíčové zjištění (ověřené přímo v prohlížeči): stránka **nepoužívá**
`<table><tr><td>` pro seznam dokumentů. Místo toho je to `<div>` layout:

```
div.toggle-block                    <- cely blok jedne sekce
  div.toggle-block-title            <- nadpis sekce (vizualne vypada jako <h2>)
    div.toggle-block-title-text     <- text nadpisu
  div.toggle-block-trow             <- jeden radek/dokument
    div                            <- [0] Popis dokumentu
    div                            <- [1] Typ (PDF / DWG / Odkaz...)
    div.url                        <- odkaz ke stazeni
      a[href="/?download=..."]     <- prihlaseny: realny odkaz se souborem
      a[href="javascript:;"]       <- neprihlaseny: zamek
    div.note                       <- Poznamka
```

`JS_PRODUCT` (JS spuštěný přímo ve stránce) projde všechny
`.toggle-block-trow` divy a pro každý:

- přeskočí hlavičkové řádky (řádek, kde první div je doslova „Popis
  dokumentu"),
- k řádku dohledá sekci — nejbližší rodič `.toggle-block`, jeho
  `.toggle-block-title-text` (s cache podle rodiče, ať se to nepočítá
  pořád dokola),
- posbírá odkazy uvnitř řádku. Každý reálný odkaz na stažení má vedle sebe
  v DOM ještě jeden **prázdný ikonkový** `<a>` se stejným `href` — ten se
  odfiltruje podmínkou, že text odkazu (`innerText`) není prázdný,
- pozná zamčený dokument podle `href === 'javascript:;'`.

Sekce, které nejsou skutečnou kategorií dokumentů, ale marketingový/
informační blok bez dokumentů (`Aktuální informace o dostupnosti výrobku`),
se v `EXCLUDED_SECTIONS` rovnou zahazují vždy.

Sekce `Nejvyhledávanější dokumenty` je jiný případ — jsou to skutečné
dokumenty, jen duplicitní s tím, co je i v jiných sekcích níž na stránce.
Proto se ve výchozím stavu taky zahazuje (`NEJVYHLEDAVANEJSI_SECTION`), ale
jde to zapnout volbou `--nejvyhledavanejsi` (nebo `nejvyhledavanejsi = true`
v `config.txt`) — `scrape_product` pak dostane `include_nejvyhledavanejsi=True`
a sekci zaznamená jako kteroukoliv jinou.

### Jak se skládá pořadí dokumentů

Python část `scrape_product` dostane ze `JS_PRODUCT` plochý seznam
"syrových" řádků a nejdřív je seskupí (`grouped`) — nový záznam vznikne,
kdykoliv se změní sekce nebo popis dokumentu. Díky tomu skončí v jedné
skupině i řádek, který má **dva soubory najednou** (typicky schéma
zapojení jako PDF + DWG).

Poté se každé skupině přidělí číslo pořadí **per soubor, ne per řádek** —
`sekce_poradi` je čítač pro každou sekci zvlášť a `poradi_v_sekci` je prosté
celé číslo. Řádek se dvěma soubory (např. schéma jako PDF + DWG) tak
dostane dvě po sobě jdoucí celá čísla — třeba `12` pro PDF a `13` pro DWG,
ne desetinný zápis.

Interně se pro každý dokument spočítá i `klic` =
`produkt_url|sekce|poradi` — stabilní identifikátor pozice řádku. Do
výstupního xlsx/csv se ale nezapisuje (není v `COLUMNS`), protože nástroj
sám nic neporovnává; je tu pro případ, že by ho chtěl použít nějaký
navazující skript.

### Sloupce, které se počítají, ale nezapisují

`scrape_product` si pro každý dokument spočítá víc polí, než kolik jich
nakonec skončí v exportu. `COLUMNS` (seznam nahoře v `snapshot.py`) určuje,
co se skutečně zapíše. Navíc se počítají a zahazují:

- `klic` — viz výše,
- `produkt`, `produkt_url` — název (H1) a adresa produktové stránky,
- `cesta_souboru` — cesta k souboru vytažená z `?download=...` (bez
  domény),
- `dostupnost` — `"ke stazeni"` / `"zamceno / nedostupne"`, odvozeno od
  `url_stazeni`.

Důvod: tahle pole jsou buď odvoditelná z jiných sloupců (`dostupnost` z
prázdnoty `url_stazeni`), nebo jsou relevantní jen v kontextu jednoho
běhu (`produkt_url` je stejná pro všechny řádky daného produktu). Kdyby
byly potřeba, stačí je do `COLUMNS` přidat.

## Výchozí hodnoty z config.txt

`load_config()` (`extractor.py`) přečte `config.txt` řádek po řádku,
rozdělí ho podle prvního `=` na `klic` a `hodnota`, ořízne mezery a vrátí
obyčejný `dict[str, str]`. Řádky bez `=`, prázdné a komentáře (`#`) se
přeskočí. Chybějící soubor → prázdný dict (žádná chyba) — `config.txt` je
tedy celý volitelný.

`snapshot.py` zavolá `load_config()` na začátku `main()`, ještě před
sestavením `argparse.ArgumentParser()`, a použije hodnoty z configu jako
`default=` pro odpovídající volby:

- textové (`format`, `types`, `category`, `brand`, `product_type`,
  `section`) — `cfg.get("klic") or None`/`"vestaveny_default"`,
- boolean (`headed`, `no_session`, `dry_run`) — přes `cfg_bool(cfg, "klic")`,
  který porovná ořízlou/malými písmeny hodnotu proti
  `("1", "true", "ano", "yes")`.

Protože je to jen `default=` v `argparse`, běžné pravidlo platí beze změny:
cokoliv zadané přímo v příkazové řádce (`--format xlsx`) config.txt pro
daný běh přebije. `--limit` a `--out` v `config.txt` záměrně nejsou —
`--limit` je typicky jednorázová věc pro test, `--out` mění umístění
výstupu, což by se snadno pletlo s výchozím `exports/snapshot_<timestamp>`
schématem.

## Filtr typu souboru (`--types`)

Volba `--types` (výchozí `all`) umožňuje otisknout jen vybrané typy souborů,
např. `--types pdf` nebo `--types pdf,dwg`. Filtrování se dělá **až po**
scrapu celého webu — `scrape_product` posbírá úplně všechno jako doteď,
teprve v `main()` se `records` prožene podmínkou na `typ_souboru` (převedeno
na velká písmena, porovnáno proti množině zadaných typů) předtím, než se
zapíše xlsx/csv. Do logu se napíše, kolik řádků filtr odstranil
(`Filtr --types pdf: 331 -> 277 radku`).

Filtruje se záměrně pozdě (ne už v `JS_PRODUCT` nebo `scrape_product`),
protože `typ_souboru` se v Pythonu dopočítává až při skládání záznamu (u
řádků s víc soubory v jedné buňce, např. schéma PDF+DWG, se přebírá z
přípony souboru, ne z textu na webu) — filtrovat dřív by znamenalo tuhle
logiku duplikovat.

## Filtr produktů/kategorie a diakritika (`--category`, `--brand`,
   `--product-type`, `--section`)

Všechny čtyři filtry používají stejné dvě funkce v `main()`:

- `normalize(s)` — přes `unicodedata.normalize("NFKD", s)` rozloží znaky
  s diakritikou na základní písmeno + kombinující znak, ten kombinující
  znak zahodí (`unicodedata.combining(c)`) a převede na malá písmena. Díky
  tomu `normalize("Technické")` a `normalize("technicke")` dají stejný
  výsledek.
- `matches_any(text, substrings)` — normalizuje `text` a zkontroluje, jestli
  v něm je jako substring aspoň jedna z předem normalizovaných hledaných
  variant (`parse_substrings` je normalizuje hned při parsování `--category`
  apod.).

`--category`/`--brand`/`--product-type` filtrují `products` hned po
`scrape_index`, tedy **před** otevřením jednotlivých produktových
stránek — šetří to čas. `--section` filtruje až `records` po scrapu,
protože sekce se pozná teprve na produktové stránce.

## Měření času a progress bar (`--limit`, log, konzole)

Každý běh loguje dobu trvání jednotlivého produktu i celého běhu přes
`time.perf_counter()`, ale na konzoli a v log souboru se to projevuje jinak:

- **log soubor** dostává detailní řádek za každý produkt (počet dokumentů,
  doba trvání, ETA) — loguje se s `extra={"file_only": True}`,
- **konzole** místo toho ukazuje jednořádkový `ProgressBar`
  (`[####------]  40%  29/72  ETA ~48s`), který se po každém produktu
  přepíše přes `\r` (`ProgressBar.update()`). Detailní řádky se na konzoli
  potlačí přes `_ConsoleFilter` (logging filtr na konzolovém handleru,
  vynechá záznamy s `file_only=True`). Progress bar se úplně přeskočí, když
  `sys.stdout.isatty()` je `False` (výstup přesměrovaný do souboru/roury) —
  nemá smysl tam plnit `\r` znaky.
- Než se vypíše `logger.warning`/`logger.exception` uprostřed běhu (retry,
  chyba produktu), zavolá se `bar.interrupt()` — ukončí rozepsaný řádek
  baru novým řádkem, aby se do něj zpráva nezamíchala; bar pak pokračuje na
  nové čisté řádce.
- na konci běhu (`main()`) se měří čas od otevření prohlížeče až po zápis
  výstupu a vypíše se v sekci „Hotovo" jako `celkovy cas behu`.
- vyplněná část baru (`#` znaky) je obarvená zeleně (`extractor.GREEN` +
  `RESET` kolem, viz [Banner a barvy](#banner-a-barvy-print_banner-enable_ansi)
  níže) — nevyplněná část (`-`) zůstává bez barvy.

## Banner a barvy (`print_banner`, `enable_ansi`)

`print_banner()` z `extractor.py` vypíše malé ASCII logo, `PROTC_OTISK`
(tučně zeleně) a `by Kotrsal` (tlumeně). Jde čistě o `print()` na `stdout`,
ne přes `logger`, takže se banner neobjeví v log souboru (to je záměr — log
má obsahovat jen věcný průběh běhu).

Volá se **jen z `protc_otisk.py`** (cesta bez podpříkazu, `--help`, nebo
neznámý příkaz) — `login.py` a `snapshot.py` ho ve svém `main()` už
nevolají. Dřív ho volal každý ze tří (protc_otisk.py i oba podpříkazy), což
znamenalo, že se banner objevil znovu při každém jednotlivém příkazu v
jedné terminálové seanci (typicky v `START-mac.command`, kde uživatel napíše víc
příkazů za sebou) — rušivé opakování stejné grafiky. Teď se banner ukáže
jen jednou, „při nahození" nástroje, a zůstává nahoře ve scrollbacku.
Vedlejší efekt: při přímém spuštění `python snapshot.py`/`python login.py`
(bez `protc_otisk.py`) se banner vůbec neukáže — akceptovaný kompromis,
hlavní cesta je přes `protc_otisk.py`/`START-linux.sh`/`START-mac.command`.

**`START-mac.command` a `clear`** — po vypsání banneru+nápovědy na startu skript
`START-mac.command` nepoužije prostý `exec "$SHELL"`, ale sestaví dočasný shell
profil (přes `mktemp`), který navíc předefinuje `clear` jako funkci:
`command clear` (skutečné smazání obrazovky) + `python protc_otisk.py`
(banner+nápověda znovu). Platí jen v tomhle jednom terminálovém okně — pro
zsh se to řeší přes dočasný `ZDOTDIR` (obsahuje `.zshrc`, který nejdřív
nasourcuje uživatelův skutečný `~/.zprofile`+`~/.zshrc`, pak přidá `clear`),
pro bash přes `--rcfile`. Pro cokoliv jiného (neznámý `$SHELL`) skript
spadne zpátky na obyčejný `exec "$SHELL"` beze změny.

**Napovídání překlepů** — `difflib.get_close_matches()`:
- `protc_otisk.py` ho použije na neznámý podpříkaz (`snpashot` →
  „Možná jsi myslel: 'snapshot'?"), porovnává proti `COMMANDS = ("login",
  "snapshot")`,
- `snapshot.py` použije `ap.parse_known_args()` místo `ap.parse_args()` —
  cokoliv, co argparse nerozpozná, skončí v `neznamo` místo aby rovnou
  spadlo s obecnou hláškou; pro každou neznámou `--volbu` se najde
  nejbližší z `ap._actions` (`cutoff=0.4`) a navrhne se.

Pozor na past: argparse defaultně povoluje **zkrácené** dlouhé volby
(`allow_abbrev=True`) — `--forma` se tiše vyhodnotí jako `--format`, pokud
je to jednoznačná zkratka, takže se `neznamo`/návrh vůbec nespustí. Není to
překlep, je to platná zkratka.

Mechanika barev:

- `GREEN`, `BOLD_GREEN`, `DIM`, `RESET` — konstanty s ANSI escape kódy
  (`\033[32m` apod.).
- `_c(code)` — vrátí daný kód, jen když `sys.stdout.isatty()` je pravda;
  jinak prázdný řetězec. Používá ho jak `print_banner()`, tak (přes přímý
  import `GREEN`/`RESET`) `ProgressBar.update()` v `snapshot.py`. Díky
  tomu se při přesměrování výstupu (`> vystup.txt`, roura do `tail` apod.)
  nikdy nezapíšou syrové escape sekvence — jen čistý text.
- `enable_ansi()` — na Windows (`os.name == "nt"`) zavolá `ctypes`/
  `kernel32.SetConsoleMode` s příznakem `ENABLE_VIRTUAL_TERMINAL_PROCESSING`,
  aby `cmd.exe`/PowerShell vůbec začaly ANSI kódy interpretovat jako barvy
  (ve Windows 10+ to jinak ve výchozím stavu není zapnuté). Na Mac/Linux se
  rovnou vrátí (`if os.name != "nt": return"`) — ANSI tam funguje bez
  zásahu. Celé tělo je v `try/except Exception: pass` — když se to na
  nějaké starší/neobvyklé Windows konfiguraci nepovede, běh pokračuje dál
  bez barev, nic se nerozbije. Volá se automaticky z `print_banner()`, není
  potřeba ji volat zvlášť.
- Žádná nová závislost (ne `colorama`) — jen `ctypes` z standardní
  knihovny.

## Přihlášený vs. nepřihlášený stav

| | nepřihlášený | přihlášený |
|---|---|---|
| zamčený dokument | `href="javascript:;"` | `href="/?download=cesta/soubor.pdf"` |
| velikost souboru | chybí | vidět v textu řádku |
| `dostupnost` v exportu | `zamceno / nedostupne` | `ke stazeni` |

`snapshot.py` bez `session.json` (nebo s `--no-session`) proto pořídí jen
částečný, veřejně viditelný otisk — hodí se to jako rychlý test, ne jako
plnohodnotný běh.

## Formáty odkazů ke stažení

- `?download=_/product.82/nazev.pdf` — soubor specifický pro daný produkt
  (číslo `82` je interní ID produktu na webu)
- `?download=Kalle/IVT/Manualy/nazev.pdf` — sdílený soubor, používaný napříč
  víc produkty (typicky obecné manuály/návody)

## Výstupní soubory a jejich pojmenování

Každý běh `snapshot.py` (pokud nezadáš vlastní `--out`) vytvoří:

```
exports/snapshot_<RRRRMMDD_HHMMSS>.xlsx   (a/nebo .csv, podle --format)
logs/snapshot_<RRRRMMDD_HHMMSS>.log
```

Časové razítko je **shodné** pro export i log stejného běhu — díky tomu se
k libovolnému starému exportu dá dohledat přesně odpovídající log a
zjistit, co se při jeho vytváření dělo (kolik produktů, jestli něco
selhalo, atd.). Formát `RRRRMMDD_HHMMSS` (bez pomlček/dvojteček) je zvolen
schválně, ať je bezpečný jako název souboru na všech systémech.

## Odolnost vůči změnám webu

Kód se záměrně neopírá o generické CSS třídy jako `container`/`row`, které
se při redesignu snadno změní, ale o specifické, sémanticky pojmenované
třídy webu (`toggle-block`, `toggle-block-trow`, …) a strukturu DOM. Pokud
web projde větší změnou layoutu, nejpravděpodobnější příznaky jsou:

- `scrape_index` vrátí 0 produktů → změnil se rozcestník (odkazy „Vybrat"
  nebo obalující struktura),
- `scrape_product` vrátí 0 dokumentů u všech produktů → buď se změnily
  třídy `.toggle-block-trow`, nebo vypršela session.

V obou případech pomůže spustit `snapshot.py --headed --limit 1` a podívat
se, co se v prohlížeči skutečně stane, případně prozkoumat DOM ručně přes
vývojářské nástroje prohlížeče.
