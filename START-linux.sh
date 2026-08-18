#!/usr/bin/env bash
# Spousteci skript pro PROTC_OTISK (Linux - a taky Mac, kdo preferuje
# terminal misto dvojkliku na START-mac.command). Aktivuje .venv (poprve ho
# rovnou vytvori a nainstaluje zavislosti) a preda vsechny argumenty do
# protc_otisk.py. Dik tomu se nemusi pred kazdym behem rucne psat
# "source .venv/bin/activate".
#
# Pouziti stejne jako "python protc_otisk.py", jen kratsi:
#   ./START-linux.sh login
#   ./START-linux.sh snapshot
#   ./START-linux.sh snapshot --limit 3 --headed
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Prvni spusteni - vytvarim virtualni prostredi (.venv)..."
    python3 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -q -r requirements.txt
    playwright install chromium
else
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python protc_otisk.py "$@"
