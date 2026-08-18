#!/usr/bin/env bash
# Pro dvojklik ve Finderu na Mac (.command Finder umi spustit, na
# rozdil od .sh, ktere by se jen otevrelo v textovem editoru). Otevre
# Terminal, aktivuje (poprve i vytvori) .venv a necha terminal otevreny,
# aby se dal napsat prikaz rucne - napr. "python protc_otisk.py snapshot".
cd "$(dirname "$0")"

# Zvetsi okno Terminalu, at je po dvojkliku vic textu naraz videt (velikost
# pisma se necha na uzivatelskem defaultu) - funguje jen v Terminal.app (ne
# treba v iTerm), proto obalene v || true, aby to pripadny neuspech
# nezastavil zbytek skriptu.
osascript -e '
tell application "Terminal"
    set bounds of front window to {80, 80, 1180, 800}
end tell
' >/dev/null 2>&1 || true

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

echo
python protc_otisk.py
echo

# Necha terminal otevreny, ale s malou vylepsenkou: "clear" v tomhle okne
# nejen smaze obrazovku (jako normalne), ale rovnou zase ukaze banner +
# napovedu - hodi se, kdyz si obrazovku vycistis a chces si pripomenout,
# jak se nastroj ovlada. Plati jen v tomhle jednom terminalovem okne, ne
# globalne - normalni "clear" v jinych oknech/terminalech neni dotcene.
# Funguje jen pro zsh/bash (na macOS default zsh); pro cokoliv jineho se
# skript chova jako drivy - proste normalni "$SHELL".
RC_FILE=$(mktemp -t protc_otisk_rc)
cat > "$RC_FILE" <<EOF
clear() { command clear; python "$(pwd)/protc_otisk.py"; }
EOF

case "$SHELL" in
    */zsh)
        ZDOTDIR_TMP=$(mktemp -d -t protc_otisk_zdotdir)
        {
            echo '[ -f "$HOME/.zprofile" ] && source "$HOME/.zprofile"'
            echo '[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc"'
            cat "$RC_FILE"
        } > "$ZDOTDIR_TMP/.zshrc"
        ZDOTDIR="$ZDOTDIR_TMP" exec zsh -i
        ;;
    */bash)
        BASH_RC_FULL=$(mktemp -t protc_otisk_bashrc)
        {
            echo '[ -f "$HOME/.bash_profile" ] && source "$HOME/.bash_profile"'
            echo '[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"'
            cat "$RC_FILE"
        } > "$BASH_RC_FULL"
        exec bash --rcfile "$BASH_RC_FULL" -i
        ;;
    *)
        exec "$SHELL"
        ;;
esac
