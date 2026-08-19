using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class BuildScript
{
    [MenuItem("Build/Build Windows Standalone Player")]
    public static void BuildWindowsPlayer()
    {
        string scenePath = "Assets/Scenes/MainTestScene.unity";

        // Create scene directory if needed
        if (!Directory.Exists("Assets/Scenes"))
        {
            Directory.CreateDirectory("Assets/Scenes");
        }

        // Create or open the test scene
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        
        // Add controller GameObject
        GameObject runnerObj = new GameObject("VRCVideoTestController");
        runnerObj.AddComponent<VRChatVideoTester.Core.VRCVideoTestController>();

        EditorSceneManager.SaveScene(scene, scenePath);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        // Setup build options
        string buildDir = "Builds";
        if (!Directory.Exists(buildDir))
        {
            Directory.CreateDirectory(buildDir);
        }

        string locationPathName = Path.Combine(buildDir, "VRChatVideoTester.exe");

        BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions
        {
            scenes = new[] { scenePath },
            locationPathName = locationPathName,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.Development
        };

        Debug.Log($"[BuildScript] Starting Windows Standalone build to: {locationPathName}");
        var report = BuildPipeline.BuildPlayer(buildPlayerOptions);
        var summary = report.summary;

        if (summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
        {
            Debug.Log($"[BuildScript] Build succeeded! Size: {summary.totalSize} bytes");
        }
        else if (summary.result == UnityEditor.Build.Reporting.BuildResult.Failed)
        {
            Debug.LogError($"[BuildScript] Build failed with {summary.totalErrors} errors!");
        }
    }
}
