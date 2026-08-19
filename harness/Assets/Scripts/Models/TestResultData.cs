using System;

namespace VRChatVideoTester.Models
{
    [Serializable]
    public class TestResultData
    {
        public string raw_url;
        public string resolved_url;
        public bool success;
        public string player_backend;
        public string error_message;
        public float total_latency_ms;
        public float ytdlp_ms;
        public float player_latency_ms;
        public bool is_prepared;
        public bool is_playing;
        public ulong width;
        public ulong height;
        public float frame_rate;
        public string ssl_cert_dir;
        public string ssl_cert_file;
        public string gnutls_priority;
        public string mono_tls_provider;
    }
}
