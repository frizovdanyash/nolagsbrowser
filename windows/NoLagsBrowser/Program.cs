using System;
using System.Windows.Forms;

namespace NoLagsBrowser
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.ThreadException += (s, e) => ShowError(e.Exception);
            AppDomain.CurrentDomain.UnhandledException += (s, e) => ShowError(e.ExceptionObject as Exception);

            var storage = new Storage();
            var form = new MainForm(storage, args);
            Application.Run(form);
        }

        private static void ShowError(Exception error)
        {
            if (error == null)
                return;
            MessageBox.Show(error.Message, "NoLags Browser", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
