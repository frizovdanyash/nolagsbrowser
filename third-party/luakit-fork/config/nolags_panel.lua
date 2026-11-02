local window = require "window"
local settings = require "settings"

local _M = {}

local css = {
    chrome    = "background-color: #f2eee7;",
    tablist   = "background-color: #f2eee7; padding: 8px 10px 0 10px;",
    tab       = "background-color: #e7e1d6; color: #5d6469; min-width: 130px; min-height: 30px; margin-right: 4px; border-radius: 9px 9px 0 0; padding: 0 6px;",
    tab_sel   = "background-color: #ffffff; color: #14231f; font-weight: bold;",
    newtab    = "background-color: #f2eee7; color: #2fb7a4; font-size: 20px; padding: 0 12px; border-radius: 9px;",
    mascot    = "padding: 0 8px 0 2px;",
    bar       = "background-color: #ffffff; padding: 5px 10px 6px 10px; border-bottom: 1px solid #e4e0d7;",
    entry     = "background-color: #f4f1ea; border-radius: 9px; padding: 5px 12px; color: #1b1f24; min-height: 26px;",
    entry_sel = "background-color: #eaf6f4;",
}

local function set_css(widget, value)
    pcall(function() widget.css = value end)
end

local function set_margin(widget, top, right, bottom, left)
    pcall(function()
        widget.margin_top = top
        widget.margin_right = right
        widget.margin_bottom = bottom
        widget.margin_left = left
    end)
end

local function make_mascot()
    local box = widget{type = "eventbox"}
    local img = widget{type = "image"}
    if not pcall(function() img:filename("nolags-mascot-48.png") end) then
        pcall(function() img:filename("nolags-mascot.png") end)
    end
    box.child = img
    set_css(box, css.mascot)
    pcall(function()
        box:add_signal("button-press", function (_, _, event)
            if event.button == 1 then
                local w = window.ancestor(box)
                if w then w:new_tab("luakit://newtab") end
            end
        end)
    end)
    return box
end

local function build_bar(w)
    local bar = widget{type = "hbox"}
    bar.homogeneous = false
    set_css(bar, css.bar)

    local mascot = make_mascot()

    local entry = widget{type = "entry"}
    set_css(entry, css.entry)
    pcall(function()
        entry:add_signal("focus-in", function () set_css(entry, css.entry .. " " .. css.entry_sel) end)
        entry:add_signal("focus-out", function () set_css(entry, css.entry) end)
    end)

    local home = widget{type = "eventbox"}
    local home_label = widget{type = "label"}
    home_label.text = "⌂"
    set_css(home_label, "font-size: 17px; color: #2fb7a4; padding: 0 10px;")
    home.child = home_label
    pcall(function()
        home:add_signal("button-press", function (_, _, event)
            if event.button == 1 then
                local win = window.ancestor(home)
                if win and win.view then win.view:load("luakit://newtab") end
            end
        end)
    end)

    bar:pack(mascot)
    bar:pack(entry, { expand = true, fill = true })
    bar:pack(home)
    w._nolags_bar = bar
    w._nolags_entry = entry
    return bar
end

local function wire(w)
    local bar = w._nolags_bar
    local entry = w._nolags_entry
    if not bar or not entry then return end

    local function sync()
        if w.view then
            entry.text = w.view.uri or ""
        end
    end

    local function go()
        local input = entry.text or ""
        input = input:gsub("^%s+", ""):gsub("%s+$", "")
        if input == "" or not w.view then return end
        w.view:load(input)
    end

    pcall(function()
        entry:add_signal("activate", function () go() end)
        entry:add_signal("key-press", function (_, _, event)
            if event.keyval == 0xff0d or event.keyval == 0xff8d then
                go()
                return true
            end
            return false
        end)
    end)

    if w.view then
        pcall(function() w.view:add_signal("property::uri", sync) end)
        sync()
    end
end

local function attach_bar(w)
    if not w or w._nolags_bar then return end
    set_css(w.tablist.widget, css.tablist)
    set_css(w.layout, css.chrome)
    local bar = build_bar(w)
    if bar then
        w.layout:pack(bar, { expand = false, fill = false })
        local ok = pcall(function() w.layout:reorder(bar, 1) end)
        if not ok then
            pcall(function() w.layout:reorder_child(bar, 1) end)
        end
    end
end

window.add_signal("build", attach_bar)

local function bind_view(w, view)
    if not view or not w._nolags_entry then return end
    local bound = w._nolags_bound or {}
    w._nolags_bound = bound
    if bound[view] then return end
    bound[view] = true
    local entry = w._nolags_entry
    local sync = function (v)
        if w._nolags_entry == entry and w.view == v then
            entry.text = v.uri or ""
        end
    end
    pcall(function() view:add_signal("property::uri", sync) end)
    pcall(function() view:add_signal("switched-page", function (v) sync(v) end) end)
    sync(view)
end

local function attach_bar(w)
    if not w or w._nolags_bar then return end
    set_css(w.tablist.widget, css.tablist)
    set_css(w.layout, css.chrome)
    local bar = build_bar(w)
    if bar then
        w.layout:pack(bar, { expand = false, fill = false })
        local ok = pcall(function() w.layout:reorder(bar, 1) end)
        if not ok then
            pcall(function() w.layout:reorder_child(bar, 1) end)
        end
    end
end

window.add_signal("build", attach_bar)

local webview = require "webview"

webview.add_signal("init", function (view)
    pcall(function()
        view:add_signal("switched-page", function (v)
            local w = webview.window(v)
            if w then bind_view(w, v) end
        end)
    end)
end)

window.add_signal("switch-page", function (w, view)
    bind_view(w, view)
end)

return _M
