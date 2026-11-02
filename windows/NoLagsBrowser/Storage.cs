using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NoLagsBrowser
{
    public class SettingsData
    {
        public string HomePage { get; set; } = "nolags://newtab";
        public string SearchEngine { get; set; } = "duckduckgo";
        public string CustomSearch { get; set; } = "";
        public bool RestoreSession { get; set; } = true;
        public bool AskOnMultiTabClose { get; set; } = true;
        public bool ShowBookmarksBar { get; set; } = true;
        public bool ShowStatusBar { get; set; } = true;
        public bool SleepTabs { get; set; } = true;
        public int SleepMinutes { get; set; } = 10;
        public bool BlockTrackers { get; set; } = true;
        public bool LowMemoryMode { get; set; } = true;
        public string PageStyle { get; set; } = "none";
        public bool ReaderModeRewrite { get; set; } = false;
        public string DownloadFolder { get; set; } = "";
        public bool AskDownloadFolder { get; set; } = false;
        public bool OpenDownloads { get; set; } = false;
        public bool ClearOnExit { get; set; } = false;
        public bool ShowFavicons { get; set; } = true;
        public string Theme { get; set; } = "system";
        public int ZoomPercent { get; set; } = 100;
        public List<string> SessionUrls { get; set; } = new List<string>();
    }

    public class HistoryEntry
    {
        public string Url { get; set; }
        public string Title { get; set; }
        public string Host { get; set; }
        public int Visits { get; set; } = 1;
        public DateTime LastVisit { get; set; } = DateTime.Now;
    }

    public class Bookmark
    {
        public string Url { get; set; }
        public string Title { get; set; }
        public string Folder { get; set; } = "";
        public DateTime Created { get; set; } = DateTime.Now;
    }

    public class DownloadEntry
    {
        public string Url { get; set; }
        public string FileName { get; set; }
        public string Path { get; set; }
        public long Size { get; set; }
        public string State { get; set; }
        public DateTime Created { get; set; } = DateTime.Now;
    }

    public class Storage
    {
        private static readonly JsonSerializerOptions Options = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            DefaultIgnoreCondition = JsonIgnoreCondition.Never
        };

        public string Root { get; }
        public SettingsData Settings { get; private set; }
        public List<HistoryEntry> History { get; private set; } = new List<HistoryEntry>();
        public List<Bookmark> Bookmarks { get; private set; } = new List<Bookmark>();
        public List<DownloadEntry> Downloads { get; private set; } = new List<DownloadEntry>();

        public Storage()
        {
            Root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "NoLagsBrowser");
            Directory.CreateDirectory(Root);
            Load();
        }

        private string FilePath(string name) => Path.Combine(Root, name);

        public void Load()
        {
            Settings = Read<SettingsData>("settings.json") ?? new SettingsData();
            History = Read<List<HistoryEntry>>("history.json") ?? new List<HistoryEntry>();
            Bookmarks = Read<List<Bookmark>>("bookmarks.json") ?? new List<Bookmark>();
            Downloads = Read<List<DownloadEntry>>("downloads.json") ?? new List<DownloadEntry>();
        }

        private T Read<T>(string name) where T : class
        {
            try
            {
                string path = FilePath(name);
                if (!File.Exists(path))
                    return null;
                string json = File.ReadAllText(path);
                return JsonSerializer.Deserialize<T>(json, Options);
            }
            catch
            {
                return null;
            }
        }

        private void Write<T>(string name, T value)
        {
            try
            {
                File.WriteAllText(FilePath(name), JsonSerializer.Serialize(value, Options));
            }
            catch
            {
            }
        }

        public void SaveSettings() => Write("settings.json", Settings);
        public void SaveHistory() => Write("history.json", History.Take(5000).ToList());
        public void SaveBookmarks() => Write("bookmarks.json", Bookmarks);
        public void SaveDownloads() => Write("downloads.json", Downloads.Take(500).ToList());

        public void AddHistory(string url, string title, string host)
        {
            if (string.IsNullOrWhiteSpace(url) || url.StartsWith("nolags://") || url.StartsWith("about:") || url.StartsWith("data:"))
                return;
            var existing = History.FirstOrDefault(h => h.Url == url);
            if (existing == null)
            {
                History.Insert(0, new HistoryEntry
                {
                    Url = url,
                    Title = title ?? "",
                    Host = host ?? "",
                    Visits = 1,
                    LastVisit = DateTime.Now
                });
            }
            else
            {
                existing.Visits++;
                existing.LastVisit = DateTime.Now;
                if (!string.IsNullOrWhiteSpace(title))
                    existing.Title = title;
                History.Remove(existing);
                History.Insert(0, existing);
            }
            if (History.Count > 5000)
                History = History.Take(5000).ToList();
            SaveHistory();
        }

        public IEnumerable<HistoryEntry> SearchHistory(string text, int limit = 200)
        {
            if (string.IsNullOrWhiteSpace(text))
                return History.Take(limit);
            string lower = text.ToLowerInvariant();
            return History.Where(h =>
                (h.Url ?? "").ToLowerInvariant().Contains(lower) ||
                (h.Title ?? "").ToLowerInvariant().Contains(lower) ||
                (h.Host ?? "").ToLowerInvariant().Contains(lower)).Take(limit);
        }

        public IEnumerable<HistoryEntry> TopSites(int limit = 10)
        {
            return History
                .Where(h => !string.IsNullOrEmpty(h.Host))
                .GroupBy(h => h.Host)
                .Select(g => new HistoryEntry
                {
                    Host = g.Key,
                    Url = g.OrderByDescending(x => x.LastVisit).First().Url,
                    Title = g.OrderByDescending(x => x.Visits).First().Title,
                    Visits = g.Sum(x => x.Visits),
                    LastVisit = g.Max(x => x.LastVisit)
                })
                .OrderByDescending(h => h.Visits)
                .Take(limit)
                .ToList();
        }

        public bool IsBookmarked(string url) => Bookmarks.Any(b => b.Url == url);

        public void ToggleBookmark(string url, string title)
        {
            if (string.IsNullOrWhiteSpace(url))
                return;
            var existing = Bookmarks.FirstOrDefault(b => b.Url == url);
            if (existing != null)
                Bookmarks.Remove(existing);
            else
                Bookmarks.Insert(0, new Bookmark { Url = url, Title = title ?? url });
            SaveBookmarks();
        }

        public IEnumerable<Bookmark> SearchBookmarks(string text, int limit = 5)
        {
            if (string.IsNullOrWhiteSpace(text))
                return Bookmarks.Take(limit);
            string lower = text.ToLowerInvariant();
            return Bookmarks.Where(b =>
                (b.Url ?? "").ToLowerInvariant().Contains(lower) ||
                (b.Title ?? "").ToLowerInvariant().Contains(lower)).Take(limit);
        }

        public void AddDownload(DownloadEntry entry)
        {
            Downloads.Insert(0, entry);
            if (Downloads.Count > 500)
                Downloads = Downloads.Take(500).ToList();
            SaveDownloads();
        }

        public void ExportBookmarksHtml(string path)
        {
            var builder = new System.Text.StringBuilder();
            builder.AppendLine("<!DOCTYPE NETSCAPE-Bookmark-file-1>");
            builder.AppendLine("<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">");
            builder.AppendLine("<TITLE>Bookmarks</TITLE><H1>Bookmarks</H1><DL><p>");
            foreach (var item in Bookmarks)
            {
                string title = System.Security.SecurityElement.Escape(item.Title ?? item.Url);
                builder.AppendLine($"    <DT><A HREF=\"{item.Url}\" ADD_DATE=\"{new DateTimeOffset(item.Created).ToUnixTimeSeconds()}\">{title}</A>");
            }
            builder.AppendLine("</DL><p>");
            File.WriteAllText(path, builder.ToString());
        }
    }
}
