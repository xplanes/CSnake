import csnGUIHandler
import csnGenerator
import csnContext
import sys
from optparse import OptionParser

parser = OptionParser(usage="%prog contextFile [options]")
parser.add_option("-i", "--install", dest="install", action="store_true", default=False, help="install files to build folder")
parser.add_option("-t", "--thirdParty", dest="thirdParty", action="store_true", default=False, help="configure third party projects")
(commandLineOptions, commandLineArgs) = parser.parse_args()

if len(commandLineArgs) != 1:
    parser.print_usage()
    sys.exit(1)
    
handler = csnGUIHandler.Handler()
context = handler.LoadContext(commandLineArgs[0])

if commandLineOptions.thirdParty:
    taskMsg = "ConfigureThirdPartyFolder from %s to %s..." % (context.thirdPartyRootFolder, context.thirdPartyBuildFolder) 
    print "Starting task: " + taskMsg  
    result = handler.ConfigureThirdPartyFolder()
    assert result, "\n\nTask failed: ConfigureThirdPartyFolder" 
    print "Finished " + taskMsg + "\nPlease build the 3rd party sources then press enter...\n"
    raw_input()

if commandLineOptions.install:
    taskMsg = "InstallBinariesToBuildFolder to %s..." % (context.buildFolder)
    print "Starting task: " + taskMsg 
    result = handler.InstallBinariesToBuildFolder()
    assert result, "\n\nTask failed: InstallBinariesToBuildFolder" 
    print "Finished task: " + taskMsg

taskMsg = "ConfigureProjectToBuildFolder to %s..." % (context.buildFolder)
print "Starting task: " + taskMsg 
result = handler.ConfigureProjectToBuildFolder(_alsoRunCMake = True)
assert result, "\n\nTask failed: ConfigureProjectToBuildFolder" 
print "Finished task: " + taskMsg + "\nPlease build the sources in %s.\n" % handler.GetTargetSolutionPath()
