import csnGUIHandler

handler = csnGUIHandler.Handler()
handler.SetCMakePath("D:/Program Files (x86)/CMake 2.4/bin/cmake.exe")
# the following is only needed if you want to build the tests on the target machine
handler.SetPythonPath("D:/Python24/python.exe")
handler.SetCompiler("Visual Studio 7 .NET 2003") # 
handler.SetCMakeBuildType("") # or "Release" or "Debug"

settings = csnGUIHandler.Settings()
settings.Load("settings.CSnakeGUI")

if False:
    taskMsg = "ConfigureThirdPartyFolder from %s to %s..." % (settings.thirdPartyRootFolder, settings.thirdPartyBinFolder) 
    print "Starting task: " + taskMsg  
    result = handler.ConfigureThirdPartyFolder(settings)
    assert result, "Task failed: ConfigureThirdPartyFolder" 
    print "Finished " + taskMsg + "\nPlease build the 3rd party sources then press enter...\n"
    raw_input()

taskMsg = "InstallBinariesToBinFolder to %s..." % (settings.binFolder)
print "Starting task: " + taskMsg 
result = handler.InstallBinariesToBinFolder(settings)
assert result, "Task failed: InstallBinariesToBinFolder" 
print "Finished task: " + taskMsg

taskMsg = "ConfigureProjectToBinFolder to %s..." % (settings.binFolder)
print "Starting task: " + taskMsg 
result = handler.ConfigureProjectToBinFolder(settings, _alsoRunCMake = True)
assert result, "Task failed: ConfigureProjectToBinFolder" 
print "Finished task: " + taskMsg + "\nPlease build the sources in %s.\n" % handler.GetTargetSolutionPath(settings)
