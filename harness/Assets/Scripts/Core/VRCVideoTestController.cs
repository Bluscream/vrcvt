using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using UnityEngine;
using VRChatVideoTester.Config;
using VRChatVideoTester.Models;
using VRChatVideoTester.Players;
using VRChatVideoTester.Resolvers;
using Debug = UnityEngine.Debug;

namespace VRChatVideoTester.Core
{
    public class VRCVideoTestController : MonoBehaviour
    {
        private TestConfig config;
        private IVideoTestPlayer activePlayer;
        private Stopwatch totalTimer;
        private float ytdlpMs = 0f;
        private float playerStartMs = 0f;
        private bool testCompleted = false;
        private string finalResolvedUrl = "";

        void Awake()
        {
            config = TestConfig.ParseFromCommandLine();
        }

        void Start()
        {
            totalTimer = Stopwatch.StartNew();
            Debug.Log($"[VRCVideoTestController] Starting Video Test with Config: URL={config.TargetUrl}, AVPro={config.UseAVProBackend}, HW={config.EnableHwDecoding}");

            // 1. Resolve stream URL via VRChat's yt-dlp
            var (resolvedUrl, elapsedMs, success) = YtDlpResolver.ResolveUrl(config.TargetUrl);
            ytdlpMs = elapsedMs;
            finalResolvedUrl = resolvedUrl;

            // 2. Select Player Backend
            GameObject playerObj = new GameObject("PlayerBackendObj");
            playerObj.transform.SetParent(transform);

            if (config.UseAVProBackend)
            {
                activePlayer = playerObj.AddComponent<AVProVideoPlayerBackend>();
            }
            else
            {
                activePlayer = playerObj.AddComponent<UnityVideoPlayerBackend>();
            }

            activePlayer.OnPrepareSuccess += OnPlayerPrepared;
            activePlayer.OnPlaybackStart += OnPlayerStarted;
            activePlayer.OnPlaybackError += OnPlayerError;

            // 3. Begin Playback
            playerStartMs = totalTimer.ElapsedMilliseconds;
            activePlayer.PlayUrl(finalResolvedUrl, config.EnableHwDecoding);
        }

        private void OnPlayerPrepared()
        {
            Debug.Log("[VRCVideoTestController] Player prepare completed successfully.");
        }

        private void OnPlayerStarted()
        {
            long elapsed = totalTimer.ElapsedMilliseconds;
            Debug.Log($"[VRCVideoTestController] Player started successfully in {elapsed} ms!");
            ExportResults(true, "Playback started successfully");
        }

        private void OnPlayerError(string errorMessage)
        {
            Debug.LogError($"[VRCVideoTestController] Player error received: {errorMessage}");
            ExportResults(false, errorMessage);
        }

        private void ExportResults(bool success, string errorMessage)
        {
            if (testCompleted) return;
            testCompleted = true;

            totalTimer.Stop();
            float totalMs = totalTimer.ElapsedMilliseconds;
            float playerMs = totalMs - ytdlpMs;

            var result = new TestResultData
            {
                raw_url = config.TargetUrl,
                resolved_url = finalResolvedUrl,
                success = success,
                player_backend = activePlayer != null ? activePlayer.BackendName : "Unknown",
                error_message = errorMessage,
                total_latency_ms = totalMs,
                ytdlp_ms = ytdlpMs,
                player_latency_ms = playerMs,
                is_prepared = success,
                is_playing = success,
                ssl_cert_dir = config.SslCertDir,
                ssl_cert_file = config.SslCertFile,
                gnutls_priority = config.GnuTlsPriority,
                mono_tls_provider = config.MonoTlsProvider
            };

            string json = JsonUtility.ToJson(result, true);
            Debug.Log($"[VRCVideoTestController] Final Test Result Data:\n{json}");

            try
            {
                File.WriteAllText(config.OutJsonPath, json, Encoding.UTF8);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[VRCVideoTestController] Failed to write outJson: {ex.Message}");
            }

            Application.Quit(success ? 0 : 1);
        }

        void Update()
        {
            if (!testCompleted && totalTimer != null && totalTimer.ElapsedMilliseconds > 25000)
            {
                Debug.LogError("[VRCVideoTestController] Execution timed out after 25 seconds!");
                ExportResults(false, "Timeout after 25s");
            }
        }
    }
}
