# 截图辅助模块：找窗口 + BitBlt/PrintWindow 抓窗体画面
# 用法：. $dir\capture_lib.ps1 ; $h = Find-WindowByTitle 'xxx'; Save-CaptureWindow $h 'D:\path\shot.png'

if (-not ('CapGdi' -as [type])) {
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;

public static class CapGdi {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc f, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowTextLengthW(IntPtr h);
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr GetWindowDC(IntPtr h);
  [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("gdi32.dll")] static extern bool BitBlt(IntPtr d, int dx, int dy, int w, int ht, IntPtr s, int sx, int sy, uint rop);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);

  public static IntPtr FindBySubstring(string needle) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => {
      if (found != IntPtr.Zero) return true;
      if (!IsWindowVisible(h)) return true;
      int len = GetWindowTextLengthW(h);
      if (len <= 0 || len > 512) return true;
      StringBuilder sb = new StringBuilder(len + 2);
      GetWindowTextW(h, sb, sb.Capacity);
      if (sb.ToString().IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0) found = h;
      return true;
    }, IntPtr.Zero);
    return found;
  }

  public static void Front(IntPtr h, int x, int y, int cx, int cy) {
    BringWindowToTop(h);
    SetForegroundWindow(h);
    SetWindowPos(h, (IntPtr)(-1), x, y, cx, cy, 0x0040); // SWP_SHOWWINDOW
  }

  public static void Save(WindowInfo wi, string path) {
    RECT r; GetWindowRect(wi.H, out r);
    int w = r.Right - r.Left, ht = r.Bottom - r.Top;
    if (w < 80 || ht < 60) throw new Exception("invalid window rect " + w + "x" + ht);
    using (Bitmap bmp = new Bitmap(w, ht, PixelFormat.Format32bppArgb)) {
      using (Graphics g = Graphics.FromImage(bmp)) {
        IntPtr hdc = g.GetHdc();
        bool ok = false;
        try { ok = PrintWindow(wi.H, hdc, 2); } catch { }
        if (!ok) {
          IntPtr src = GetWindowDC(wi.H);
          try { ok = BitBlt(hdc, 0, 0, w, ht, src, 0, 0, 0x00CC0020 /*SRCCOPY*/); } finally { ReleaseDC(wi.H, src); }
        }
        g.ReleaseHdc(hdc);
        if (!ok) throw new Exception("capture failed");
        bmp.Save(path, ImageFormat.Png);
      }
    }
  }

  public class WindowInfo { public IntPtr H; public WindowInfo(IntPtr h) { H = h; } }
}
'@ -WarningAction SilentlyContinue
}

function Find-WindowByTitle {
  param([string]$Needle, [int]$TimeoutSec = 120)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    $h = [CapGdi]::FindBySubstring($Needle)
    if ($h -ne [IntPtr]::Zero) { return $h }
    Start-Sleep -Milliseconds 400
  }
  return [IntPtr]::Zero
}

function Save-CaptureWindow {
  param([IntPtr]$Hwnd, [string]$OutPath)
  $wi = New-Object CapGdi+WindowInfo $Hwnd
  [CapGdi]::Save($wi, $OutPath)
}

function Set-WindowFront {
  param([IntPtr]$Hwnd, [int]$X = 0, [int]$Y = 0, [int]$W = 1360, [int]$H = 860)
  [CapGdi]::Front($Hwnd, $X, $Y, $W, $H)
}
