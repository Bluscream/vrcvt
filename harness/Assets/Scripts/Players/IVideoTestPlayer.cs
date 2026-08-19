using System;

namespace VRChatVideoTester.Players
{
    public interface IVideoTestPlayer
    {
        string BackendName { get; }
        event Action OnPrepareSuccess;
        event Action OnPlaybackStart;
        event Action<string> OnPlaybackError;

        void PlayUrl(string url, bool enableHwDecoding);
        void Stop();
    }
}
