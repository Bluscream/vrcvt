using System;
using UnityEngine;
using UnityEngine.Video;

namespace VRChatVideoTester.Players
{
    public class UnityVideoPlayerBackend : MonoBehaviour, IVideoTestPlayer
    {
        public string BackendName => "Unity.VideoPlayer";

        public event Action OnPrepareSuccess;
        public event Action OnPlaybackStart;
        public event Action<string> OnPlaybackError;

        private VideoPlayer videoPlayer;

        void Awake()
        {
            videoPlayer = gameObject.AddComponent<VideoPlayer>();
            videoPlayer.playOnAwake = false;
            videoPlayer.renderMode = VideoRenderMode.APIOnly;
            videoPlayer.source = VideoSource.Url;
            videoPlayer.audioOutputMode = VideoAudioOutputMode.Direct;

            videoPlayer.prepareCompleted += (vp) => OnPrepareSuccess?.Invoke();
            videoPlayer.started += (vp) => OnPlaybackStart?.Invoke();
            videoPlayer.errorReceived += (vp, msg) => OnPlaybackError?.Invoke(msg);
        }

        public void PlayUrl(string url, bool enableHwDecoding)
        {
            videoPlayer.url = url;
            videoPlayer.Play();
            videoPlayer.Prepare();
        }

        public void Stop()
        {
            if (videoPlayer != null && videoPlayer.isPlaying)
            {
                videoPlayer.Stop();
            }
        }

        void Update()
        {
            if (videoPlayer != null && videoPlayer.isPlaying && videoPlayer.frame > 0)
            {
                OnPlaybackStart?.Invoke();
            }
        }
    }
}
