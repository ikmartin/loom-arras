# source me: TinyTeX first, every TeX directory removed from the ordinary PATH
S=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/tinytex
TTBIN=$S/tt/TinyTeX/bin/universal-darwin
REST=$(printf '%s' "$PATH" | tr ':' '\n' | grep -v -E '^/usr/local/texlive|^/Library/TeX|TinyTeX' | paste -sd: -)
export PATH="$TTBIN:$REST"
export XDG_CONFIG_HOME=$S/xdg
unset INFOPATH
LOOM=/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom
