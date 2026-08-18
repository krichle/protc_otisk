"""
KROK 1 - Prihlaseni.

Otevre normalni (viditelny) prohlizec na prihlasovaci strance PROTC_OTISK.
Ty se prihlasis RUCNE svym jmenem a heslem - skript zadne heslo nezna,
neuklada a nikam neposila.

Az budes prihlaseny, vratis se do terminalu a zmacknes Enter.
Skript ulozi session (cookies) do souboru 'session.json'.
Vsechny dalsi behy snapshot.py uz probehnou automaticky bez prihlasovani.

Session casem vyprsi - pak proste spustis login.py znovu.

Spusteni:  python login.py
"""

import datetime as dt
import logging
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from extractor import check_session, CHECK_URL

LOGIN_URL = "https://www.projektuj-tepelna-cerpadla.cz/cz/prihlaseni"
HERE = Path(__file__).parent
SESSION_FILE = HERE / "session.json"
LOG_DIR = HERE / "logs"


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"login_{run_id}.log"

    logger = logging.getLogger("login")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    return logger, log_path


def main():
    # Banner se tady nevypisuje - ukazuje se jen jednou pri "nahozeni" (bare
    # "python protc_otisk.py" / START-mac.command), ne pri kazdem jednotlivem
    # prikazu, viz protc_otisk.py.
    logger, log_path = setup_logging()
    logger.info(f"Start login.py, log: {log_path}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context(locale="cs-CZ")
            page = ctx.new_page()
            page.goto(LOGIN_URL, wait_until="domcontentloaded")

            print("=" * 70)
            print("  Otevrel jsem prohlizec na prihlasovaci strance PROTC_OTISK.")
            print()
            print("  1) Prihlas se v tom okne RUCNE (jmeno + heslo).")
            print("  2) Odklikni pripadnou cookie listu.")
            print("  3) Pak se vrat sem a zmackni ENTER.")
            print("=" * 70)
            input("\n>>> Az budes prihlaseny, zmackni ENTER... ")

            # Overeni, ze prihlaseni opravdu funguje:
            # na zamceném dokumentu ma byt misto 'javascript:;' skutecna URL
            check = check_session(page, CHECK_URL)
            locked, downloads = check["locked"], check["downloads"]

            ctx.storage_state(path=str(SESSION_FILE))
            browser.close()
    except Exception:
        # cely traceback jde do log souboru, aby slo pozdeji dohledat presne
        # v cem prihlaseni spadlo (spatna URL, zmena stranky, timeout, ...)
        logger.exception("login.py spadl s neocekavanou chybou")
        print(f"\nCHYBA - podrobnosti (traceback) jsou v logu: {log_path}")
        sys.exit(1)

    logger.info(f"Session ulozena do: {SESSION_FILE}")
    logger.info(f"Kontrola na strance GEO 700 -> odkazu ke stazeni: {downloads}, zamcenych: {locked}")

    print()
    print(f"Session ulozena do: {SESSION_FILE}")
    print(f"Kontrola na strance GEO 700 -> odkazu ke stazeni: {downloads}, zamcenych: {locked}")
    if not check["ok"]:
        logger.warning("Porad to vypada na neprihlaseny stav.")
        print()
        print("  !! POZOR: porad to vypada na nepřihlaseny stav.")
        print("     Zkus login.py znovu a over, ze ses fakt prihlasil.")
        sys.exit(1)
    print()
    print("Hotovo. Ted spust:  python snapshot.py")
    print(f"(prubeh viz log: {log_path})")


if __name__ == "__main__":
    main()
