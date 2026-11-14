# source me: TinyTeX and the system directories only, as on a Mac with no Homebrew and no MacTeX
S=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/tinytex
TTBIN=$S/tt/TinyTeX/bin/universal-darwin
export PATH="$TTBIN:/usr/bin:/bin:/usr/sbin:/sbin"
export XDG_CONFIG_HOME=$S/xdg
unset INFOPATH
LOOM=/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom
unset LIBGS
