using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace NoLagsBrowser
{
    internal sealed class SettingsForm : Form
    {
        private readonly Storage _storage;
        private readonly TabControl _tabs = new TabControl { Dock = DockStyle.Fill, Padding = new Point(14, 5) };

        public SettingsForm(Storage storage)
        {
            _storage = storage;
            Text = "Настройки — NoLags Browser";
            Width = 620;
            Height = 560;
            StartPosition = FormStartPosition.CenterParent;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            Font = new Font("Segoe UI", 9.5f);

            _tabs.TabPages.Add(BuildMain());
            _tabs.TabPages.Add(BuildMemory());
            _tabs.TabPages.Add(BuildPrivacy());
            _tabs.TabPages.Add(BuildAbout());

            var bottom = new Panel { Dock = DockStyle.Bottom, Height = 52 };
            var save = new Button
            {
                Text = "Сохранить",
                DialogResult = DialogResult.OK,
                Width = 120,
                Height = 32,
                Left = Width - 270,
                Top = 10,
                BackColor = Color.FromArgb(47, 183, 164),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            save.FlatAppearance.BorderSize = 0;
            save.Click += (s, e) => Save();
            var cancel = new Button
            {
                Text = "Отмена",
                DialogResult = DialogResult.Cancel,
                Width = 110,
                Height = 32,
                Left = Width - 140,
                Top = 10
            };
            bottom.Controls.Add(save);
            bottom.Controls.Add(cancel);
            Controls.Add(_tabs);
            Controls.Add(bottom);
            AcceptButton = save;
            CancelButton = cancel;
        }

        private TabPage BuildMain()
        {
            var page = NewPage("Основные");
            var engine = NewCombo(UrlTools.Engines.Select(e => e.Value.Name).ToArray());
            engine.Tag = "engine";
            engine.SelectedIndex = Math.Max(0, UrlTools.Engines.Keys.ToList().IndexOf(_storage.Settings.SearchEngine));
            AddRow(page, "Поисковая система", engine);

            var home = new TextBox { Text = _storage.Settings.HomePage, Width = 320, Tag = "home" };
            AddRow(page, "Домашняя страница", home);

            var downloads = new TextBox { Text = _storage.Settings.DownloadFolder, Width = 320, Tag = "downloads" };
            AddRow(page, "Папка загрузок (пусто — стандартная)", downloads);

            AddCheck(page, "Восстанавливать сеанс", _storage.Settings.RestoreSession, "restore");
            AddCheck(page, "Спрашивать при закрытии нескольких вкладок", _storage.Settings.AskOnMultiTabClose, "askclose");
            AddCheck(page, "Показывать панель закладок", _storage.Settings.ShowBookmarksBar, "bmbar");
            AddCheck(page, "Показывать строку состояния", _storage.Settings.ShowStatusBar, "status");
            AddCheck(page, "Спрашивать папку для каждой загрузки", _storage.Settings.AskDownloadFolder, "askdl");
            AddCheck(page, "Открывать файлы после загрузки", _storage.Settings.OpenDownloads, "opendl");
            AddCheck(page, "Очищать данные при выходе", _storage.Settings.ClearOnExit, "clearexit");
            return page;
        }

        private TabPage BuildMemory()
        {
            var page = NewPage("Производительность");
            AddCheck(page, "Усыплять неактивные вкладки", _storage.Settings.SleepTabs, "sleep");
            AddCheck(page, "Режим низкого потребления памяти", _storage.Settings.LowMemoryMode, "lowmem");

            var sleep = new NumericUpDown
            {
                Minimum = 1,
                Maximum = 240,
                Value = Math.Max(1, Math.Min(240, _storage.Settings.SleepMinutes)),
                Width = 80,
                Tag = "sleepmin"
            };
            AddRow(page, "Усыплять вкладку через, минут", sleep);

            var info = new Label
            {
                Text = "Сон вкладки выгружает её содержимое и освобождает память.\n" +
                       "Кнопка «Освободить память» очищает рабочий набор процессов и кэш.",
                AutoSize = false,
                Width = 520,
                Height = 60,
                ForeColor = Color.FromArgb(108, 116, 128)
            };
            page.Controls.Add(info);
            return page;
        }

        private TabPage BuildPrivacy()
        {
            var page = NewPage("Приватность");
            AddCheck(page, "Блокировать сторонние трекеры", _storage.Settings.BlockTrackers, "block");
            AddCheck(page, "Строгая защита от отслеживания (ITP)", true, "itp");
            AddCheck(page, "Не сохранять пароли и адреса", true, "nopass");

            var style = NewCombo(new[] { "Как на сайте", "Тёмная тема страниц", "Сепия", "Чёрно-белая" });
            style.Tag = "style";
            style.SelectedIndex = _storage.Settings.PageStyle switch
            {
                "dark" => 1,
                "sepia" => 2,
                "gray" => 3,
                _ => 0
            };
            AddRow(page, "Оформление страниц", style);

            var theme = NewCombo(new[] { "Системная тема", "Светлая", "Тёмная" });
            theme.Tag = "theme";
            theme.SelectedIndex = _storage.Settings.Theme switch
            {
                "light" => 1,
                "dark" => 2,
                _ => 0
            };
            AddRow(page, "Тема интерфейса", theme);
            return page;
        }

        private TabPage BuildAbout()
        {
            var page = NewPage("О браузере");
            var label = new Label
            {
                Text = "NoLags Browser 1.0.0\nДвижок WebView2 (Chromium)\n\n" +
                       "Управление памятью, сон вкладок, блокировка трекеров,\n" +
                       "режим чтения и лёгкий интерфейс.\n\n" +
                       "github.com/frizovdanyash/nolagsbrowser",
                AutoSize = false,
                Width = 520,
                Height = 160,
                Location = new Point(16, 16)
            };
            page.Controls.Add(label);
            return page;
        }

        private static TabPage NewPage(string title)
        {
            return new TabPage(title)
            {
                AutoScroll = true,
                BackColor = Color.White,
                Padding = new Padding(14)
            };
        }

        private static ComboBox NewCombo(string[] items)
        {
            var combo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Width = 240
            };
            combo.Items.AddRange(items);
            return combo;
        }

        private static void AddRow(TabPage page, string label, Control control)
        {
            var container = new Panel
            {
                Dock = DockStyle.Top,
                Height = 46,
                Padding = new Padding(4, 8, 4, 4)
            };
            var text = new Label
            {
                Text = label,
                AutoSize = false,
                Dock = DockStyle.Left,
                Width = 260,
                TextAlign = ContentAlignment.MiddleLeft
            };
            control.Dock = DockStyle.Left;
            container.Controls.Add(control);
            container.Controls.Add(text);
            page.Controls.Add(container);
            container.BringToFront();
        }

        private static void AddCheck(TabPage page, string label, bool value, string tag)
        {
            var check = new CheckBox
            {
                Text = label,
                Checked = value,
                Tag = tag,
                AutoSize = false,
                Dock = DockStyle.Top,
                Height = 30,
                Padding = new Padding(4, 4, 0, 0)
            };
            page.Controls.Add(check);
            check.BringToFront();
        }

        private T Find<T>(string tag) where T : Control =>
            Controls.OfType<TabControl>().SelectMany(t => t.TabPages.Cast<TabPage>())
                .SelectMany(p => p.Controls.Cast<Control>())
                .SelectMany(Flatten)
                .OfType<T>()
                .FirstOrDefault(c => c.Tag as string == tag);

        private static System.Collections.Generic.IEnumerable<Control> Flatten(Control control)
        {
            yield return control;
            foreach (Control child in control.Controls)
                foreach (var nested in Flatten(child))
                    yield return nested;
        }

        private void Save()
        {
            var settings = _storage.Settings;
            var engine = Find<ComboBox>("engine");
            if (engine != null && engine.SelectedIndex >= 0)
                settings.SearchEngine = UrlTools.Engines.Keys.ToList()[engine.SelectedIndex];
            var home = Find<TextBox>("home");
            if (home != null && !string.IsNullOrWhiteSpace(home.Text))
                settings.HomePage = home.Text.Trim();
            var downloads = Find<TextBox>("downloads");
            if (downloads != null)
                settings.DownloadFolder = downloads.Text.Trim();
            settings.RestoreSession = ReadCheck("restore", settings.RestoreSession);
            settings.AskOnMultiTabClose = ReadCheck("askclose", settings.AskOnMultiTabClose);
            settings.ShowBookmarksBar = ReadCheck("bmbar", settings.ShowBookmarksBar);
            settings.ShowStatusBar = ReadCheck("status", settings.ShowStatusBar);
            settings.AskDownloadFolder = ReadCheck("askdl", settings.AskDownloadFolder);
            settings.OpenDownloads = ReadCheck("opendl", settings.OpenDownloads);
            settings.ClearOnExit = ReadCheck("clearexit", settings.ClearOnExit);
            settings.SleepTabs = ReadCheck("sleep", settings.SleepTabs);
            settings.LowMemoryMode = ReadCheck("lowmem", settings.LowMemoryMode);
            settings.BlockTrackers = ReadCheck("block", settings.BlockTrackers);
            var sleep = Find<NumericUpDown>("sleepmin");
            if (sleep != null)
                settings.SleepMinutes = (int)sleep.Value;
            var style = Find<ComboBox>("style");
            if (style != null)
                settings.PageStyle = style.SelectedIndex switch
                {
                    1 => "dark",
                    2 => "sepia",
                    3 => "gray",
                    _ => "none"
                };
            var theme = Find<ComboBox>("theme");
            if (theme != null)
                settings.Theme = theme.SelectedIndex switch
                {
                    1 => "light",
                    2 => "dark",
                    _ => "system"
                };
            _storage.SaveSettings();
        }

        private bool ReadCheck(string tag, bool fallback)
        {
            var check = Find<CheckBox>(tag);
            return check?.Checked ?? fallback;
        }
    }
}
