using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace NoLagsBrowser
{
    internal static class WinNative
    {
        [DllImport("psapi.dll")]
        private static extern int EmptyWorkingSet(IntPtr process);

        [DllImport("kernel32.dll")]
        private static extern IntPtr GetCurrentProcess();

        [DllImport("user32.dll")]
        private static extern bool SetProcessWorkingSetSize(IntPtr process, IntPtr minimum, IntPtr maximum);

        public static void TrimMemory()
        {
            EmptyWorkingSet(GetCurrentProcess());
            SetProcessWorkingSetSize(GetCurrentProcess(), new IntPtr(-1), new IntPtr(-1));
            foreach (var process in Process.GetProcessesByName("msedgewebview2"))
            {
                try
                {
                    EmptyWorkingSet(process.Handle);
                }
                catch
                {
                }
            }
            GC.Collect();
            GC.WaitForPendingFinalizers();
            GC.Collect();
        }

        public static long CurrentMemoryMb()
        {
            long total = 0;
            try
            {
                total += Process.GetCurrentProcess().WorkingSet64;
                foreach (var process in Process.GetProcessesByName("msedgewebview2"))
                {
                    try
                    {
                        total += process.WorkingSet64;
                    }
                    catch
                    {
                    }
                }
            }
            catch
            {
            }
            return total / (1024 * 1024);
        }
    }
}
