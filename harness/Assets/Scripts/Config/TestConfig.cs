using System;
using UnityEngine;

namespace VRChatVideoTester.Config
{
    public class TestConfig
    {
        public string TargetUrl { get; set; } = "https://media.w3.org/2010/05/sintel/trailer.mp4";
        public string OutJsonPath { get; set; } = "VRCVideoTestResult.json";
        public bool UseAVProBackend { get; set; } = false;
        public bool DisableHwDecoding { get; set; } = false;
        public bool EnableHwDecoding { get; set; } = true;

        // SSL / TLS Environment Overrides
        public string SslCertDir { get; set; } = "/etc/ssl/certs";
        public string SslCertFile { get; set; } = "/etc/ssl/certs/ca-certificates.crt";
        public string GnuTlsPriority { get; set; } = "NORMAL";
        public string MonoTlsProvider { get; set; } = "btls";

        public static TestConfig ParseFromCommandLine()
        {
            var config = new TestConfig();
            string[] args = Environment.GetCommandLineArgs();

            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i];

                if ((arg == "--url" || arg == "-videoUrl") && i + 1 < args.Length)
                {
                    config.TargetUrl = args[++i];
                }
                else if (arg == "-outJson" && i + 1 < args.Length)
                {
                    config.OutJsonPath = args[++i];
                }
                else if (arg == "--enable-avpro-in-proton" || arg == "--use-avpro")
                {
                    config.UseAVProBackend = true;
                }
                else if (arg == "--disable-hw-video-decoding")
                {
                    config.DisableHwDecoding = true;
                    config.EnableHwDecoding = false;
                }
                else if (arg == "--enable-hw-video-decoding")
                {
                    config.EnableHwDecoding = true;
                    config.DisableHwDecoding = false;
                }
                else if (arg == "--ssl-cert-dir" && i + 1 < args.Length)
                {
                    config.SslCertDir = args[++i];
                }
                else if (arg == "--ssl-cert-file" && i + 1 < args.Length)
                {
                    config.SslCertFile = args[++i];
                }
                else if (arg == "--gnutls-priority" && i + 1 < args.Length)
                {
                    config.GnuTlsPriority = args[++i];
                }
                else if (arg == "--mono-tls-provider" && i + 1 < args.Length)
                {
                    config.MonoTlsProvider = args[++i];
                }
            }

            config.ApplyTlsEnvironment();
            return config;
        }

        public void ApplyTlsEnvironment()
        {
            try
            {
                if (!string.IsNullOrEmpty(SslCertDir))
                    Environment.SetEnvironmentVariable("SSL_CERT_DIR", SslCertDir);

                if (!string.IsNullOrEmpty(SslCertFile))
                    Environment.SetEnvironmentVariable("SSL_CERT_FILE", SslCertFile);

                if (!string.IsNullOrEmpty(GnuTlsPriority))
                    Environment.SetEnvironmentVariable("G_TLS_GNUTLS_PRIORITY", GnuTlsPriority);

                if (!string.IsNullOrEmpty(MonoTlsProvider))
                    Environment.SetEnvironmentVariable("MONO_TLS_PROVIDER", MonoTlsProvider);

                Debug.Log($"[TestConfig] TLS Environment Applied: SSL_CERT_DIR={SslCertDir}, SSL_CERT_FILE={SslCertFile}, G_TLS_GNUTLS_PRIORITY={GnuTlsPriority}");
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[TestConfig] Failed to set TLS env vars: {ex.Message}");
            }
        }
    }
}
