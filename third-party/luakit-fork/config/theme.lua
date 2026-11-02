-------------------------
-- NoLags Browser theme --
-------------------------

local theme = {}

theme.font = "11px \"Inter\", \"DejaVu Sans\", sans-serif"
theme.bold_font = "bold 11px \"Inter\", \"DejaVu Sans\", sans-serif"
theme.title_font = "bold 12px \"Inter\", \"DejaVu Sans\", sans-serif"
theme.mono_font = "11px \"JetBrains Mono\", \"DejaVu Sans Mono\", monospace"

theme.fg = "#1b1f24"
theme.bg = "#f7f5f0"

theme.accent = "#2fb7a4"
theme.accent_dark = "#1f8f80"
theme.accent_soft = "#e3f4f1"
theme.ink = "#1b1f24"
theme.paper = "#f7f5f0"
theme.surface = "#ffffff"
theme.line = "#e4e0d7"
theme.muted = "#7c8288"

theme.success_fg = "#1f8f5a"
theme.loaded_fg = theme.accent
theme.error_fg = "#ffffff"
theme.error_bg = "#e2564b"

theme.warning_fg = "#8a5a00"
theme.warning_bg = "#fff4d6"

theme.notif_fg = theme.ink
theme.notif_bg = theme.surface

theme.menu_fg = theme.ink
theme.menu_bg = theme.surface
theme.menu_selected_fg = "#0f2f2b"
theme.menu_selected_bg = theme.accent_soft
theme.menu_title_bg = theme.surface
theme.menu_primary_title_fg = theme.accent_dark
theme.menu_secondary_title_fg = theme.muted
theme.menu_disabled_fg = "#b3b8bd"
theme.menu_disabled_bg = theme.surface
theme.menu_enabled_fg = theme.ink
theme.menu_enabled_bg = theme.surface
theme.menu_active_fg = theme.accent_dark
theme.menu_active_bg = theme.surface

theme.proxy_active_menu_fg = theme.ink
theme.proxy_active_menu_bg = theme.accent_soft
theme.proxy_inactive_menu_fg = theme.muted
theme.proxy_inactive_menu_bg = theme.surface

theme.sbar_fg = "#35404a"
theme.sbar_bg = "#ffffff"
theme.sbar_border = theme.line

theme.dbar_fg = theme.ink
theme.dbar_bg = theme.surface
theme.dbar_error_fg = "#e2564b"

theme.ibar_fg = theme.ink
theme.ibar_bg = "rgba(0,0,0,0)"

theme.tab_fg = "#6b7378"
theme.tab_bg = "#efebe3"
theme.tab_hover_bg = "#f5f1ea"
theme.tab_ntheme = "#9aa0a6"
theme.selected_fg = "#132420"
theme.selected_bg = "#ffffff"
theme.selected_ntheme = theme.accent
theme.loading_fg = theme.accent_dark
theme.loading_bg = "#ffffff"

theme.selected_private_tab_bg = "#ede6f7"
theme.private_tab_bg = "#f3eefb"

theme.trust_fg = "#1f8f5a"
theme.notrust_fg = "#e2564b"

theme.hint_font = "bold 11px \"JetBrains Mono\", monospace"
theme.hint_fg = "#ffffff"
theme.hint_bg = theme.accent_dark
theme.hint_border = "1px solid #ffffff"
theme.hint_opacity = "0.22"
theme.hint_overlay_bg = "rgba(47,183,164,0.22)"
theme.hint_overlay_border = "1px dotted " .. theme.accent_dark
theme.hint_overlay_selected_bg = "rgba(47,183,164,0.45)"
theme.hint_overlay_selected_border = theme.hint_overlay_border

theme.ok = { fg = "#0f2f2b", bg = theme.accent_soft }
theme.warn = { fg = "#8a5a00", bg = "#fff4d6" }
theme.error = { fg = "#ffffff", bg = "#e2564b" }

theme.gopher_light = { bg = "#f7f5f0", fg = "#1b1f24", link = "#1f8f80" }
theme.gopher_dark = { bg = "#171b20", fg = "#e8e6e1", link = theme.accent }

return theme
