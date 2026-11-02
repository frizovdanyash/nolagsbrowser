using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Web;
using System.Windows.Forms;
using Timer = System.Windows.Forms.Timer;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace NoLagsBrowser
{
    internal sealed class BrowserTab
    {
        public WebView2 View;
        public TabPage Page;
        public string Url = "";
        public string Title = "Новая вкладка";
        public bool Reading;
        public bool StyleApplied;
        public DateTime LastActive = DateTime.Now;
        public long LastBytes;
        public DateTime LastChange = DateTime.Now;
        public string LastNotifiedUrl = "";
        public double ZoomPercent = 100.0;

        public bool IsInternal => UrlTools.IsInternal(Url);
        public bool IsSleeping => Page?.Tag as string == "sleep";
    }

    internal sealed class MainForm : Form
    {
        private readonly Storage _storage;
        private SettingsData S => _storage.Settings;

        private TabControl _tabs;
        private ToolStrip _toolbar;
        private ToolStrip _bookmarksBar;
        private ToolStripStatusLabel _statusLabel;
        private ToolStripStatusLabel _memoryLabel;
        private ToolStripStatusLabel _zoomLabel;
        private StatusStrip _statusStrip;
        private ToolStripTextBox _address;
        private ToolStripButton _backButton;
        private ToolStripButton _forwardButton;
        private ToolStripButton _reloadButton;
        private ToolStripButton _starButton;
        private ToolStripButton _readerButton;
        private ToolStripButton _sleepButton;
        private Timer _memoryTimer;
        private Timer _sleepTimer;
        private readonly List<BrowserTab> _closedTabs = new List<BrowserTab>();
        private bool _suppressAddressEvent;
        private bool _internalNavigating;
        private readonly string[] _startupArgs;

        private static readonly string[] Trackers =
        {
            "doubleclick.net", "google-analytics.com", "googletagmanager.com", "googletagservices.com",
            "googleadservices.com", "adservice.google.com", "facebook.net", "scorecardresearch.com",
            "quantserve.com", "criteo.com", "criteo.net", "taboola.com", "outbrain.com", "adnxs.com",
            "adsrvr.org", "rubiconproject.com", "pubmatic.com", "openx.net", "casalemedia.com",
            "smartadserver.com", "moatads.com", "serving-sys.com", "2mdn.net", "adform.net",
            "amazon-adsystem.com", "media.net", "zedo.com", "exelator.com", "bluekai.com", "demdex.net",
            "krxd.net", "agkn.com", "rlcdn.com", "mathtag.com", "bidswitch.net", "sharethrough.com",
            "teads.tv", "spotxchange.com", "3lift.com", "33across.com", "indexww.com", "tapad.com",
            "crwdcntrl.net", "hotjar.com", "fullstory.com", "mouseflow.com", "mixpanel.com",
            "amplitude.com", "segment.io", "segment.com", "mc.yandex.ru", "an.yandex.ru", "adfox.ru",
            "adriver.ru", "top-fwz1.mail.ru", "clarity.ms", "histats.com", "statcounter.com"
        };

        public MainForm(Storage storage, string[] args)
        {
            _storage = storage;
            _startupArgs = args ?? Array.Empty<string>();
            BuildUi();
            ApplySettings();
            RestoreSession();
            _memoryTimer = new Timer { Interval = 20000 };
            _memoryTimer.Tick += (s, e) => UpdateMemory();
            _memoryTimer.Start();
            _sleepTimer = new Timer { Interval = 60000 };
            _sleepTimer.Tick += (s, e) => SleepIdleTabs();
            _sleepTimer.Start();
        }

        private void BuildUi()
        {
            Text = "NoLags Browser";
            Width = 1200;
            Height = 780;
            MinimumSize = new Size(640, 420);
            StartPosition = FormStartPosition.CenterScreen;
            try
            {
                Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            }
            catch
            {
            }
            BackColor = Color.FromArgb(245, 243, 238);

            _toolbar = new ToolStrip
            {
                GripStyle = ToolStripGripStyle.Hidden,
                RenderMode = ToolStripRenderMode.System,
                Padding = new Padding(4, 3, 4, 3),
                ImageScalingSize = new Size(18, 18)
            };

            _backButton = MakeButton("◀", "Назад (Alt+←)", (s, e) => Current?.View?.CoreWebView2?.GoBack());
            _forwardButton = MakeButton("▶", "Вперёд (Alt+→)", (s, e) => Current?.View?.CoreWebView2?.GoForward());
            _reloadButton = MakeButton("⟳", "Обновить (F5)", (s, e) => ReloadCurrent());
            var homeButton = MakeButton("⌂", "Домашняя страница (Alt+Home)", (s, e) => Navigate(HomePage));

            _address = new ToolStripTextBox
            {
                AutoSize = false,
                Width = 600,
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Segoe UI", 10.5f)
            };
            _address.KeyDown += AddressKeyDown;
            _address.Enter += (s, e) =>
            {
                if (Current != null && !string.IsNullOrEmpty(Current.Url))
                    BeginInvoke(new Action(() => _address.SelectAll()));
            };
            _address.Leave += (s, e) => UpdateAddressBar();

            _starButton = MakeButton("☆", "Добавить в закладки (Ctrl+D)", (s, e) => ToggleBookmarkCurrent());
            _readerButton = MakeButton("▤", "Режим чтения (Ctrl+Shift+F)", (s, e) => ToggleReader());
            _sleepButton = MakeButton("z", "Усыпить вкладку", (s, e) => SleepTab(Current));
            var menuButton = MakeButton("☰", "Меню", (s, e) => ShowMenu());

            _toolbar.Items.AddRange(new ToolStripItem[]
            {
                _backButton, _forwardButton, _reloadButton, homeButton,
                new ToolStripSeparator(), _address,
                new ToolStripSeparator(), _starButton, _readerButton, _sleepButton, menuButton
            });
            Controls.Add(_toolbar);

            _bookmarksBar = new ToolStrip
            {
                GripStyle = ToolStripGripStyle.Hidden,
                RenderMode = ToolStripRenderMode.System,
                Padding = new Padding(4, 1, 4, 1),
                AutoSize = true
            };
            Controls.Add(_bookmarksBar);

            _tabs = new TabControl
            {
                Dock = DockStyle.Fill,
                Padding = new Point(14, 4),
                Font = new Font("Segoe UI", 9.5f),
                DrawMode = TabDrawMode.OwnerDrawFixed,
                ItemSize = new Size(210, 26),
                SizeMode = TabSizeMode.Fixed
            };
            _tabs.DrawItem += DrawTab;
            _tabs.MouseDown += TabsMouseDown;
            _tabs.SelectedIndexChanged += TabsChanged;
            _tabs.MouseDoubleClick += (s, e) => NewTab();
            Controls.Add(_tabs);
            _tabs.BringToFront();
            _toolbar.Dock = DockStyle.Top;
            _bookmarksBar.Dock = DockStyle.Top;

            _statusStrip = new StatusStrip { SizingGrip = false };
            _statusLabel = new ToolStripStatusLabel { Spring = true, TextAlign = ContentAlignment.MiddleLeft };
            _zoomLabel = new ToolStripStatusLabel();
            _memoryLabel = new ToolStripStatusLabel();
            _statusStrip.Items.AddRange(new ToolStripItem[] { _statusLabel, _zoomLabel, _memoryLabel });
            Controls.Add(_statusStrip);

            KeyPreview = true;
            KeyDown += MainKeyDown;
        }

        private ToolStripButton MakeButton(string text, string tooltip, EventHandler onClick)
        {
            var button = new ToolStripButton(text)
            {
                DisplayStyle = ToolStripItemDisplayStyle.Text,
                ToolTipText = tooltip,
                AutoSize = false,
                Width = 30,
                Height = 26,
                Font = new Font("Segoe UI Symbol", 11f)
            };
            button.Click += onClick;
            return button;
        }

        private void DrawTab(object sender, DrawItemEventArgs e)
        {
            var page = _tabs.TabPages[e.Index];
            bool selected = e.Index == _tabs.SelectedIndex;
            using var background = new SolidBrush(selected ? Color.White : Color.FromArgb(238, 236, 231));
            e.Graphics.FillRectangle(background, e.Bounds);
            if (selected)
            {
                using var accent = new SolidBrush(Color.FromArgb(47, 183, 164));
                e.Graphics.FillRectangle(accent, new Rectangle(e.Bounds.X + 6, e.Bounds.Bottom - 3, e.Bounds.Width - 12, 3));
            }
            string title = page.Text;
            if (title.Length > 26)
                title = title.Substring(0, 25) + "…";
            bool sleeping = page.Tag as string == "sleep";
            var textRect = new Rectangle(e.Bounds.X + 8, e.Bounds.Y, e.Bounds.Width - 30, e.Bounds.Height);
            TextRenderer.DrawText(e.Graphics, sleeping ? "💤 " + title : title, Font, textRect,
                selected ? Color.FromArgb(32, 35, 42) : Color.FromArgb(108, 116, 128),
                TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
            TextRenderer.DrawText(e.Graphics, "✕", new Font("Segoe UI", 8.5f),
                new Rectangle(e.Bounds.Right - 22, e.Bounds.Y, 18, e.Bounds.Height),
                Color.FromArgb(120, 128, 138), TextFormatFlags.VerticalCenter | TextFormatFlags.HorizontalCenter);
        }

        private void TabsMouseDown(object sender, MouseEventArgs e)
        {
            for (int index = 0; index < _tabs.TabPages.Count; index++)
            {
                var rect = _tabs.GetTabRect(index);
                if (!rect.Contains(e.Location))
                    continue;
                if (e.Button == MouseButtons.Middle)
                {
                    CloseTab(_tabs.TabPages[index]);
                    return;
                }
                if (e.Button == MouseButtons.Left && e.X > rect.Right - 24)
                {
                    CloseTab(_tabs.TabPages[index]);
                    return;
                }
                if (e.Button == MouseButtons.Right)
                {
                    _tabs.SelectedIndex = index;
                    ShowTabMenu(_tabs.TabPages[index]);
                    return;
                }
            }
            if (e.Button == MouseButtons.Right && e.X > _tabs.Width - 120)
                ShowTabMenu(null);
        }

        private void TabsChanged(object sender, EventArgs e)
        {
            var tab = Current;
            if (tab == null)
                return;
            tab.LastActive = DateTime.Now;
            if (tab.IsSleeping)
                Revive(tab);
            UpdateAddressBar();
            UpdateNavButtons();
            UpdateStar();
            Text = string.IsNullOrEmpty(tab.Title) ? "NoLags Browser" : tab.Title + " — NoLags Browser";
            UpdateZoomLabel();
        }

        private BrowserTab Current
        {
            get
            {
                if (_tabs?.SelectedTab == null)
                    return null;
                return _tabs.SelectedTab.Tag as BrowserTab;
            }
        }

        private string HomePage => string.IsNullOrWhiteSpace(S.HomePage) ? "nolags://newtab" : S.HomePage;

        private string DownloadFolder => string.IsNullOrWhiteSpace(S.DownloadFolder)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads")
            : S.DownloadFolder;

        private void ApplySettings()
        {
            _bookmarksBar.Visible = S.ShowBookmarksBar;
            _statusStrip.Visible = S.ShowStatusBar;
            RebuildBookmarksBar();
        }

        public void RebuildBookmarksBar()
        {
            _bookmarksBar.Items.Clear();
            var all = new ToolStripButton("Все закладки") { DisplayStyle = ToolStripItemDisplayStyle.Text };
            all.Click += (s, e) => OpenPage("nolags://bookmarks");
            foreach (var bookmark in _storage.Bookmarks.Take(24))
            {
                var button = new ToolStripButton(Shorten(bookmark.Title ?? bookmark.Url, 26))
                {
                    DisplayStyle = ToolStripItemDisplayStyle.Text,
                    ToolTipText = bookmark.Url,
                    Tag = bookmark.Url
                };
                button.Click += (s, e) => Navigate((string)((ToolStripItem)s).Tag);
                button.MouseDown += (s, e) =>
                {
                    if (e.Button == MouseButtons.Middle)
                        NewTab((string)((ToolStripItem)s).Tag, background: true);
                };
                _bookmarksBar.Items.Add(button);
            }
            _bookmarksBar.Items.Add(new ToolStripSeparator());
            _bookmarksBar.Items.Add(all);
        }

        public void ApplyToAllTabs()
        {
            foreach (var tab in AllTabs())
                ApplyTabOptions(tab);
            ApplySettings();
        }

        private void ApplyTabOptions(BrowserTab tab)
        {
            if (tab?.View?.CoreWebView2 == null)
                return;
            var core = tab.View.CoreWebView2;
            try
            {
                core.Settings.IsScriptEnabled = true;
                core.Settings.AreDefaultScriptDialogsEnabled = true;
                core.Settings.IsWebMessageEnabled = true;
                core.Settings.AreDevToolsEnabled = true;
                core.Settings.IsStatusBarEnabled = S.ShowStatusBar;
                core.Settings.AreBrowserAcceleratorKeysEnabled = false;
                core.Settings.IsPinchZoomEnabled = false;
                core.Settings.IsZoomControlEnabled = true;
                core.Settings.IsPasswordAutosaveEnabled = false;
                core.Settings.IsGeneralAutofillEnabled = false;
            }
            catch
            {
            }
        }

        private IEnumerable<BrowserTab> AllTabs() => _tabs.TabPages.Cast<TabPage>().Select(p => p.Tag).OfType<BrowserTab>();

        private async Task<CoreWebView2Environment> CreateEnvironmentAsync()
        {
            string dataFolder = Path.Combine(_storage.Root, "WebView2");
            Directory.CreateDirectory(dataFolder);
            var options = new CoreWebView2EnvironmentOptions
            {
                AdditionalBrowserArguments = S.LowMemoryMode
                    ? "--renderer-process-limit=2 --js-flags=--lite-mode --disable-features=PixelCanvas --single-process"
                    : "--renderer-process-limit=3"
            };
            return await CoreWebView2Environment.CreateAsync(null, dataFolder, options);
        }

        private void NewTab(string url = null, bool background = false, bool select = true)
        {
            var tab = new BrowserTab();
            var page = new TabPage("Новая вкладка");
            tab.Page = page;
            page.Tag = tab;

            var view = new WebView2
            {
                Dock = DockStyle.Fill,
                DefaultBackgroundColor = Color.FromArgb(245, 243, 238)
            };
            tab.View = view;
            page.Controls.Add(view);
            _tabs.TabPages.Add(page);
            if (!background)
                _tabs.SelectedTab = page;

            _ = InitializeAsync(tab, url);
        }

        private async Task InitializeAsync(BrowserTab tab, string url)
        {
            try
            {
                var environment = await CreateEnvironmentAsync();
                await tab.View.EnsureCoreWebView2Async(environment);
                var core = tab.View.CoreWebView2;
                var settings = core.Settings;
                settings.AreDefaultContextMenusEnabled = true;
                settings.AreDevToolsEnabled = true;
                settings.IsStatusBarEnabled = S.ShowStatusBar;
                settings.AreBrowserAcceleratorKeysEnabled = false;
                settings.IsPasswordAutosaveEnabled = false;
                settings.IsGeneralAutofillEnabled = false;
                if (S.Theme == "dark" || S.Theme == "system")
                {
                    try
                    {
                        core.Profile.PreferredColorScheme = S.Theme == "dark"
                            ? CoreWebView2PreferredColorScheme.Dark
                            : CoreWebView2PreferredColorScheme.Auto;
                    }
                    catch
                    {
                    }
                }
                core.Profile.PreferredTrackingPreventionLevel = S.BlockTrackers
                    ? CoreWebView2TrackingPreventionLevel.Strict
                    : CoreWebView2TrackingPreventionLevel.None;
                try
                {
                    core.Profile.PreferredColorScheme = CoreWebView2PreferredColorScheme.Auto;
                }
                catch
                {
                }

                core.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All);
                core.WebResourceRequested += (s, e) => OnResourceRequested(tab, e);
                core.NavigationStarting += (s, e) => OnNavigationStarting(tab, e);
                core.NavigationCompleted += (s, e) => OnNavigationCompleted(tab, e);
                core.SourceChanged += (s, e) => OnSourceChanged(tab);
                core.DocumentTitleChanged += (s, e) => OnTitleChanged(tab);
                core.FaviconChanged += (s, e) => OnFaviconChanged(tab);
                core.NewWindowRequested += (s, e) =>
                {
                    e.Handled = true;
                    NewTab(e.Uri, background: false);
                };
                core.DownloadStarting += (s, e) => OnDownloadStarting(e);
                core.PermissionRequested += (s, e) =>
                {
                    if (e.PermissionKind == CoreWebView2PermissionKind.Notifications)
                        e.State = CoreWebView2PermissionState.Deny;
                };
                core.WebMessageReceived += (s, e) => OnWebMessage(tab, e);
                core.ProcessFailed += (s, e) =>
                {
                    if (e.ProcessFailedKind != CoreWebView2ProcessFailedKind.BrowserProcessExited)
                        BeginInvoke(new Action(() => ReloadCurrent()));
                };
                core.AddScriptToExecuteOnDocumentCreatedAsync(
                    "window.nl={navigate:function(v){window.chrome.webview.postMessage(JSON.stringify({action:'navigate',text:v}))}," +
                    "raw:function(v){window.chrome.webview.postMessage(JSON.stringify({action:'raw',text:v}))}," +
                    "action:function(v){window.chrome.webview.postMessage(JSON.stringify({action:'action',name:v}))}};");

                NavigateTo(tab, url ?? "nolags://newtab");
            }
            catch (Exception error)
            {
                tab.Page.Controls.Clear();
                tab.Page.Controls.Add(new Label
                {
                    Dock = DockStyle.Fill,
                    TextAlign = ContentAlignment.MiddleCenter,
                    Text = "Не удалось запустить WebView2.\n\n" +
                           "Установите Microsoft Edge WebView2 Runtime:\nhttps://go.microsoft.com/fwlink/p/?LinkId=2124703\n\n" + error.Message
                });
            }
        }

        private void OnResourceRequested(BrowserTab tab, CoreWebView2WebResourceRequestedEventArgs e)
        {
            if (!S.BlockTrackers)
                return;
            try
            {
                var host = new Uri(e.Request.Uri).Host;
                if (Trackers.Any(t => host == t || host.EndsWith("." + t, StringComparison.OrdinalIgnoreCase)))
                    e.Response = tab.View.CoreWebView2.Environment.CreateWebResourceResponse(null, 403, "Blocked", "Access-Control-Allow-Origin: *");
            }
            catch
            {
            }
        }

        private void OnNavigationStarting(BrowserTab tab, CoreWebView2NavigationStartingEventArgs e)
        {
            if (_internalNavigating || !e.Uri.StartsWith("nolags://", StringComparison.OrdinalIgnoreCase))
                return;
            e.Cancel = true;
            ShowInternal(tab, e.Uri);
        }

        private void OnNavigationCompleted(BrowserTab tab, CoreWebView2NavigationCompletedEventArgs e)
        {
            UpdateNavButtons();
            if (!e.IsSuccess && tab == Current)
            {
                string reason = e.WebErrorStatus.ToString();
                ShowInternal(tab, "nolags://error?message=" + Uri.EscapeDataString(reason) + "&url=" + Uri.EscapeDataString(tab.Url));
                return;
            }
            if (!tab.IsInternal)
                _storage.AddHistory(tab.Url, tab.Title, UrlTools.Host(tab.Url));
            UpdateStar();
        }

        private void OnSourceChanged(BrowserTab tab)
        {
            tab.Url = tab.View.Source?.AbsoluteUri ?? tab.Url;
            if (tab == Current)
                UpdateAddressBar();
        }

        private void OnTitleChanged(BrowserTab tab)
        {
            tab.Title = string.IsNullOrWhiteSpace(tab.View.CoreWebView2.DocumentTitle)
                ? UrlTools.Pretty(tab.Url)
                : tab.View.CoreWebView2.DocumentTitle;
            tab.Page.Text = Shorten(tab.Title, 32);
            if (tab == Current)
                Text = tab.Title + " — NoLags Browser";
        }

        private void OnFaviconChanged(BrowserTab tab)
        {
            if (!S.ShowFavicons)
                return;
            try
            {
                string icon = tab.View.CoreWebView2.FaviconUri;
                if (!string.IsNullOrEmpty(icon) && icon.StartsWith("http"))
                    tab.Page.ImageIndex = -1;
            }
            catch
            {
            }
        }

        private void OnDownloadStarting(CoreWebView2DownloadStartingEventArgs e)
        {
            string name = "download";
            try
            {
                name = Path.GetFileName(new Uri(e.DownloadOperation.Uri).AbsolutePath);
            }
            catch
            {
            }
            if (string.IsNullOrWhiteSpace(name))
                name = "nolags-download.bin";
            string folder = DownloadFolder;
            Directory.CreateDirectory(folder);
            string path = Path.Combine(folder, name);
            if (File.Exists(path))
                path = Path.Combine(folder, Path.GetFileNameWithoutExtension(name) + "-" + DateTime.Now.Ticks % 10000 + Path.GetExtension(name));
            e.ResultFilePath = path;
            _storage.AddDownload(new DownloadEntry
            {
                Url = e.DownloadOperation.Uri,
                FileName = Path.GetFileName(path),
                Path = path,
                State = "загружается"
            });
            var operation = e.DownloadOperation;
            operation.StateChanged += (s, args) =>
            {
                BeginInvoke(new Action(() =>
                {
                    if (operation.State.ToString() == "Completed")
                    {
                        _statusLabel.Text = "Загрузка завершена: " + Path.GetFileName(path);
                        if (S.OpenDownloads)
                            Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
                    }
                }));
            };
            _statusLabel.Text = "Загрузка: " + Path.GetFileName(path);
        }

        private void OnWebMessage(BrowserTab tab, CoreWebView2WebMessageReceivedEventArgs e)
        {
            Dictionary<string, string> message;
            try
            {
                using var document = JsonDocument.Parse(e.WebMessageAsJson);
                message = new Dictionary<string, string>();
                if (document.RootElement.ValueKind == JsonValueKind.String)
                {
                    using var inner = JsonDocument.Parse(document.RootElement.GetString());
                    foreach (var property in inner.RootElement.EnumerateObject())
                        message[property.Name] = property.Value.ToString();
                }
                else if (document.RootElement.ValueKind == JsonValueKind.Object)
                {
                    foreach (var property in document.RootElement.EnumerateObject())
                        message[property.Name] = property.Value.ToString();
                }
            }
            catch
            {
                return;
            }
            message.TryGetValue("action", out string action);
            message.TryGetValue("text", out string text);
            message.TryGetValue("name", out string name);
            switch (action)
            {
                case "navigate":
                    if (!string.IsNullOrEmpty(text))
                        Navigate(text);
                    break;
                case "raw":
                    if (!string.IsNullOrEmpty(text))
                        Navigate(UrlTools.SearchUrl(S, text));
                    break;
                case "action":
                    switch (name)
                    {
                        case "trim":
                            TrimMemory();
                            break;
                        case "history":
                            OpenPage("nolags://history");
                            break;
                        case "bookmarks":
                            OpenPage("nolags://bookmarks");
                            break;
                        case "downloads":
                            OpenPage("nolags://downloads");
                            break;
                        case "settings":
                            ShowSettings();
                            break;
                        case "sleep":
                            SleepBackgroundTabs();
                            break;
                        case "mem":
                            tab.View?.CoreWebView2?.ExecuteScriptAsync(
                                $"window.nlMem && window.nlMem({WinNative.CurrentMemoryMb()}, {_tabs.TabPages.Count})");
                            break;
                    }
                    break;
            }
        }

        public void Navigate(string text, bool forceSearch = false)
        {
            var tab = Current;
            if (tab == null)
                return;
            string url = UrlTools.Normalize(text, S, forceSearch);
            NavigateTo(tab, url);
        }

        private void NavigateTo(BrowserTab tab, string url)
        {
            if (url.StartsWith("nolags://", StringComparison.OrdinalIgnoreCase) &&
                !url.StartsWith("nolags://error", StringComparison.OrdinalIgnoreCase))
            {
                ShowInternal(tab, url);
                return;
            }
            try
            {
                tab.View.CoreWebView2?.Navigate(url);
            }
            catch
            {
                ShowInternal(tab, "nolags://error?message=" + Uri.EscapeDataString("Некорректный адрес") + "&url=" + Uri.EscapeDataString(url));
            }
        }

        private void ShowInternal(BrowserTab tab, string url)
        {
            string html = InternalHtml(url);
            tab.Url = url;
            tab.Page.Tag = tab;
            _internalNavigating = true;
            try
            {
                tab.View.CoreWebView2?.NavigateToString(html);
            }
            finally
            {
                _internalNavigating = false;
            }
            tab.Title = InternalTitle(url);
            tab.Page.Text = Shorten(tab.Title, 32);
            if (tab == Current)
            {
                Text = tab.Title + " — NoLags Browser";
                UpdateAddressBar();
                UpdateNavButtons();
            }
        }

        private static string InternalTitle(string url)
        {
            if (url.Contains("history"))
                return "История";
            if (url.Contains("bookmarks"))
                return "Закладки";
            if (url.Contains("downloads"))
                return "Загрузки";
            if (url.Contains("error"))
                return "Не удалось открыть страницу";
            return "Новая вкладка";
        }

        private string InternalHtml(string url)
        {
            string page = url.Split('?')[0].TrimEnd('/');
            if (page.EndsWith("history"))
                return InternalHistory();
            if (page.EndsWith("bookmarks"))
                return InternalBookmarks();
            if (page.EndsWith("downloads"))
                return InternalDownloads();
            if (page.EndsWith("error"))
                return InternalError(url);
            return StartPage.Build(_storage);
        }

        private string Wrap(string title, string body) => "<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\">" +
            "<style>body{margin:0;background:#f5f3ee;color:#20232a;font-family:'Segoe UI',system-ui,sans-serif}" +
            "@media (prefers-color-scheme:dark){body{background:#14171c;color:#e9edf2}.card{background:#1c2027!important;border-color:rgba(233,237,242,.12)!important}.dim{color:#9aa4b2!important}}" +
            ".wrap{max-width:1040px;margin:0 auto;padding:24px}h1{font-size:22px;margin:0 0 16px}" +
            ".card{background:#fff;border:1px solid rgba(32,35,42,.12);border-radius:14px;padding:16px}" +
            ".row{display:flex;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid rgba(32,35,42,.08)}" +
            ".row:last-child{border-bottom:none}.grow{flex:1;min-width:0}.t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
            ".dim{color:#6c7480;font-size:12.5px}.btn{border:1px solid rgba(32,35,42,.15);background:transparent;border-radius:9px;padding:6px 12px;cursor:pointer;color:inherit}" +
            ".btn:hover{border-color:#2fb7a4;color:#2fb7a4}.fav{width:28px;height:28px;border-radius:9px;background:#2fb7a4;color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600}" +
            "a{color:#2fb7a4;text-decoration:none}</style></head><body><div class=\"wrap\"><h1>{TITLE}</h1>{BODY}</div></body></html>"
            .Replace("{TITLE}", title).Replace("{BODY}", body);

        private string InternalHistory()
        {
            var builder = new System.Text.StringBuilder("<div class=\"card\">");
            var entries = _storage.SearchHistory("", 300).ToList();
            if (entries.Count == 0)
                builder.Append("<p class=\"dim\">История пуста.</p>");
            foreach (var group in entries.GroupBy(h => h.LastVisit.Date).OrderByDescending(g => g.Key))
            {
                builder.Append($"<p class=\"dim\" style=\"margin:12px 0 4px\">{group.Key:dd.MM.yyyy}</p>");
                foreach (var item in group)
                    builder.Append($"<div class=\"row\"><div class=\"fav\">{Escape(UrlTools.Host(item.Url).Take(2).ToArray())}</div>" +
                                   $"<div class=\"grow\" onclick=\"nl.navigate('{EscapeAttr(item.Url)}')\" style=\"cursor:pointer\">" +
                                   $"<div class=\"t\">{Escape(item.Title ?? item.Url)}</div><div class=\"dim\">{Escape(UrlTools.Pretty(item.Url))} · {item.Visits} визитов</div></div></div>");
            }
            builder.Append("</div>");
            return Wrap("История", builder.ToString());
        }

        private string InternalBookmarks()
        {
            var builder = new System.Text.StringBuilder("<div class=\"card\">");
            if (_storage.Bookmarks.Count == 0)
                builder.Append("<p class=\"dim\">Закладок нет.</p>");
            foreach (var item in _storage.Bookmarks)
                builder.Append($"<div class=\"row\"><div class=\"fav\">{Escape(UrlTools.Host(item.Url).Take(2).ToArray())}</div>" +
                               $"<div class=\"grow\" onclick=\"nl.navigate('{EscapeAttr(item.Url)}')\" style=\"cursor:pointer\">" +
                               $"<div class=\"t\">{Escape(item.Title ?? item.Url)}</div><div class=\"dim\">{Escape(UrlTools.Pretty(item.Url))}</div></div>" +
                               $"<button class=\"btn\" onclick=\"nl.action('bookmarks')\">Открыть</button></div>");
            builder.Append("</div>");
            return Wrap("Закладки", builder.ToString());
        }

        private string InternalDownloads()
        {
            var builder = new System.Text.StringBuilder("<div class=\"card\">");
            if (_storage.Downloads.Count == 0)
                builder.Append("<p class=\"dim\">Загрузок нет.</p>");
            foreach (var item in _storage.Downloads)
                builder.Append($"<div class=\"row\"><div class=\"fav\">↓</div><div class=\"grow\"><div class=\"t\">{Escape(item.FileName)}</div>" +
                               $"<div class=\"dim\">{item.Size / 1024} КБ · {item.State} · {item.Created:dd.MM.yyyy HH:mm}</div></div></div>");
            builder.Append("</div>");
            return Wrap("Загрузки", builder.ToString());
        }

        private string InternalError(string url)
        {
            var query = System.Web.HttpUtility.ParseQueryString(url.Contains("?") ? url.Substring(url.IndexOf('?')) : "");
            string message = query["message"] ?? "Неизвестная ошибка";
            string target = query["url"] ?? "";
            string body = "<div class=\"card\" style=\"text-align:center\">" +
                          (string.IsNullOrEmpty(StartPage.Sleep) ? "" : $"<img src=\"{StartPage.Sleep}\" style=\"width:160px;border-radius:16px\">") +
                          $"<h2 style=\"margin:14px 0 4px\">Не удалось открыть страницу</h2><p class=\"dim\">{Escape(message)}</p>" +
                          $"<p class=\"dim\" style=\"word-break:break-all\">{Escape(target)}</p>" +
                          "<button class=\"btn\" onclick=\"nl.action('reload')\">Повторить</button></div>";
            return Wrap("Ошибка загрузки", body);
        }

        private static string Escape(string text) =>
            (text ?? "").Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;");

        private static string EscapeAttr(string text) => Escape(text).Replace("'", "\\'");

        private static string Escape(char[] chars) => Escape(new string(chars)).Replace("'", "");

        private static string Shorten(string text, int limit)
        {
            if (string.IsNullOrEmpty(text))
                return "";
            return text.Length <= limit ? text : text.Substring(0, limit - 1) + "…";
        }

        private void UpdateAddressBar()
        {
            var tab = Current;
            _suppressAddressEvent = true;
            _address.Text = tab == null ? "" : (UrlTools.IsInternal(tab.Url) ? "NoLags" : tab.Url);
            _suppressAddressEvent = false;
            _starButton.Text = tab != null && _storage.IsBookmarked(tab.Url) ? "★" : "☆";
        }

        private void UpdateNavButtons()
        {
            var core = Current?.View?.CoreWebView2;
            _backButton.Enabled = core?.CanGoBack ?? false;
            _forwardButton.Enabled = core?.CanGoForward ?? false;
        }

        private void UpdateStar()
        {
            var tab = Current;
            _starButton.Text = tab != null && _storage.IsBookmarked(tab.Url) ? "★" : "☆";
        }

        private void UpdateZoomLabel() =>
            _zoomLabel.Text = Current == null || Math.Abs(Current.ZoomPercent - 100) < 1 ? "" : $"Масштаб {Current.ZoomPercent:0}%";

        private void AddressKeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode != Keys.Enter)
                return;
            e.SuppressKeyPress = true;
            string text = _address.Text.Trim();
            if (text.Length == 0)
                return;
            if (text.Equals("NoLags", StringComparison.OrdinalIgnoreCase))
                text = "nolags://newtab";
            Navigate(text, e.Shift);
            if (Current?.View != null)
                Current.View.Focus();
        }

        public void UpdateMemory()
        {
            long memory = WinNative.CurrentMemoryMb();
            int tabs = _tabs?.TabPages.Count ?? 0;
            _memoryLabel.Text = $"ОЗУ {memory} МБ · вкладок {tabs}";
        }

        public void TrimMemory()
        {
            WinNative.TrimMemory();
            UpdateMemory();
            _statusLabel.Text = "Память освобождена";
        }

        private void SleepIdleTabs()
        {
            if (!S.SleepTabs)
                return;
            foreach (var tab in AllTabs())
            {
                if (tab == Current || tab.IsSleeping || tab.IsInternal || string.IsNullOrEmpty(tab.Url))
                    continue;
                if ((DateTime.Now - tab.LastActive).TotalMinutes >= Math.Max(1, S.SleepMinutes))
                    SleepTab(tab);
            }
        }

        public void SleepBackgroundTabs()
        {
            int count = 0;
            foreach (var tab in AllTabs())
            {
                if (tab != Current && !tab.IsSleeping && SleepTab(tab))
                    count++;
            }
            _statusLabel.Text = $"Усыплено вкладок: {count}";
        }

        private bool SleepTab(BrowserTab tab)
        {
            if (tab == null || tab.IsSleeping || tab.IsInternal || string.IsNullOrEmpty(tab.Url))
                return false;
            string html = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>" +
                          "body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;" +
                          "background:#f5f3ee;color:#20232a;font-family:'Segoe UI',sans-serif;text-align:center}" +
                          "@media (prefers-color-scheme:dark){body{background:#14171c;color:#e9edf2}}" +
                          "img{width:150px;border-radius:16px;margin-bottom:16px}.dim{color:#6c7480;max-width:420px;font-size:14px}" +
                          "button{margin-top:18px;padding:10px 18px;border-radius:12px;border:none;background:#2fb7a4;color:#fff;font-size:14px;cursor:pointer}" +
                          "</style></head><body>" +
                          (string.IsNullOrEmpty(StartPage.Sleep) ? "" : $"<img src=\"{StartPage.Sleep}\">") +
                          "<h2 style=\"margin:0 0 6px\">Вкладка спит</h2>" +
                          "<div class=\"dim\">Память освобождена. Нажмите кнопку или выберите вкладку, чтобы загрузить страницу заново.</div>" +
                          "<button onclick=\"nl.action('wake')\">Проснуться</button></body></html>";
            tab.Page.Tag = "sleep";
            tab.Page.Text = "💤 " + Shorten(tab.Title, 28);
            tab.View.Visible = false;
            tab.View.CoreWebView2?.NavigateToString(html);
            tab.View.Visible = true;
            return true;
        }

        private void Revive(BrowserTab tab)
        {
            if (!tab.IsSleeping)
                return;
            tab.Page.Tag = tab;
            tab.Page.Text = Shorten(tab.Title, 32);
            if (!string.IsNullOrEmpty(tab.Url))
                tab.View.CoreWebView2?.Navigate(tab.Url);
        }

        private void ToggleBookmarkCurrent()
        {
            var tab = Current;
            if (tab == null || string.IsNullOrEmpty(tab.Url))
                return;
            _storage.ToggleBookmark(tab.Url, tab.Title);
            UpdateStar();
            RebuildBookmarksBar();
        }

        private void ToggleReader()
        {
            var tab = Current;
            if (tab?.View?.CoreWebView2 == null)
                return;
            tab.Reading = !tab.Reading;
            string css = "body{background:#faf9f4!important;color:#23262b!important}" +
                         "article,main,[role=main]{max-width:46rem!important;margin:0 auto!important;font-family:Georgia,serif!important;font-size:19px!important;line-height:1.7!important}" +
                         "aside,nav,footer,header,.advert,.ads,.sidebar{display:none!important}";
            if (tab.Reading)
                tab.View.CoreWebView2.ExecuteScriptAsync(
                    "(function(){var s=document.createElement('style');s.id='nl-reader';s.textContent=" + JsonSerializer.Serialize(css) +
                    ";document.documentElement.appendChild(s);})()");
            else
                tab.View.CoreWebView2.ExecuteScriptAsync(
                    "(function(){var s=document.getElementById('nl-reader');if(s)s.remove();})()");
            _statusLabel.Text = tab.Reading ? "Режим чтения включён" : "Режим чтения выключен";
        }

        private void SetPageStyle(string style)
        {
            var tab = Current;
            if (tab?.View?.CoreWebView2 == null)
                return;
            S.PageStyle = style;
            _storage.SaveSettings();
            string css = style switch
            {
                "dark" => "html{filter:invert(1) hue-rotate(180deg)!important;background:#111!important}img,video,picture,canvas,svg{filter:invert(1) hue-rotate(180deg)!important}",
                "sepia" => "html{filter:sepia(.32) saturate(.9)!important;background:#f4ecd8!important}",
                "gray" => "html{filter:grayscale(1)!important}",
                _ => ""
            };
            tab.View.CoreWebView2.ExecuteScriptAsync(
                "(function(){var s=document.getElementById('nl-style');if(s)s.remove();" +
                (string.IsNullOrEmpty(css) ? "" : "var n=document.createElement('style');n.id='nl-style';n.textContent=" + JsonSerializer.Serialize(css) + ";document.documentElement.appendChild(n);") +
                "})()");
            _statusLabel.Text = "Оформление страниц обновлено";
        }

        private void Zoom(int delta)
        {
            var tab = Current;
            if (tab?.View?.CoreWebView2 == null)
                return;
            tab.ZoomPercent = Math.Max(25, Math.Min(500, tab.ZoomPercent + delta));
            tab.View.ZoomFactor = tab.ZoomPercent / 100.0;
            UpdateZoomLabel();
        }

        private void ResetZoom()
        {
            var tab = Current;
            if (tab?.View == null)
                return;
            tab.ZoomPercent = 100;
            tab.View.ZoomFactor = 1.0;
            UpdateZoomLabel();
        }

        private void ReloadCurrent()
        {
            var tab = Current;
            if (tab == null)
                return;
            if (tab.IsSleeping)
            {
                Revive(tab);
                return;
            }
            if (tab.IsInternal)
                ShowInternal(tab, tab.Url);
            else
                tab.View.CoreWebView2?.Reload();
        }

        public void OpenPage(string url)
        {
            var tab = Current;
            if (tab != null && tab.IsInternal && url.StartsWith("nolags://"))
                ShowInternal(tab, url);
            else
                NewTab(url);
        }

        private void CloseTab(TabPage page)
        {
            if (page == null)
                return;
            var tab = page.Tag as BrowserTab;
            if (tab != null && !tab.IsInternal && !string.IsNullOrEmpty(tab.Url))
                _closedTabs.Insert(0, tab);
            if (_closedTabs.Count > 20)
                _closedTabs.RemoveRange(20, _closedTabs.Count - 20);
            _tabs.TabPages.Remove(page);
            page.Dispose();
            if (_tabs.TabPages.Count == 0)
                NewTab("nolags://newtab");
        }

        private void RestoreSession()
        {
            foreach (var arg in _startupArgs)
                if (arg.StartsWith("http", StringComparison.OrdinalIgnoreCase) || arg.StartsWith("nolags://"))
                    NewTab(arg);
            if (_tabs.TabPages.Count > 0)
                return;
            if (S.RestoreSession && S.SessionUrls.Count > 0)
            {
                foreach (var url in S.SessionUrls.Take(12))
                    NewTab(url);
                return;
            }
            NewTab(HomePage);
        }

        private void SaveSession()
        {
            S.SessionUrls = AllTabs().Where(t => !t.IsInternal && !string.IsNullOrEmpty(t.Url)).Select(t => t.Url).Take(20).ToList();
            _storage.SaveSettings();
        }

        private void ShowMenu()
        {
            var menu = new ContextMenuStrip { Renderer = new ToolStripSystemRenderer() };
            menu.Items.Add("Новая вкладка\tCtrl+T", null, (s, e) => NewTab());
            menu.Items.Add("Новое окно\tCtrl+N", null, (s, e) => Process.Start(new ProcessStartInfo(Application.ExecutablePath) { UseShellExecute = true }));
            menu.Items.Add("Вернуть закрытую вкладку\tCtrl+Shift+T", null, (s, e) => RestoreClosedTab());
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("История\tCtrl+H", null, (s, e) => OpenPage("nolags://history"));
            menu.Items.Add("Закладки\tCtrl+Shift+O", null, (s, e) => OpenPage("nolags://bookmarks"));
            menu.Items.Add("Загрузки\tCtrl+J", null, (s, e) => OpenPage("nolags://downloads"));
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Освободить память", null, (s, e) => TrimMemory());
            menu.Items.Add("Усыпить фоновые вкладки", null, (s, e) => SleepBackgroundTabs());
            var sleepItem = new ToolStripMenuItem("Усыплять вкладки автоматически")
            {
                CheckOnClick = true,
                Checked = S.SleepTabs
            };
            sleepItem.Click += (s, e) =>
            {
                S.SleepTabs = sleepItem.Checked;
                _storage.SaveSettings();
            };
            menu.Items.Add(sleepItem);
            menu.Items.Add("Показывать панель закладок\tCtrl+B", null, (s, e) =>
            {
                S.ShowBookmarksBar = !S.ShowBookmarksBar;
                _storage.SaveSettings();
                ApplySettings();
            });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Тёмная тема страниц", null, (s, e) => SetPageStyle(S.PageStyle == "dark" ? "none" : "dark"));
            menu.Items.Add("Режим чтения\tCtrl+Shift+F", null, (s, e) => ToggleReader());
            menu.Items.Add("Печать\tCtrl+P", null, (s, e) => Current?.View?.CoreWebView2?.ShowPrintUI());
            menu.Items.Add("Инструменты разработчика\tF12", null, (s, e) => Current?.View?.CoreWebView2?.OpenDevToolsWindow());
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Настройки", null, (s, e) => ShowSettings());
            menu.Items.Add("О браузере", null, (s, e) => ShowAbout());
            menu.Items.Add("Выход", null, (s, e) => Close());
            menu.Show(Cursor.Position);
        }

        private void ShowTabMenu(TabPage page)
        {
            var tab = page?.Tag as BrowserTab;
            var menu = new ContextMenuStrip();
            if (tab != null)
            {
                menu.Items.Add("Обновить", null, (s, e) => ReloadCurrent());
                menu.Items.Add("Скопировать адрес", null, (s, e) => Clipboard.SetText(tab.Url ?? ""));
                menu.Items.Add("Усыпить вкладку", null, (s, e) => SleepTab(tab));
                menu.Items.Add(new ToolStripSeparator());
                menu.Items.Add("Закрыть вкладку", null, (s, e) => CloseTab(page));
                menu.Items.Add("Закрыть другие вкладки", null, (s, e) =>
                {
                    foreach (var other in _tabs.TabPages.Cast<TabPage>().Where(p => p != page).ToList())
                        CloseTab(other);
                });
            }
            menu.Items.Add("Новая вкладка", null, (s, e) => NewTab());
            if (_closedTabs.Count > 0)
                menu.Items.Add("Вернуть закрытую вкладку", null, (s, e) => RestoreClosedTab());
            menu.Show(Cursor.Position);
        }

        private void RestoreClosedTab()
        {
            if (_closedTabs.Count == 0)
                return;
            var tab = _closedTabs[0];
            _closedTabs.RemoveAt(0);
            NewTab(tab.Url);
        }

        private void ShowSettings()
        {
            using var dialog = new SettingsForm(_storage);
            dialog.ShowDialog(this);
            ApplyToAllTabs();
        }

        private void ShowAbout()
        {
            using var dialog = new Form
            {
                Text = "О браузере",
                Width = 560,
                Height = 460,
                StartPosition = FormStartPosition.CenterParent,
                FormBorderStyle = FormBorderStyle.FixedDialog,
                MaximizeBox = false,
                MinimizeBox = false,
                BackColor = Color.White
            };
            var picture = new PictureBox
            {
                Image = LoadImage("mascot.png"),
                SizeMode = PictureBoxSizeMode.Zoom,
                Bounds = new Rectangle(20, 20, 200, 260)
            };
            dialog.Controls.Add(picture);
            dialog.Controls.Add(new Label
            {
                Text = "NoLags Browser 1.0.0\nДвижок: WebView2 (Chromium)\n\n" +
                       "Лёгкий браузер с ручным управлением памятью,\nсном вкладок и блокировкой трекеров.\n\n" +
                       "github.com/frizovdanyash/nolagsbrowser\nMIT License, Danechka",
                Bounds = new Rectangle(240, 30, 290, 240),
                Font = new Font("Segoe UI", 10)
            });
            var close = new Button { Text = "Закрыть", Bounds = new Rectangle(410, 370, 110, 34), DialogResult = DialogResult.OK };
            dialog.Controls.Add(close);
            dialog.AcceptButton = close;
            dialog.ShowDialog(this);
        }

        private static Image LoadImage(string name)
        {
            try
            {
                using var stream = System.Reflection.Assembly.GetExecutingAssembly().GetManifestResourceStream("NoLagsBrowser.Resources." + name);
                return stream == null ? null : Image.FromStream(stream);
            }
            catch
            {
                return null;
            }
        }

        private void MainKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Control && e.KeyCode == Keys.T)
            {
                NewTab();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.Shift && e.KeyCode == Keys.T)
            {
                RestoreClosedTab();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.W)
            {
                CloseTab(_tabs.SelectedTab);
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.L)
            {
                _address.Focus();
                _address.SelectAll();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.N)
            {
                Process.Start(new ProcessStartInfo(Application.ExecutablePath) { UseShellExecute = true });
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.D)
            {
                ToggleBookmarkCurrent();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.H)
            {
                OpenPage("nolags://history");
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.J)
            {
                OpenPage("nolags://downloads");
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.Shift && e.KeyCode == Keys.O)
            {
                OpenPage("nolags://bookmarks");
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.B)
            {
                S.ShowBookmarksBar = !S.ShowBookmarksBar;
                _storage.SaveSettings();
                ApplySettings();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.R || e.KeyCode == Keys.F5)
            {
                ReloadCurrent();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.P)
            {
                Current?.View?.CoreWebView2?.ShowPrintUI();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.S)
            {
                SavePage();
                e.SuppressKeyPress = true;
            }
            else if (e.KeyCode == Keys.F12)
            {
                Current?.View?.CoreWebView2?.OpenDevToolsWindow();
                e.SuppressKeyPress = true;
            }
            else if (e.KeyCode == Keys.F11)
            {
                FormBorderStyle = FormBorderStyle == FormBorderStyle.None ? FormBorderStyle.Sizable : FormBorderStyle.None;
                WindowState = FormWindowState.Normal;
                WindowState = FormWindowState.Maximized;
            }
            else if (e.Control && (e.KeyCode == Keys.Oemplus || e.KeyCode == Keys.Add))
            {
                Zoom(10);
                e.SuppressKeyPress = true;
            }
            else if (e.Control && (e.KeyCode == Keys.OemMinus || e.KeyCode == Keys.Subtract))
            {
                Zoom(-10);
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.D0)
            {
                ResetZoom();
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.KeyCode == Keys.Tab)
            {
                int index = _tabs.SelectedIndex + 1;
                if (index >= _tabs.TabPages.Count)
                    index = 0;
                _tabs.SelectedIndex = index;
                e.SuppressKeyPress = true;
            }
            else if (e.Control && e.Shift && e.KeyCode == Keys.Delete)
            {
                if (MessageBox.Show("Очистить историю и закладки?", "NoLags Browser",
                        MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                {
                    _storage.History.Clear();
                    _storage.SaveHistory();
                    RebuildBookmarksBar();
                    _statusLabel.Text = "История очищена";
                }
                e.SuppressKeyPress = true;
            }
            else if (e.Alt && e.KeyCode == Keys.Left)
            {
                Current?.View?.CoreWebView2?.GoBack();
                e.SuppressKeyPress = true;
            }
            else if (e.Alt && e.KeyCode == Keys.Right)
            {
                Current?.View?.CoreWebView2?.GoForward();
                e.SuppressKeyPress = true;
            }
            else if (e.Alt && e.KeyCode == Keys.Home)
            {
                Navigate(HomePage);
                e.SuppressKeyPress = true;
            }
        }

        private void SavePage()
        {
            var tab = Current;
            if (tab?.View?.CoreWebView2 == null)
                return;
            using var dialog = new SaveFileDialog
            {
                Filter = "Веб-страница (*.html)|*.html|Все файлы (*.*)|*.*",
                FileName = Shorten(tab.Title ?? "page", 60) + ".html",
                InitialDirectory = DownloadFolder
            };
            if (dialog.ShowDialog(this) != DialogResult.OK)
                return;
            string script = "document.documentElement.outerHTML";
            tab.View.CoreWebView2.ExecuteScriptAsync(script).ContinueWith(task =>
            {
                try
                {
                    string html = JsonSerializer.Deserialize<string>(task.Result) ?? "";
                    File.WriteAllText(dialog.FileName, html);
                    BeginInvoke(new Action(() => _statusLabel.Text = "Страница сохранена"));
                }
                catch
                {
                }
            });
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (S.AskOnMultiTabClose && _tabs != null && _tabs.TabPages.Count > 1 && e.CloseReason == CloseReason.UserClosing)
            {
                var answer = MessageBox.Show($"Закрыть браузер? Открыто вкладок: {_tabs.TabPages.Count}",
                    "NoLags Browser", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (answer != DialogResult.Yes)
                {
                    e.Cancel = true;
                    return;
                }
            }
            SaveSession();
            base.OnFormClosing(e);
        }
    }
}
