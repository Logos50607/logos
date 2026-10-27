-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- 把 yank 內容推進 tmux buffer，讓其他 pane 可用 prefix+] 貼上
local function yank_to_tmux()
  local text = vim.fn.getreg('"')
  if text ~= "" and vim.fn.executable("tmux") == 1 and os.getenv("TMUX") then
    vim.fn.system("tmux load-buffer -", text)
  end
end

vim.keymap.set("n", "<leader>y", function()
  vim.cmd("normal! yy")
  yank_to_tmux()
end, { desc = "Yank line to tmux buffer" })

vim.keymap.set("v", "<leader>y", function()
  vim.cmd('normal! y')
  yank_to_tmux()
end, { desc = "Yank selection to tmux buffer" })
