#!/bin/sh
# 驗證 install.sh 的 symlink 是否正確建立

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
pass=0
fail=0

check() {
  label="$1"
  dst="$2"
  expected_src="$3"

  if [ ! -L "$dst" ]; then
    echo "FAIL  $label: $dst 不是 symlink"
    fail=$((fail + 1))
  elif [ "$(readlink "$dst")" != "$expected_src" ]; then
    echo "FAIL  $label: 指向 $(readlink "$dst")，預期 $expected_src"
    fail=$((fail + 1))
  elif [ ! -e "$dst" ]; then
    echo "FAIL  $label: symlink 存在但目標不存在"
    fail=$((fail + 1))
  else
    echo "PASS  $label"
    pass=$((pass + 1))
  fi
}

check "tmux"    "$HOME/.tmux.conf"     "$DOTFILES/tmux/.tmux.conf"
check "git"     "$HOME/.gitconfig"     "$DOTFILES/git/.gitconfig"
check "bash"    "$HOME/.bashrc"        "$DOTFILES/bash/.bashrc"
check "nvim"    "$HOME/.config/nvim"   "$DOTFILES/nvim"

echo ""
echo "結果：$pass 通過，$fail 失敗"
[ "$fail" -eq 0 ]
