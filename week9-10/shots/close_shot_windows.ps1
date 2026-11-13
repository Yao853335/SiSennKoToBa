# 关闭所有标题含指定关键词的遗留展示窗口（WM_CLOSE 温和退出）
param([string]$Needle = "SHOT_UIE")

if (-not ('CloseWin' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class CloseWin {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc f, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextLengthW(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr SendMessageTimeout(IntPtr h, uint msg, IntPtr w, IntPtr l, uint flags, uint ms, out IntPtr res);
  static System.Collections.Generic.List<IntPtr> hits = new System.Collections.Generic.List<IntPtr>();
  static string needle = "";
  public static int CloseAll(string n) {
    needle = n; hits.Clear();
    EnumWindows((h, l) => {
      if (!IsWindowVisible(h)) return true;
      int len = GetWindowTextLengthW(h);
      if (len <= 0 || len > 512) return true;
      StringBuilder sb = new StringBuilder(len + 2);
      GetWindowTextW(h, sb, sb.Capacity);
      if (sb.ToString().IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0) hits.Add(h);
      return true;
    }, IntPtr.Zero);
    foreach (var h in hits) {
      IntPtr r;
      SendMessageTimeout(h, 0x0010 /*WM_CLOSE*/, IntPtr.Zero, IntPtr.Zero, 0x0002 /*SMTO_ABORTIFHUNG*/, 2000, out r);
    }
    return hits.Count;
  }
}
'@ -WarningAction SilentlyContinue
}
$k = [CloseWin]::CloseAll($Needle)
Write-Output "closed=$k"
