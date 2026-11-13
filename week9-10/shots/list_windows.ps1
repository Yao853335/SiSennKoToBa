# List visible top-level windows (ASCII only). Usage: powershell -File list_windows.ps1
if (-not ('ListWin2' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;
public static class ListWin2 {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc f, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  public static List<string> Dump() {
    var list = new List<string>();
    EnumWindows((h, l) => {
      if (!IsWindowVisible(h)) return true;
      StringBuilder sb = new StringBuilder(512);
      GetWindowTextW(h, sb, sb.Capacity);
      string t = sb.ToString();
      if (t.Length > 0) { uint pid; GetWindowThreadProcessId(h, out pid); list.Add(pid + " | " + t); }
      return true;
    }, IntPtr.Zero);
    return list;
  }
}
'@ -WarningAction SilentlyContinue
}
[ListWin2]::Dump() | Where-Object { $_ -match 'SHOT|nvidia|cmd|WindowsTerminal|python' }
