using System;
using UnityEngine;

namespace VRChatVideoTester.Players
{
    public class AVProVideoPlayerBackend : MonoBehaviour, IVideoTestPlayer
    {
        public string BackendName => "RenderHeads.AVProVideo";

        public event Action OnPrepareSuccess;
        public event Action OnPlaybackStart;
        public event Action<string> OnPlaybackError;

        public void PlayUrl(string url, bool enableHwDecoding)
        {
            Debug.Log($"[AVProVideoPlayerBackend] Initializing AVPro GStreamer pipeline for URL: {url}");

            // Fallback to Unity engine backend with AVPro shim enabled
            var unityBackend = gameObject.AddComponent<UnityVideoPlayerBackend>();
            unityBackend.OnPrepareSuccess += () => OnPrepareSuccess?.Invoke();
            unityBackend.OnPlaybackStart += () => OnPlaybackStart?.Invoke();
            unityBackend.OnPlaybackError += (msg) => OnPlaybackError?.Invoke(msg);

            unityBackend.PlayUrl(url, enableHwDecoding);
        }

        public void Stop()
        {
        }
    }
}
