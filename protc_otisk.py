"""
Univerzalni vstupni bod pro PROTC_OTISK - misto pameti "login.py / snapshot.py"
si pamatujes jen jeden prikaz s podprikazem (stejny princip jako
`git commit`, `git push` - "CLI s subcommandy").

Pouziti:
    python protc_otisk.py login
    python protc_otisk.py snapshot
    python protc_otisk.py snapshot --limit 3 --headed

Kazdy podprikaz jen zavola main() z prislusneho puvodniho souboru - zadna
logika se nemeni, tohle je jen pohodlnejsi obal.
"""

import difflib
import sys

from extractor import print_banner, load_config

COMMANDS = ("login", "snapshot")


def build_usage():
    """Sestavi napovedu s aktualnimi vychozimi hodnotami z config.txt (napr.
    kdyz je tam nastaveny format=csv, napoveda rovnou ukaze '(vychozi: csv)'
    misto natvrdo napsaneho 'xlsx')."""
    cfg = load_config()
    format_default = cfg.get("format") or "xlsx"
    types_default = cfg.get("types") or "all"

    return f"""\
Pouziti:
  python protc_otisk.py login              prihlaseni (ulozi session.json)
  python protc_otisk.py snapshot [volby]   vytvori otisk -> exports/

Volby snapshotu:
  --format {{xlsx,csv,both}}    format vystupu (vychozi: {format_default})
  --limit N                    jen prvnich N produktu (rychly test)
  --headed                     zobrazit prohlizec pri behu
  --out zaklad_nazvu           vlastni nazev/umisteni vystupu (bez pripony)
  --no-session                 bez prihlaseni, jen verejna cast webu
  --dry-run                    scrape bez zapisu, jen ukaze souhrn
  --types pdf,dwg,...          jen dane typy souboru (vychozi: {types_default})
  --category text,text         filtr kategorie (substring, bez diakritiky)
  --brand text,text            filtr znacky (substring, bez diakritiky)
  --product-type text,text     filtr typu produktu (substring, bez diakritiky)
  --section text,text          filtr sekce dokumentu (substring, bez diakritiky)

Vychozi hodnoty (format, types, filtry, ...) se daji zmenit v config.txt,
aniz by bylo nutne je pokazde psat v prikazove radce. Podrobny popis chovani
kazde volby: README.md

Priklad:
  python protc_otisk.py snapshot --limit 3 --headed
  python protc_otisk.py snapshot --category vzduch --types pdf
"""


def main():
    # Banner se vypisuje jen tady - pri "nahozeni" nastroje (bez podprikazu,
    # --help, nebo neznamy prikaz). "login"/"snapshot" uz banner znovu
    # netisknou, aby se neopakoval pri kazdem jednotlivem prikazu v jedne
    # terminalove seanci (napr. z START-mac.command) - banner se objevi jen jednou
    # nahore a zustane tam.
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_banner()
        print(build_usage())
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    cmd = sys.argv.pop(1)  # odstrani podprikaz, zbytek argv necha pro dany skript

    if cmd == "login":
        import login
        login.main()
    elif cmd == "snapshot":
        import snapshot
        snapshot.main()
    else:
        print_banner()
        print(f"Neznamy prikaz: {cmd!r}\n")
        if cmd.startswith("-"):
            # castá chyba: volba napsana rovnou za protc_otisk.py bez
            # podprikazu, napr. "protc_otisk.py --format csv" misto
            # "protc_otisk.py snapshot --format csv"
            print(f"Volby jako {cmd!r} patri za podprikaz 'snapshot', "
                  f"napr.:  python protc_otisk.py snapshot {cmd} ...\n")
        else:
            navrh = difflib.get_close_matches(cmd, COMMANDS, n=1, cutoff=0.4)
            if navrh:
                print(f"Mozna jsi mysel: {navrh[0]!r}?\n")
        print(build_usage())
        sys.exit(1)


if __name__ == "__main__":
    main()
