using System;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace VRChatVideoTester.Resolvers
{
    public class YtDlpResolver
    {
        public static string FindYtDlpExecutable()
        {
            // 1. Check VRChat's localAppDataLow tools directory
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrEmpty(localAppData))
            {
                string vrchatYtdlp = Path.Combine(localAppData + "Low", "VRChat", "VRChat", "Tools", "yt-dlp.exe");
                if (File.Exists(vrchatYtdlp))
                {
                    Debug.Log($"[YtDlpResolver] Found VRChat bundled yt-dlp at: {vrchatYtdlp}");
                    return vrchatYtdlp;
                }
            }

            // 2. Check drive_c AppDataLow default path under Wine/Proton
            string driveCYtdlp = @"C:\users\steamuser\AppData\LocalLow\VRChat\VRChat\Tools\yt-dlp.exe";
            if (File.Exists(driveCYtdlp))
            {
                Debug.Log($"[YtDlpResolver] Found Wine drive_c yt-dlp at: {driveCYtdlp}");
                return driveCYtdlp;
            }

            // 3. Fallback to PATH
            return "yt-dlp";
        }

        public static (string resolvedUrl, float elapsedMs, bool success) ResolveUrl(string rawUrl)
        {
            if (string.IsNullOrEmpty(rawUrl) || rawUrl.StartsWith("file:") || rawUrl.EndsWith(".mp4") || rawUrl.EndsWith(".m3u8"))
            {
                return (rawUrl, 0f, true);
            }

            string ytdlpPath = FindYtDlpExecutable();
            var timer = Stopwatch.StartNew();

            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = ytdlpPath,
                    Arguments = $"-g -f \"best[ext=mp4]/best\" \"{rawUrl}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (var proc = Process.Start(psi))
                {
                    string output = proc.StandardOutput.ReadToEnd();
                    proc.WaitForExit(15000);
                    timer.Stop();

                    string[] lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    if (lines.Length > 0 && lines[0].StartsWith("http"))
                    {
                        string directUrl = lines[0].Trim();
                        Debug.Log($"[YtDlpResolver] Resolved stream URL in {timer.ElapsedMilliseconds} ms:\n{directUrl}");
                        return (directUrl, timer.ElapsedMilliseconds, true);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[YtDlpResolver] Resolution warning: {ex.Message}");
            }

            timer.Stop();
            return (rawUrl, timer.ElapsedMilliseconds, false);
        }
    }
}
