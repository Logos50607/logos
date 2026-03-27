#!/bin/sh
# dotfiles install script
# 冪等：重複執行不會壞掉

DOTFILES="$(cd "$(dirname "$0")" && pwd)"

link() {
  src="$1"
  dst="$2"
  if [ -L "$dst" ]; then
    echo "skip (already symlink): $dst"
  elif [ -e "$dst" ]; then
    echo "backup: $dst -> $dst.bak"
    mv "$dst" "$dst.bak"
    ln -sf "$src" "$dst"
  else
    ln -sf "$src" "$dst"
    echo "linked: $dst -> $src"
  fi
}

link "$DOTFILES/tmux/.tmux.conf"   "$HOME/.tmux.conf"
link "$DOTFILES/git/.gitconfig"    "$HOME/.gitconfig"
link "$DOTFILES/bash/.bashrc"      "$HOME/.bashrc"
link "$DOTFILES/nvim"              "$HOME/.config/nvim"

echo ""
sh "$DOTFILES/test_install.sh"
