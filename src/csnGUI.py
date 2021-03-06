## @package csnGUI
# Definition of main application CSnakeGUIApp. 

#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
import wxversion
import sys
if not getattr(sys, 'frozen', False):
    wxversion.select('2.8')

from wx import xrc
import csnGUIHandler
import csnGUIOptions
import csnContext
import csnProject
from csnListener import ChangeListener, ProgressListener, ProgressEvent
import csnBuild
import csnUtility
import os.path
import shutil
import string
import time
import subprocess
import xrcbinder
from optparse import OptionParser
from about import About
import wx.grid
import wx.lib.agw.customtreectrl as ct

# Only there to allow its inclusion when generating executables.
import csnCilab #@UnusedImport
import webbrowser
import logging
import copy
import re
import traceback
from wx._core import EVT_MENU

class AskUser:
    def __init__(self, frame):
        self.__questionType = wx.YES_NO
        self.__frame = frame
    
    def QuestionYesNo(self):
        return wx.YES_NO
    
    def AnswerYes(self):
        return wx.ID_YES
    
    def AnswerNo(self):
        return wx.ID_NO
    
    def SetType(self, questionType):
        self.__questionType = questionType
    
    def Ask(self, message, defaultAnswer):
        dlg = wx.MessageDialog(self.__frame, message, 'Question', style = self.__questionType | wx.ICON_QUESTION)
        return dlg.ShowModal()

class PathPickerCtrl(wx.Control):
    def __init__(self, parent, id=-1, pos=(-1,-1), size=(-1,-1), style=0, validator=wx.DefaultValidator, name="PathPicker", evtHandler=None, folderName="Folder"):
        wx.Control.__init__(self, parent, id=id, pos=pos, size=size, style=style|wx.BORDER_NONE, validator=validator, name=name)
        
        self.evtHandler = evtHandler
        
        self.oldValue = None
        self.grid = None
        self.row = None
        self.col = None
        self.handlerConnected = False
        self.folderName = folderName
        self.dontLeaveEditMode = False
        
        self.panel = wx.Panel(self, style = wx.BORDER_NONE)
        self.text = wx.TextCtrl(self.panel, style = wx.TE_PROCESS_TAB | wx.TE_PROCESS_ENTER)
        self.button = wx.Button(self.panel, label='...')
        self.button.SetMinSize((30, -1))
        self.panel.Bind(wx.EVT_BUTTON, self.OnButtonClick)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.text, flag=wx.EXPAND, proportion=1)
        self.sizer.Add(self.button, flag=wx.EXPAND, proportion=0)
        self.panel.SetSizer(self.sizer)
        
        self.windows = [self, self.panel, self.text, self.button]
        for window in self.windows:
            window.Bind(wx.EVT_KILL_FOCUS, self.OnSomeoneLostFocus)
        self.Bind(wx.EVT_SET_FOCUS, self.OnGotFocus)
        self.text.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.button.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        
    def OnButtonClick(self, event):
        self.dontLeaveEditMode = True
        oldValue = self.text.GetValue()
        dlg = wx.DirDialog(None, "Select %s" % self.folderName, oldValue, wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text.SetValue(dlg.GetPath().replace("\\", "/"))
            self.MoveGridCursor(0, 0)
        self.dontLeaveEditMode = False
        
    def OnKeyDown(self, event):
        if event.GetKeyCode()==wx.WXK_TAB:
            self.MoveGridCursor(0, 1)
            event.Skip(False)
        elif event.GetKeyCode()==wx.WXK_RETURN:
            self.MoveGridCursor(1, 0)
            event.Skip(False)
        elif event.GetKeyCode()==wx.WXK_ESCAPE:
            self.SetValue(self.oldValue)
            self.MoveGridCursor(0, 0)
            self.grid.SetFocus()
            event.Skip(False)
        else:
            event.Skip(True)
    
    def MoveGridCursor(self, diffRow, diffCol):
        newRow = self.row + diffRow
        self.grid.SetFocus()
        if newRow >= self.grid.GetTable().GetNumberRows():
            newRow = self.row
        newCol = self.col + diffCol
        if newCol >= self.grid.GetTable().GetNumberCols():
            newCol = self.col
        self.grid.SetGridCursor(newRow, newCol)
        self.grid.ClearSelection()
        self.grid.SelectRow(newRow)
    
    def OnGotFocus(self, event):
        self.text.SetFocus()
        event.Skip()
        
    def OnSomeoneLostFocus(self, event):
        if not self.handlerConnected:
            if not (self.FindFocus() in self.windows) and not self.dontLeaveEditMode:
                self.evtHandler.ProcessEvent(event)
    
    def SetDimensions(self, x, y, width, height, sizeFlags):
        wx.Control.SetDimensions(self, x, y, width, height, sizeFlags)
        self.panel.SetDimensions(x=0, y=0, width=width, height=height, sizeFlags=sizeFlags)
    
    def SetInitialValue(self, value):
        self.oldValue = value
        self.SetValue(value)
        
    def SetValue(self, value):
        self.text.SetValue(value)
        self.text.SetInsertionPointEnd()
        
    def GetValue(self):
        return self.text.GetValue()
    
    def SetGrid(self, row, col, grid):
        self.row = row
        self.col = col
        self.grid = grid
    
class PathPickerEditor(wx.grid.PyGridCellEditor):
    def __init__(self, folderName = "Folder"):
        wx.grid.PyGridCellEditor.__init__(self)
        self.handlerConnected = False
        self.folderName = folderName
    
    def ConnectHandler(self):
        if not self.handlerConnected:
            self._picker.PushEventHandler(self.evtHandler)
            self.handlerConnected = True
            self._picker.handlerConnected = True

    def DisconnectHandler(self):
        if self.handlerConnected:
            self._picker.PopEventHandler()
            self.handlerConnected = False
            self._picker.handlerConnected = False
    
    def Create(self, parent, id, evtHandler):
        self._picker = PathPickerCtrl(parent=parent, id=id, evtHandler=evtHandler, folderName=self.folderName)
        self.value = ""
        self.SetControl(self._picker)
        self.evtHandler = evtHandler
        self.ConnectHandler()
 
    def SetSize(self, rect):
        self._picker.SetDimensions(rect.x, rect.y, rect.width, rect.height, wx.SIZE_ALLOW_MINUS_ONE)
 
    def Show(self, show, attr):
        super(PathPickerEditor, self).Show(show, attr)
 
    def PaintBackground(self, rect, attr):
        pass
 
    def BeginEdit(self, row, col, grid):
        self.DisconnectHandler()
        self.value = str(grid.GetTable().GetValue(row, col)).strip()
        self._picker.SetInitialValue(self.value)
        self._picker.SetGrid(row, col, grid)
        self._picker.SetFocus()
 
    def EndEdit(self, row, col, grid):
        changed = False
        value = self._picker.GetValue()
        if value != self.value:
            changed = True
            grid.SetCellValue(row, col, value) # update the table
            self.value = value
        self.ConnectHandler()
        return changed
 
    def Reset(self):
        pass
 
    def IsAcceptedKey(self, evt):
        return (not (evt.ControlDown() or evt.AltDown()) and
                evt.GetKeyCode() != wx.WXK_SHIFT)
 
    def StartingKey(self, evt):
        key = evt.GetKeyCode()
        if key in [ wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3,
                    wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7,
                    wx.WXK_NUMPAD8, wx.WXK_NUMPAD9
                    ]:
 
            ch = chr(ord('0') + key - wx.WXK_NUMPAD0)
            self._picker.SetValue(ch)
        elif key < 256 and key >= 0 and chr(key) in string.printable:
            ch = chr(key)
            self._picker.SetValue(ch)
        elif key in [wx.WXK_DELETE, wx.WXK_BACK]:
            self._picker.SetValue("")
        
        evt.Skip()
 
    def StartingClick(self):
        pass
 
    def Clone(self):
        return PathPickerEditor(folderName = self.folderName)

class SelectFolderCallback:
    """ 
    Lets the user choose a path, then calls 'callback' to set the path value in the domain layer, 
    and calls app.UpdateGUI.
    """
    def __init__(self, message, callbackGet, callbackSet, app):
        self.message = message
        self.callbackGet = callbackGet
        self.callbackSet = callbackSet
        self.app = app
        
    def __call__(self, event = None):
        oldValue = self.callbackGet()
        
        dlg = wx.DirDialog(None, self.message, oldValue, wx.DD_DIR_MUST_EXIST)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.callbackSet(dlg.GetPath().replace("\\", "/"))
        self.app.UpdateGUI()

class FileDrop(wx.FileDropTarget):
    def __init__(self, app):
        wx.FileDropTarget.__init__(self)
        self.__app = app

    def OnDropFiles(self, x, y, filenames):
        self.__app.LoadContext(filenames[0])
        
class CSnakeGUIApp(wx.App):
    def OnInit(self):
        # logging init
        self.__logger = logging.getLogger("CSnake")
        self.__logger.debug("method: OnInit")
        
        # initalise main vars 
        
        self.destroyed = False
        self.listOfPossibleTargets = []
        
        self.__projectTreeIsDrawn = False
        self.__projectTree = None
        
        self.context = None
        self.options = None
        self.originalContextData = None
        self.contextFilename = None
        self.contextModified = False
        self.changeListener = ChangeListener(self)
        self.progressListener = ProgressListener(self)
        self.__cancelAction = False
        # pair of wx.id and recent context path
        self.__recentContextPaths = []
       
        self.projectNeedUpdate = False
        self.__currentSolutionPath = None
        
        # flag to know if running a configure all
        self.__runningConfigureAll = False 
        
        wx.InitAllImageHandlers()
        
        xrcFile = csnUtility.GetRootOfCSnake() + "/resources/csnGUI.xrc"
        self.res = xrc.XmlResource(xrcFile)
        
        self.csnakeFolder = csnUtility.GetCSnakeUserFolder()
        self.thisFolder = None
            
        # launch init methods
        self.InitFrame()
        self.InitMenu()
        self.InitOtherGUIStuff()
        self.Initialize()
        self.SetTopWindow(self.frame)

        self.__logger.debug("end method: OnInit")

        return 1

    def InitFrame(self):
        # debug log
        self.__logger.debug("method: InitFrame")
        
        self.frame = self.res.LoadFrame(None, "frmCSnakeGUI")
        
        dt = FileDrop(self)
        self.frame.SetDropTarget(dt)
        
        self.binder = xrcbinder.Binder(self, self.frame)
        
        self.textLog = xrc.XRCCTRL(self.frame, "textLog")
        self.binder.AddTextControl("txtBuildFolder", buddyClass = "context", buddyField = "_ContextData__buildFolder", isFilename = True)
        self.binder.AddTextControl("txtCMakePath", buddyClass = "context", buddyField = "_ContextData__cmakePath", isFilename = True)
        self.binder.AddTextControl("txtPythonPath", buddyClass = "context", buddyField = "_ContextData__pythonPath", isFilename = True)
        self.binder.AddTextControl("txtVisualStudioPath", buddyClass = "context", buddyField = "_ContextData__idePath", isFilename = True)
        # not the good buddyField since combo has "instance - csn file" format...
        self.binder.AddComboBox("cmbCSnakeFile", valueListFunctor = self.GetCSnakeFileComboBoxItems, buddyClass = "context", buddyField = "_ContextData__csnakeFile", isFilename = True)
        self.binder.AddComboBox("cmbInstance", valueListFunctor = self.GetInstanceComboBoxItems, buddyClass = "context", buddyField = "_ContextData__instance")
        self.binder.AddDropDownList("cmbCompiler", valueListFunctor = self.GetCompilerComboBoxItems, buddyClass = "context", buddyField = "_ContextData__compilername")
        self.binder.AddDropDownList("cmbBuildType", valueListFunctor = self.GetBuildTypeComboBoxItems, buddyClass = "context", buddyField = "_ContextData__configurationName")
        self.binder.AddListBox("lbxRootFolders", buddyClass = "context", buddyField = "_ContextData__rootFolders", isFilename = True)
        self.binder.AddCheckBox("chkAskToLaunchVisualStudio", buddyClass = "options", buddyField = "_Options__askToLaunchIDE")
        
        self.binder.AddGrid("gridThirdPartySrcAndBuildFolders", buddyClass = "context", buddyField = "_ContextData__thirdPartySrcAndBuildFolders", isFilename = True)

        self.noteBook = xrc.XRCCTRL(self.frame, "noteBook")
        self.noteBook.SetSelection(0)
        
        self.panelSelectProjects = xrc.XRCCTRL(self.frame, "panelSelectProjects")
        self.statusBar = xrc.XRCCTRL(self.frame, "statusBar")

        self.panelContext = xrc.XRCCTRL(self.frame, "panelContext")
        self.panelOptions = xrc.XRCCTRL(self.frame, "panelOptions")

        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select Binary Folder", self.GetBuildFolder, self.SetBuildFolder, self), id=xrc.XRCID("btnSelectBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Add root folder", self.GetLastRootFolder, self.AddRootFolder, self), id=xrc.XRCID("btnAddRootFolder"))

        self.frame.Bind(wx.EVT_BUTTON, self.OnDetectRootFolders, id=xrc.XRCID("btnDetectRootFolders"))

        self.frame.Bind(wx.EVT_BUTTON, self.OnAddThirdPartySrcAndBuildFolder, id=xrc.XRCID("btnAddThirdPartySrcAndBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnRemoveThirdPartySrcAndBuildFolder, id=xrc.XRCID("btnRemoveThirdPartySrcAndBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnMoveUpThirdPartySrcAndBuildFolder, id=xrc.XRCID("btnMoveUpThirdPartySrcAndBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnMoveDownThirdPartySrcAndBuildFolder, id=xrc.XRCID("btnMoveDownThirdPartySrcAndBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnConfigureThirdPartySrcAndBuildFolder, id=xrc.XRCID("btnConfigureThirdPartySrcAndBuildFolder"))

        self.frame.Bind(wx.EVT_BUTTON, self.OnSetCMakePath, id=xrc.XRCID("btnSetCMakePath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSetPythonPath, id=xrc.XRCID("btnSetPythonPath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSelectCSnakeFile, id=xrc.XRCID("btnSelectCSnakeFile"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSetVisualStudioPath, id=xrc.XRCID("btnSetVisualStudioPath"))

        self.frame.Bind(wx.EVT_BUTTON, self.OnRefreshProjects, id=xrc.XRCID("btnForceRefreshProjects"))
        self.btnForceRefreshProjects = xrc.XRCCTRL(self.frame, "btnForceRefreshProjects")
        
        self.frame.Bind(wx.EVT_BUTTON, self.OnRemoveRootFolder, id=xrc.XRCID("btnRemoveRootFolder"))
        self.frame.Bind(wx.EVT_COMBOBOX, self.OnSelectRecentlyUsed, id=xrc.XRCID("cmbCSnakeFile"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnUpdateListOfTargets, id=xrc.XRCID("btnUpdateListOfTargets"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnCreateCMakeFilesAndRunCMake, id=xrc.XRCID("btnCreateCMakeFilesAndRunCMake"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnConfigureALL, id=xrc.XRCID("btnConfigureALL"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnConfigureThirdPartyFolder, id=xrc.XRCID("btnConfigureThirdPartyFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnInstallFilesToBuildFolder, id=xrc.XRCID("btnInstallFilesToBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnLaunchIDE, id=xrc.XRCID("btnLaunchIDE"))
        self.frame.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNoteBookPageChanged, id=xrc.XRCID("noteBook"))
        self.frame.Bind(wx.EVT_COMBOBOX, self.OnSelectCompiler, id=xrc.XRCID("cmbCompiler"))
        
        self.frame.Bind(wx.EVT_LISTBOX_DCLICK, self.OnRootFoldersDClick, id=xrc.XRCID("lbxRootFolders"))
        self.frame.Bind(wx.EVT_LISTBOX_DCLICK, self.OnThirdPartyFoldersDClick, id=xrc.XRCID("lbxThirdPartyFolders"))
        self.frame.Bind(wx.EVT_LISTBOX_DCLICK, self.OnThirdPartyBuildFoldersDClick, id=xrc.XRCID("lbxThirdPartyBuildFolders"))
        
        if not csnUtility.IsWindowsPlatform():
            #xrc.XRCCTRL(self.panelContext, "btnConfigureALL").Disable()
            xrc.XRCCTRL(self.panelContext, "btnLaunchIDE").Disable()
            xrc.XRCCTRL(self.panelOptions, "btnSetVisualStudioPath").Disable()
            xrc.XRCCTRL(self.panelOptions, "txtVisualStudioPath").Disable()
            xrc.XRCCTRL(self.panelOptions, "chkAskToLaunchVisualStudio").Disable()
        
        self.gridThirdPartySrcAndBuildFolders.CreateGrid(0,2)
        self.gridThirdPartySrcAndBuildFolders.SetColLabelValue(0, "Source folder")
        self.gridThirdPartySrcAndBuildFolders.SetColLabelValue(1, "Build folder")
        self.gridThirdPartySrcAndBuildFolders.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnThirdPartySrcAndBuildFolderSelectCell)
        
        attrThirdPartySrc = wx.grid.GridCellAttr()
        attrThirdPartySrc.SetEditor(PathPickerEditor(folderName = "Third Party Source Folder"))
        attrThirdPartyBin = wx.grid.GridCellAttr()
        attrThirdPartyBin.SetEditor(PathPickerEditor(folderName = "Third Party Build Folder"))
        self.gridThirdPartySrcAndBuildFolders.SetColAttr(0, attrThirdPartySrc)
        self.gridThirdPartySrcAndBuildFolders.SetColAttr(1, attrThirdPartyBin)
        self.gridThirdPartySrcAndBuildFolders.ForceRefresh()

    def OnRootFoldersDClick(self, event):
        """Handles the wx.EVT_LISTBOX_DCLICK event for lbxRootFolders"""
        if csnUtility.IsWindowsPlatform():
            folder_path = csnUtility.UnNormalizePath( self.lbxRootFolders.GetStringSelection() )
            os.system("explorer " + folder_path)

    def OnThirdPartyFoldersDClick(self, event):
        """Handles the wx.EVT_LISTBOX_DCLICK event for lbxThirdPartyFolders"""
        if csnUtility.IsWindowsPlatform():
            folder_path = csnUtility.UnNormalizePath( self.lbxThirdPartyFolders.GetStringSelection() )
            os.system("explorer " + folder_path)

    def OnThirdPartyBuildFoldersDClick(self, event):
        """Handles the wx.EVT_LISTBOX_DCLICK event for lbxThirdPartyBuildFolders"""
        if csnUtility.IsWindowsPlatform():
            folder_path = csnUtility.UnNormalizePath( self.lbxThirdPartyBuildFolders.GetStringSelection() )
            os.system("explorer " + folder_path)
        
    def OnNoteBookPageChanged(self, event):
        if self.noteBook.GetPageText(self.noteBook.GetSelection()) == "Select Projects":
            self.DoActions([self.ActionSelectProjects])
        
    def EnableConfigBar(self, enable):
        if enable:
            xrc.XRCCTRL(self.panelContext, "btnCreateCMakeFilesAndRunCMake").Enable()
            xrc.XRCCTRL(self.panelContext, "btnInstallFilesToBuildFolder").Enable()  
            xrc.XRCCTRL(self.panelContext, "btnConfigureThirdPartyFolder").Enable()
        else:
            xrc.XRCCTRL(self.panelContext, "btnCreateCMakeFilesAndRunCMake").Disable()
            xrc.XRCCTRL(self.panelContext, "btnInstallFilesToBuildFolder").Disable() 
            xrc.XRCCTRL(self.panelContext, "btnConfigureThirdPartyFolder").Disable()
            
    def InitMenu(self):
        # debug log
        self.__logger.debug("method: InitMenu")

        # File
        self.frame.Bind(wx.EVT_MENU, self.OnContextNew, id=xrc.XRCID("mnuContextNew"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextOpen, id=xrc.XRCID("mnuContextOpen"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextSave, id=xrc.XRCID("mnuContextSave"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextSaveAs, id=xrc.XRCID("mnuContextSaveAs"))
        self.frame.Bind(wx.EVT_MENU, self.OnExit, id=xrc.XRCID("mnuExit"))
        # Help
        self.frame.Bind(wx.EVT_MENU, self.OnHelp, id=xrc.XRCID("mnuHelp"))
        self.frame.Bind(wx.EVT_MENU, self.OnAbout, id=xrc.XRCID("mnuAbout"))
        
    def InitRecentContextPathsDisplay(self):
        """ Initialise recent context list. """
        # debug log
        self.__logger.debug("method: InitRecentContextPathsDisplay")
        # get the menu
        menuBar = self.frame.GetMenuBar()
        id = menuBar.FindMenu("File")
        filemenu = menuBar.GetMenu( id )
        numberOfItems = 5 # New, Open, Save, Save As, Exit
        assert( filemenu.GetMenuItemCount() == numberOfItems )
        # insert separator
        # items before: new, open, save and save as
        filemenu.InsertSeparator(numberOfItems-1)
        filemenu.InsertSeparator(numberOfItems)
        # insert paths
        # items before: new, open, save, save as, separator
        pos = numberOfItems
        for index in range(self.options.GetRecentContextPathLength()):
            # context path
            path = self.options.GetRecentContextPath(index)
            head, tail = os.path.split( path )
            # insert
            wxid = wx.NewId()
            filemenu.Insert(pos, wxid, tail, "Open '%s'" % path )
            self.__recentContextPaths.append( [wxid, path] )
            EVT_MENU(self, wxid, self.OnOpenRecent)
            pos = pos + 1

    def __AddRecentContextPath(self, path):
        """ Add a recent context to the options and GUI. """
        # Check if already saved
        if self.options.GetRecentContextPathLength() > 0 and self.options.GetRecentContextPath(0) == path:
            return
        # Add to the options
        self.options.PushRecentContextPath(path)
        # Add to the GUI
        menuBar = self.frame.GetMenuBar()
        id = menuBar.FindMenu("File")
        filemenu = menuBar.GetMenu( id )
        # maximum 5 items (+4 defaults +2 separators)
        if filemenu.GetMenuItemCount() > 10:
            filemenu.RemoveItem( filemenu.FindItemByPosition(8) )
            self.__recentContextPaths.pop()
        # insert
        # items before: open, save, save as, separator
        head, tail = os.path.split( path )
        wxid = wx.NewId()
        postition = 5 # New, Open, Save, Save As, separator
        filemenu.Insert(postition, wxid, tail, "Open '%s'" % path )
        self.__recentContextPaths.insert( 0, [wxid, path] )
        EVT_MENU(self, wxid, self.OnOpenRecent)
    
    def OnOpenRecent(self, event):
        """ Open recent context file. """
        if not self.__CheckSaveChanges(): return
        for pair in self.__recentContextPaths:
            if pair[0] == event.GetId():
                self.LoadContext( pair[1] )
                break
    
    def InitOtherGUIStuff(self):
        # debug log
        self.__logger.debug("method: InitOtherGUIStuff")

        self.LoadIcon()
        self.panelSelectProjects.SetScrollRate(25, 25)

        # connect close event
        self.frame.Bind(wx.EVT_CLOSE, self.OnExit, self.frame)
        
        #self.frame.GetSizer().Remove(xrc.XRCID(self.frame, "boxInstallFolder"))
        self.frame.Show()
        
        # progress bar
        self.__progressBar = None
        # progress start and range (in case of multiple actions)
        self.__progressStart = 0
        self.__progressRange = 100
        
    def Initialize(self):
        """ Initializes the application. """
        # debug log
        self.__logger.debug("method: Initialize")
        # possible command line options
        self.ParseCommandLine()
        # CSnake version
        self.__Report("CSnake version = %s" % csnBuild.version)
        # create the GUI handler 
        self.CreateGuiHandler()
        # initialize options
        self.InitializeOptions()
        # initialize context
        self.InitialiseContext()
        # initialize default option paths
        self.InitializePaths()

        # Update GUI (last one to call)
        self.UpdateGUI()
        self.frame.Fit()
        # debug log
        self.__logger.debug("end method: Initialize")
        
    def __Warn(self, message):
        """ Shows a warning message to the user. """
        self.__logger.warn("csnGUI.warn: %s" % message)
        if message is None: return
        dlg = wx.MessageDialog(self.frame, message, 'Warning', style = wx.OK | wx.ICON_EXCLAMATION)
        dlg.ShowModal()
        
    def Error(self, message):
        """ Shows an error message to the user. """
        self.__logger.error("csnGUI.error: %s" % message)
        if message is None: return
        dlg = wx.MessageDialog(self.frame, message, 'Error', style = wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()

    def __Report(self, message):
        """ Shows an report message to the user. """
        self.__logger.info("csnGUI.report: %s" % message)
        if message is None: return
        self.textLog.WriteText(message + "\n")

    def AddLogSeparator(self):
        self.textLog.WriteText("\n")
    
    def SetStatus(self, message):
        self.statusBar.SetFields([message])
        
    def __SetContextFilename(self, filename):
        self.contextFilename = filename
        # also save it in the options
        self.options.SetContextFilename(filename)
        self.SaveOptions()
        # update the frame title
        self.frame.SetTitle("CSnake GUI - %s" % self.contextFilename)

    def __GetContextFilename(self):
        return self.contextFilename
    
    def SetContextModified(self, modified):
        # check if new context is different from the original one
        if self.originalContextData != None:
            equal = self.context.GetData().Equal(self.originalContextData)
            self.contextModified = modified and not equal
        else:
            self.contextModified = modified
        # update the frame title
        oldTitle = self.frame.GetTitle()
        if self.contextModified:
            self.frame.SetTitle("CSnake GUI - %s *" % self.contextFilename)
        else:
            self.frame.SetTitle("CSnake GUI - %s" % self.contextFilename)
        # update project update flag
        if modified:
            self.projectNeedUpdate = True
            self.EnableConfigBar(True)      
        
    def IsContextModified(self):
        return self.contextModified
    
    def DoProjectNeedUpdate(self):
        return self.projectNeedUpdate
    
    def LoadIcon(self):
        iconFile = csnUtility.GetRootOfCSnake() + "/resources/Laticauda_colubrina.ico"
        icon1 = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.frame.SetIcon(icon1)
    
    def ParseCommandLine(self):
        parser = OptionParser()
        parser.add_option("-c", "--console", dest="console", default=False, help="print all messages to the console window")
        (self.commandLineOptions, self.commandLineArgs) = parser.parse_args()
        # if the csnake folder does not exist use the folder where it is run
        self.thisFolder = "%s" % (os.path.dirname(sys.argv[0]))
        self.thisFolder = self.thisFolder.replace("\\", "/")
        if self.thisFolder == "":
            self.thisFolder = "."
        if not os.path.isdir(self.csnakeFolder):
            self.csnakeFolder = self.thisFolder
    
    def CreateGuiHandler(self):
        # debug log
        self.__logger.debug("method: CreateGuiHandler")
        self.__guiHandler = csnGUIHandler.Handler()
        self.__guiHandler.AddListener(self.progressListener)
        self.context = None
    
    def InitializePaths(self):
        """ Initialize the options paths. """
        # debug log
        self.__logger.debug("method: InitializePaths")
        
        # found flags
        foundCmake = False
        foundPython = False
        foundIde = False
        # original paths
        cmakePath = self.context.GetCmakePath()
        pythonPath = self.context.GetPythonPath()
        idePath = self.context.GetIdePath()
        # find cmake if not specified
        if not os.path.isfile(cmakePath):
            cmakePath = csnUtility.GetDefaultCMakePath()
            if cmakePath:
                foundCmake = True
            else:
                self.__logger.info("Could not find default CMake.")
        # find python if not specified
        if not os.path.isfile(pythonPath):
            pythonPath = csnUtility.GetDefaultPythonPath()
            if pythonPath:
                foundPython = True
            else:
                self.__logger.info("Could not find default Python.")
        # find visual studio if not specified
        if csnUtility.IsWindowsPlatform() and \
            self.context.GetCompilername().find("Visual Studio") != -1 and \
            not os.path.isfile(idePath):
            idePath = csnUtility.GetDefaultVisualStudioPath(self.context.GetCompilername())
            if idePath:
                foundIde = True
            else:
                self.__logger.info("Could not find default Visual Studio.")
        # mention it to the user
        if foundCmake or foundPython or foundIde:
            message = "CSnake found/corrected setting paths. Do you want to use them?"
            if( foundCmake ):
                message += "\n- CMake: %s" % cmakePath
            if( foundPython ):
                message += "\n- Python: %s" % pythonPath
            if( foundIde ):
                message += "\n- Ide: %s" % idePath
            dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                if( foundCmake ):
                    self.__logger.info("Using cmake: %s" % cmakePath)
                    self.context.SetCmakePath(cmakePath)
                if( foundPython ):
                    self.__logger.info("Using python: %s" % pythonPath)
                    self.context.SetPythonPath(pythonPath)
                if( foundIde ):
                    self.__logger.info("Using ide: %s" % idePath)
                    self.context.SetIdePath(idePath)
            else:
                self.__logger.info("Not using found paths.")
    
    def InitializeOptions(self):
        """ Initialize GUI options. """
        # debug log
        self.__logger.debug("method: InitializeOptions")
        # create object
        self.options = csnGUIOptions.Options()
        self.binder.SetBuddyClass("options", self.options)
        
        # find the file
        optionsInCSnake = "%s/options" % self.csnakeFolder
        optionsInThis = "%s/options" % self.thisFolder
        # options are in the thisFolder, copy them to the csnakeFolder
        if not os.path.isfile(optionsInCSnake) and os.path.isfile(optionsInThis):
            self.__logger.debug("Found options in CSnake folder, copying it to .csnake.")
            shutil.copy(optionsInThis, optionsInCSnake)
        
        # save the file name
        self.optionsFilename = optionsInCSnake
        self.__logger.debug("options file: %s" % self.optionsFilename)
        
        # load it if present
        if os.path.isfile(optionsInCSnake):
            try:
                self.__logger.debug("Loading options.")
                self.options.Load(self.optionsFilename)
            except IOError, error:
                self.Error("%s" % error)
                # save a clean one
                self.options.Save(self.optionsFilename)
            # initialise display of recent paths
            self.InitRecentContextPathsDisplay()
        else:
            self.__logger.debug("No options found, using default.")
            self.SaveOptions()
            
    def InitialiseContext(self):
        """ Initialise the context. """
        # debug log
        self.__logger.debug("method: InitialiseContext")

        # find the context file name
        filename = None
        # previously used context
        fname = self.options.GetContextFilename()
        if fname and fname != "":
            filename = fname
        # if on command line, override option file
        if len(self.commandLineArgs) >= 1:
            filename = self.commandLineArgs[0]

        # load the file
        if filename:
            self.LoadContext(filename)
        
        # if not loaded, use a default one
        if not self.context:
            self.__logger.debug("Using default context.")
            context = csnContext.Context()
            self.__guiHandler.SetContext(context)
            self.__SetContext(context)
        
    def CopyGUIToContextAndOptions(self):
        """ Copy all GUI fields to the current context """
        self.binder.UpdateBuddies()
        
    def SaveContextAs(self):
        dlg = wx.FileDialog(None, "Save As...", defaultDir = os.path.dirname(self.options.GetContextFilename()), wildcard = "*.CSnakeGUI", style = wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            # Add default extension if not present
            (root, ext) = os.path.splitext(dlg.GetPath())
            if ext == ".CSnakeGUI":
                contextFilename = dlg.GetPath()
            else:
                contextFilename = "%s.CSnakeGUI" % root
            # save old filename
            if self.contextFilename:
                self.__AddRecentContextPath(self.contextFilename)
            # Save the context
            self.SaveContext(contextFilename)
            # the context was properly saved
            return True
        else:
            # the context was not saved
            return False
    
    def SaveContext(self, contextFilename):
        """ Save the current context. """
        # debug log
        self.__logger.debug("method: SaveContext: %s" % contextFilename)

        # Get content from frame
        self.CopyGUIToContextAndOptions()
        
        # Try to save
        saved = False
        try:
            self.__logger.debug("Saving context.")
            self.context.Save(contextFilename)
            saved = True
        except:
            self.Error("Sorry, CSnakeGUI could not save the context to %s\n. Please check if another program is locking this file.\n" % contextFilename)
        
        if saved:
            # Update name and flag    
            self.__SetContextFilename(contextFilename)
            # reset data for check changes
            self.originalContextData = copy.deepcopy(self.context.GetData())
            # reset modified flag
            self.SetContextModified(False)
    
    def SaveOptions(self):
        try:
            self.options.Save(self.optionsFilename)
        except:
            self.Error("Sorry, CSnakeGUI could not save the options to %s\n. Please check if another program is locking this file.\n" % self.optionsFilename)
    
    def OnDetectRootFolders(self, event):
        # check situation
        if not self.__CheckCSnakeFile():
            return
        # detect
        additionalRootFolders = self.__guiHandler.FindAdditionalRootFolders()
        self.context.ExtendRootFolders(additionalRootFolders)
        self.UpdateGUI()
    
    def FindAdditionalRootFolders(self, onlyForNewInstance=False):
        if onlyForNewInstance and self.context.IsCSnakeFileInRecentlyUsed():
            return
        
        additionalRootFolders = self.__guiHandler.FindAdditionalRootFolders()
        if len(additionalRootFolders):
            message =  "CSnakeGUI found additional root folders which are likely to be necessary for target %s.\n" % self.context.GetInstance()
            message += "Should CSnakeGUI add the following root folders?\n\n"
            for folder in additionalRootFolders:
                message += folder + "\n"
            message += "\n\nThis question will not appear again for this target, but you can later add the above root folders\nusing the Detect button\n"
                
            dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.context.ExtendRootFolders(additionalRootFolders)
                self.UpdateGUI()
            
    def OnConfigureALL(self, event):
        # check situation
        if not self.__CheckCSnakeFile() \
            or not self.__CheckThirdPartyFolders() \
            or not self.__CheckRootFolders() \
            or not self.__CheckBuildFolder():
            return
        # run the actions
        self.__runningConfigureAll = True
        actions = [
           self.ActionConfigureThirdPartyFolders,
           self.ActionBuildThirdParty,
           self.ActionCreateCMakeFilesAndRunCMake,
           self.ActionBuildProject,
           self.ActionInstallFilesToBuildFolder]
        self.DoActions(actions)
        self.__runningConfigureAll = False
        
    def OnUpdateListOfTargets(self, event): # wxGlade: CSnakeGUIFrame.<event_handler>
        # check situation
        if not self.__CheckCSnakeFile():
            return
        # run the action
        if self.DoActions([self.ActionUpdateListOfTargets]):
            self.UpdateGUI()
            self.EnableConfigBar(True)

    def OnCreateCMakeFilesAndRunCMake(self, event):
        # check situation
        if not self.__CheckCSnakeFile() \
            or not self.__CheckRootFolders() \
            or not self.__CheckBuildFolder():
            return
        # run the action
        if self.DoActions([self.ActionCreateCMakeFilesAndRunCMake]):
            xrc.XRCCTRL(self.panelContext, "btnLaunchIDE").SetFocus()
        
    def OnConfigureThirdPartyFolder(self, event):
        # check situation
        if not self.__CheckCSnakeFile() or not self.__CheckThirdPartyFolders():
            return
        # run the action
        if self.DoActions([self.ActionConfigureThirdPartyFolders]):
            xrc.XRCCTRL(self.panelContext, "btnInstallFilesToBuildFolder").SetFocus()
        
    def OnInstallFilesToBuildFolder(self, event):
        # check situation
        if not self.__CheckCSnakeFile() \
            or not self.__CheckRootFolders() \
            or not self.__CheckBuildFolder():
            return
        # run the action
        if self.DoActions([self.ActionInstallFilesToBuildFolder]):
            xrc.XRCCTRL(self.panelContext, "btnCreateCMakeFilesAndRunCMake").SetFocus()

    def ActionUpdateListOfTargets(self, args):
        oldInstance = self.context.GetInstance()
        self.listOfPossibleTargets = self.__guiHandler.GetListOfPossibleTargets()
        if len(self.listOfPossibleTargets):
            if self.listOfPossibleTargets.count(oldInstance) == 0:
                self.context.SetInstance(self.listOfPossibleTargets[0])
            return True
        return False

    def ActionCreateCMakeFilesAndRunCMake(self, args):
        self.FindAdditionalRootFolders(True)
        if self.__guiHandler.ConfigureProjectToBuildFolder(_alsoRunCMake = True, _askUser=AskUser(self.frame)):
            self.__currentSolutionPath = self.__guiHandler.GetTargetSolutionPath()
            if self.options.GetAskToLaunchIDE() and not self.__runningConfigureAll:
                self.AskToLaunchIDE(self.__currentSolutionPath)
            return True
        return False
        
    def ActionOnlyCreateCMakeFiles(self, args):
        self.FindAdditionalRootFolders(True)
        return self.__guiHandler.ConfigureProjectToBuildFolder(_alsoRunCMake = False, _askUser=AskUser(self.frame))
        
    def ActionConfigureThirdPartyFolders(self, args):
        if self.__guiHandler.ConfigureThirdPartyFolders():
            self.__currentSolutionPath = self.__guiHandler.GetThirdPartySolutionPaths()[0]
            if self.options.GetAskToLaunchIDE() and not self.__runningConfigureAll:
                self.AskToLaunchIDE(self.__currentSolutionPath)
            return True
        return False
        
    def ActionConfigureThirdPartyFolder(self, args):
        source = args[0]
        build = args[1]
        allBuildFolders = args[2]
        if self.__guiHandler.ConfigureThirdPartyFolder( source, build, allBuildFolders ):
            return True
        return False
        
    def ActionBuildThirdParty(self, args):
        return self.__guiHandler.BuildMultiple(self.__guiHandler.GetThirdPartySolutionPaths(), self.context.GetConfigurationName(), True)
        
    def ActionBuildProject(self, args):
        return self.__guiHandler.Build(self.__guiHandler.GetTargetSolutionPath(), self.context.GetConfigurationName(), False)
        
    def ActionInstallFilesToBuildFolder(self, args):
        self.FindAdditionalRootFolders(True)
        return self.__guiHandler.InstallBinariesToBuildFolder()
            
    def DoActions(self, actions, *args):
        self.SetStatus("Processing...")
        
        self.AddLogSeparator()
        self.__Report("Working, patience please...")
        
        startTime = time.time()
        
        # progress bar
        # The initial message seems to fix the window size...
        self.__progressBar = wx.ProgressDialog("Running...", "Running actions from a list of actions.", parent=self.frame, style=wx.PD_CAN_ABORT|wx.PD_AUTO_HIDE|wx.PD_APP_MODAL)

        res = True
        nActions = len(actions)
        count = 0
        range = 100 / nActions
        for action in actions:
            # progress
            start = count*range
            self.SetProgressStartAndRange(start, range)
            # remove the first 'Action'
            actionStr = action.__name__[6:]
            # split at upper case
            actionStr = re.sub(r'([a-z]*)([A-Z])',r'\1 \2',actionStr).strip()
            self.__Report("Action: %s." % actionStr)
            self.ProgressChanged(ProgressEvent(self,start,actionStr))
            try:
                res = res and action(args)
                count += 1
            except Exception, error:
                message = "Stopped, exception in process.\n%s" % str(error)
                # to keep the message alive after the error windows is closed.
                self.__Report(traceback.format_exc())
                # show as error
                self.Error(message)
                break
            # check cancel
            self.ProgressChanged(ProgressEvent(self, range))
            if self.__HasUserCanceled():
                self.__ResetUserCancel()
                self.__Report("Stopped, user canceled.")
                break
            # check the process' result
            if not res:
                message = "Stopped, error in process." 
                error = self.__guiHandler.GetErrorMessage()
                if error and error != "":
                    message = "%s\n%s" % (message, error)
                # to keep the message alive after the error windows is closed.
                self.__Report(message)
                # show as error
                self.Error(message)
                break
            
        elapsedTime = time.time() - startTime
        minutes = int(elapsedTime) / 60
        seconds = elapsedTime - 60*minutes
        message = "Done ("
        if minutes != 0:
            message += "%dmn" % minutes
        if minutes != 0 and seconds != 0:
            message += " "
        if seconds != 0:
            message += "%.2fs" % seconds
        message += ")."
        self.__Report(message)
        
        self.UpdateGUI()
        self.SetStatus("")
        
        # reset start and range and send 100% (closes the progress bar)
        self.SetProgressStartAndRange(0, 100)
        self.ProgressChanged(ProgressEvent(self,100,"Done"))
        
        return res
        
    def Restart(self):
        """ Restart the application """
        arglist = []
        if( os.path.splitext(os.path.basename(sys.executable))[0].lower() == "python" ):
            arglist = [sys.executable]
            arglist.extend(sys.argv)
        os.execv(sys.executable, arglist)
                
    def OnSelectCSnakeFile(self, event): # wxGlade: CSnakeGUIFrame.<event_handler>
        """
        Select file containing the project that should be configured.
        """
        # Set path of that file that was selected before
        oldValue = self.context.GetCsnakeFile()
        if oldValue.find("/") == -1:
            oldPath = ""
        else:
            oldPathAndFilenameSplit = oldValue.rsplit("/", 1)
            oldPath = oldPathAndFilenameSplit[0] + "/"
            oldValue = oldPathAndFilenameSplit[1]

        dlg = wx.FileDialog(None, "Select CSnake file", wildcard = "Python source files (*.py)|*.py",defaultDir = oldPath, defaultFile = oldValue)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.context.SetCsnakeFile(dlg.GetPath())
            self.OnUpdateListOfTargets(event)
            self.UpdateGUI()

    def SetBuildFolder(self, folder):
        self.context.SetBuildFolder(folder)
        
    def GetBuildFolder(self):
        return self.context.GetBuildFolder()
        
    def AddRootFolder(self, folder): # wxGlade: CSnakeGUIFrame.<event_handler>
        """
        Add folder where CSnake files must be searched to context rootFolders.
        """
        try:
            self.context.AddRootFolder( folder )
            
            # Automatically find thirdparty folder
            defaultThirdPartyFolders = csnUtility.SearchSubFolder2Levels( folder, 'src', 'tp' )
            
            for defaultThirdPartyFolder in defaultThirdPartyFolders:
                if os.path.isdir( defaultThirdPartyFolder ):
                    message = "Found thirdparty folder: %s. Do you want to add it?" % defaultThirdPartyFolder
                    dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
                    if dlg.ShowModal() == wx.ID_YES:
                        self.AddThirdPartyFolder( defaultThirdPartyFolder )
        except Exception, error:
            self.Error(str(error))
    
    def GetLastRootFolder(self):
        if self.context.GetNumberOfRootFolders() > 0:
            return self.context.GetRootFolder(self.context.GetNumberOfRootFolders()-1)
        else:
            return ""

    def OnRemoveRootFolder(self, event): # wxGlade: CSnakeGUIFrame.<event_handler>
        """
        Remove folder where CSnake files must be searched from context rootFolders.
        """
        folder = self.lbxRootFolders.GetStringSelection()
        # check if correct selection
        if folder == None or folder == "":
            message = "Please select at least one folder."
            self.__Warn(message)
        else:
            # remove
            self.context.RemoveRootFolder(folder)
            self.UpdateGUI()

    def AddThirdPartyFolder(self, folder): # wxGlade: CSnakeGUIFrame.<event_handler>
        """
        Add folder where CSnake files must be searched to context.thirdPartyFolders.
        Example:
		Thirdparty source folder: K:/Code/src/lb1/srclb/tp
		Thirdparty build folder: K:/Code/bin/b1_vs11_64e/tp_lb
        """
        projectNameAr = folder.split('/')
        projectNameAr.reverse()
        projectName = projectNameAr[1].split('src')[1]
        rootBuildFolder = self.context.GetBuildFolder() + "/tp_"+ projectName
        newBuildFolder = rootBuildFolder
        alreadyUsed = True
        index = 0
        while alreadyUsed:
            alreadyUsed = False
            if index > 0: newBuildFolder = rootBuildFolder + ("%d" % index)
            for listedFolder in self.context.GetThirdPartyBuildFolders():
                if newBuildFolder == listedFolder:
                    alreadyUsed = True
                    break
            index = index + 1
        message = "Do you want to use \"%s\" as Build Folder for Third Party folder \"%s\"?" % (newBuildFolder, folder)
        dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.context.AddThirdPartySrcAndBuildFolder(folder, newBuildFolder)
        else:
            self.context.AddThirdPartySrcAndBuildFolder(folder, "")

    def OnThirdPartySrcAndBuildFolderSelectCell(self, event):
        self.gridThirdPartySrcAndBuildFolders.SelectRow(event.GetRow())
        event.Skip()
    
    def ThirdPartySrcAndBuildFolderGetSelectedRows(self):
        selection = self.gridThirdPartySrcAndBuildFolders.GetSelectedRows()
        return selection

    def OnAddThirdPartySrcAndBuildFolder(self, event):
        self.context.AddThirdPartySrcAndBuildFolder("", "")
        self.UpdateGUI()
        self.gridThirdPartySrcAndBuildFolders.ClearSelection()
        newRow = self.gridThirdPartySrcAndBuildFolders.GetTable().GetNumberRows()-1
        self.gridThirdPartySrcAndBuildFolders.SelectRow(newRow, True)
        self.gridThirdPartySrcAndBuildFolders.SetGridCursor(newRow, 0)
        self.gridThirdPartySrcAndBuildFolders.SetFocus()

    def OnRemoveThirdPartySrcAndBuildFolder(self, event):
        selection = self.ThirdPartySrcAndBuildFolderGetSelectedRows()
        if (len(selection) == 0):
            message = "Please select at least one row. You can click on the row index to select a row."
            self.__Warn(message)
        else:
            for i in range(len(selection)):
                self.context.RemoveThirdPartySrcAndBuildFolderByIndex(selection[i])
                for j in range(i+1, len(selection)):
                    if selection[j] > selection[i]:
                        selection[j] = selection[j] - 1
            self.UpdateGUI()
            self.gridThirdPartySrcAndBuildFolders.ClearSelection()
            
        self.gridThirdPartySrcAndBuildFolders.SetFocus()
        
    def OnConfigureThirdPartySrcAndBuildFolder(self, event):
        selection = sorted(self.ThirdPartySrcAndBuildFolderGetSelectedRows())
        if (len(selection) == 0):
            message = "Please select at least one row. You can click on the row index to select a row."
            self.__Warn(message)
            self.gridThirdPartySrcAndBuildFolders.SetFocus()
        else:
            self.gridThirdPartySrcAndBuildFolders.SetFocus()
            for row in selection:
                source = self.context.GetThirdPartyFolder(row)
                build = self.context.GetThirdPartyBuildFolderByIndex(row)
                # check situation
                if not self.__CheckCSnakeFile() \
                    or not self.__CheckThirdPartySrcFolder(source) \
                    or not self.__CheckThirdPartyBuildFolder(build):
                    return
                # run the action
                self.DoActions([self.ActionConfigureThirdPartyFolder], source, build, self.context.GetThirdPartyBuildFoldersComplete())
        
    def OnMoveUpThirdPartySrcAndBuildFolder(self, event):
        selection = sorted(self.ThirdPartySrcAndBuildFolderGetSelectedRows())
        if (len(selection) == 0):
            message = "Please select at least one row. You can click on the row index to select a row."
            self.__Warn(message)
        else:
            newSelection = []
            boundaryIndex = 0
            for index in selection:
                if index > boundaryIndex:
                    self.context.MoveUpThirdPartySrcAndBuildFolder(index)
                    newSelection.append(index-1)
                else:
                    boundaryIndex = index + 1
                    newSelection.append(index)
            self.UpdateGUI()
            self.gridThirdPartySrcAndBuildFolders.ClearSelection()
            first = True
            for row in newSelection:
                self.gridThirdPartySrcAndBuildFolders.SelectRow(row, True)
                if first:
                    self.gridThirdPartySrcAndBuildFolders.SetGridCursor(row, 0)
                    first = False
                    
        self.gridThirdPartySrcAndBuildFolders.SetFocus()
        
    def OnMoveDownThirdPartySrcAndBuildFolder(self, event):
        selection = sorted(self.ThirdPartySrcAndBuildFolderGetSelectedRows(), reverse = True)
        if (len(selection) == 0):
            message = "Please select at least one row. You can click on the row index to select a row."
            self.__Warn(message)
        else:
            newSelection = []
            boundaryIndex = self.context.GetNumberOfThirdPartyFolders() - 1
            for index in selection:
                if index < boundaryIndex:
                    self.context.MoveDownThirdPartySrcAndBuildFolder(index)
                    newSelection.append(index+1)
                else:
                    boundaryIndex = index - 1
                    newSelection.append(index)
            self.UpdateGUI()
            self.gridThirdPartySrcAndBuildFolders.ClearSelection()
            first = True
            for row in newSelection:
                self.gridThirdPartySrcAndBuildFolders.SelectRow(row, True)
                if first:
                    self.gridThirdPartySrcAndBuildFolders.SetGridCursor(row, 0)
                    first = False
            
        self.gridThirdPartySrcAndBuildFolders.SetFocus()
        
    def OnContextNew(self, event):
        """ Open a New empty context. """
        # save context if modified
        self.__CheckSaveChanges()
        # create an empty context
        context = csnContext.Context()
        # load it
        self.__guiHandler.SetContext(context)
        self.__SetContext(context)
        # update the GUI
        self.UpdateGUI()
        # initialise the paths
        self.InitializePaths()
        # update the GUI
        self.UpdateGUI()

    def OnContextOpen(self, event):
        """
        Let the user load a context.
        """
        if not self.__CheckSaveChanges(): return
        dlg = wx.FileDialog(None, "Select CSnake context file", defaultDir = os.path.dirname(self.options.GetContextFilename()), wildcard = "Context Files (*.CSnakeGUI;*.csnakecontext)|*.CSnakeGUI;*.csnakecontext|All Files (*.*)|*.*")
        if dlg.ShowModal() == wx.ID_OK:
            self.UpdateGUI()
            self.LoadContext(dlg.GetPath())

    def OnContextSave(self, event):
        """ Save the context to the current file. """
        # check if the file name is correct
        if self.contextFilename == None or self.contextFilename == "" or not os.path.exists(self.contextFilename):
            self.SaveContextAs()
        else:
            self.SaveContext(self.contextFilename)

    def OnContextSaveAs(self, event):
        """ Let the user save the context to a specific file. """
        self.SaveContextAs()

    def GetCompilerComboBoxItems(self):
        result = []
        result.append("")
        if csnUtility.IsWindowsPlatform():
            result.append("Visual Studio 7 .NET 2003")
            result.append("Visual Studio 8 2005")
            result.append("Visual Studio 8 2005 Win64")
            result.append("Visual Studio 9 2008")
            result.append("Visual Studio 9 2008 Win64")
            result.append("Visual Studio 10")
            result.append("Visual Studio 10 Win64")
            result.append("Visual Studio 11")
            result.append("Visual Studio 11 Win64")
            result.append("Visual Studio 12")
            result.append("Visual Studio 12 Win64")
            result.append("Visual Studio 15")
            result.append("Visual Studio 15 Win64")
            result.append("NMake Makefiles")
        result.append("KDevelop3")
        result.append("Unix Makefiles")
        result.append("Eclipse CDT4 - Unix Makefiles")
        return result
        
    def GetBuildTypeComboBoxItems(self):
        list = [""]
        if self.context.GetCompiler()!= None:
            list = self.context.GetCompiler().GetAllowedConfigurations()
        return list
    
    def GetCSnakeFileComboBoxItems(self):
        result = list()
        count = 0
        for x in self.context.GetRecentlyUsed():
            result.append("%s - In %s" % (x.GetInstance(), x.GetCsnakeFile()))
            count += 1
            if count >= 10:
                break
        return result
    
    def UpdateGUI(self):
        """ Refreshes the GUI based on the current context. Also saves the current context to the context filename """
        # refresh context
        self.binder.UpdateControls()
        self.frame.Layout()
        self.frame.Update()
        wx.CallAfter(self.frame.Update)
    
    def LoadContext(self, contextFilename):
        """ Load configuration context from context filename.  """
        # debug log
        self.__logger.debug("method: LoadContext: %s" % contextFilename)
        
        # Default context
        context = None
        # Check if the file name is specified
        if contextFilename != None and contextFilename != "":
            # Check if the file exists
            if os.path.exists(contextFilename):
                # Load the context (has to be done through the __guiHandler)
                try:
                    context = self.__guiHandler.LoadContext(contextFilename)
                except IOError, error:
                    self.Error("Could not load the context file: '%s'." % error)
            else:
                self.Error("Could not find context file: '%s'." % contextFilename)
        
        if context:
            # Save the context
            self.__SetContext(context)
            # save old filename
            if self.contextFilename:
                self.__AddRecentContextPath(self.contextFilename)
            # save file name
            self.__SetContextFilename(contextFilename)
            # log success
            self.__logger.debug("Loaded context.")
            # Update 
            self.EnableConfigBar(True)
            self.UpdateGUI()
        else:
            # log warning
            self.__logger.debug("Could not load context.")

    def __SetContext(self, context):
        self.context = context
        # Save a copy to check changes
        data = self.context.GetData()
        self.originalContextData = copy.deepcopy( data )
        # Add a change listener
        self.context.AddListener(self.changeListener)
        # Force the refresh of the project list
        self.projectNeedUpdate = True
        if self.noteBook.GetPageText(self.noteBook.GetSelection()) == "Select Projects":
            self.DoActions([self.ActionSelectProjects])
        # Set as buddy class for GUI
        self.binder.SetBuddyClass("context", self.context)
        
    def GetInstanceComboBoxItems(self):
        return self.listOfPossibleTargets
            
    def AskToLaunchIDE(self, pathToSolution):
        message = "Launch Visual Studio with solution %s?" % pathToSolution
        dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.__LaunchIDE(pathToSolution)

    def OnLaunchIDE(self, event = None):
        self.__LaunchIDE(self.__currentSolutionPath)
            
    def __LaunchIDE(self, pathToSolution):
        ''' Launch the IDE with the input path.'''
        if pathToSolution and os.path.exists(pathToSolution):
            argList = [self.context.GetIdePath(), pathToSolution]
            subprocess.Popen(argList)
        else:
            self.Error("Cannot open IDE, solution does not exist: %s" % pathToSolution)
    
    def __CheckSaveChanges(self):
        """ Check if changes need to be saved. Return false if canceled. """
        self.CopyGUIToContextAndOptions()
        if self.IsContextModified():
            message = "Save changes before closing?"
            dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.CANCEL)
            ret = dlg.ShowModal()
            if ret == wx.ID_YES:
                if self.contextFilename == None or not os.path.isfile(self.contextFilename):
                    self.SaveContextAs()
                else:
                    self.SaveContext(self.contextFilename)
            elif ret == wx.ID_NO:
                self.SetContextModified(False)
            elif ret == wx.ID_CANCEL:
                return False
        # default
        return True
    
    def OnExit(self, event = None):
        if not self.destroyed:
            if not self.__CheckSaveChanges(): return
            self.destroyed = True
            self.frame.Destroy()

    def OnHelp(self, event = None):
        ''' Text displayed for help.'''
        indexFilename = csnUtility.GetRootOfCSnake() + "/doc/html/index.html"
        if os.path.exists(indexFilename):
            webbrowser.open(indexFilename)
        else:
            self.Error("Missing documentation.")
                                        
    def OnAbout(self, event = None):
        ''' Text displayed in the About box.'''
        about = About()
        about.read(csnUtility.GetRootOfCSnake() + "/resources/about.txt")
        info = wx.AboutDialogInfo()
        info.SetName(about.getName())
        info.SetVersion(about.getVersion())
        info.SetDescription(about.getDescription())
        info.SetCopyright(about.getAuthor())
        wx.AboutBox(info)
        
    def OnSelectRecentlyUsed(self, event): # wxGlade: CSnakeGUIFrame.<event_handler>
        # get the context from the list
        context = self.context.GetRecentlyUsed()[event.GetSelection()]
        # update context properties
        self.context.SetCsnakeFile(context.GetCsnakeFile())
        # do an update of the targets
        self.OnUpdateListOfTargets(event)
        # force the instance
        self.context.SetInstance(context.GetInstance())
        # update frame
        self.UpdateGUI()

    def OnSetCMakePath(self, event): # wxGlade: CSnakeOptionsFrame.<event_handler>
        """
        Let the user select where CSnake is located.
        """
        dlg = wx.FileDialog(None, "Select path to CMake")
        if dlg.ShowModal() == wx.ID_OK:
            self.context.SetCmakePath(dlg.GetPath())
            self.UpdateGUI()

    def OnSetPythonPath(self, event): # wxGlade: CSnakeOptionsFrame.<event_handler>
        dlg = wx.FileDialog(None, "Select path to Python")
        if dlg.ShowModal() == wx.ID_OK:
            self.context.SetPythonPath(dlg.GetPath())
            self.UpdateGUI()

    def OnSetVisualStudioPath(self, event): # wxGlade: CSnakeOptionsFrame.<event_handler>
        dlg = wx.FileDialog(None, "Select path to Visual Studio")
        if dlg.ShowModal() == wx.ID_OK:
            self.context.SetIdePath(dlg.GetPath())
            self.UpdateGUI()

    def __GetCategories(self,forceRefresh = False):
        try:
            categories = self.__guiHandler.GetCategories(forceRefresh)
        except Exception, error:
            # show error message
            message = "Could not load project dependencies."
            message = message + "\nPlease check the fields 'CSnake File' and/or 'Instance'"
            message = message + ("\nMessage: '%s'" % error)
            raise RuntimeError(message)
        return categories
    
    def ActionSelectProjects(self, args):
        # do not go further if there is no csnake file or instance
        if not self.__CheckCSnakeFile() or not self.context.GetInstance():
            return
        
        # get list of ALL the categories on which the user can filter
        self.SetStatus("Retrieving projects...")
        
        if not self.__projectTreeIsDrawn or self.DoProjectNeedUpdate():
            # get the categories
            categories = self.__GetCategories(forceRefresh = False)
            # create/clean the panel
            self.panelSelectProjects.GetSizer().Clear()
            if self.__projectTree:
                self.__projectTree.Destroy()
            self.__projectTreeItems = dict()
            self.__projectTreeDependencyCache = dict()
            
            # create tree
            wxVersion = [int(number) for number in wx.__version__.split('.')]
            if wxVersion < [2, 8, 11]:
                self.__projectTree = ct.CustomTreeCtrl(self.panelSelectProjects,
                    style = wx.TR_HAS_BUTTONS | wx.TR_HAS_VARIABLE_ROW_HEIGHT | 
                        wx.TR_SINGLE)
            else:
                self.__projectTree = ct.CustomTreeCtrl(self.panelSelectProjects,
                    style = wx.TR_HAS_BUTTONS | wx.TR_HAS_VARIABLE_ROW_HEIGHT | 
                        wx.TR_SINGLE, 
                    agwStyle = wx.TR_HIDE_ROOT | 
                        ct.TR_AUTO_CHECK_CHILD | ct.TR_AUTO_CHECK_PARENT)
                
            treeRoot = self.__projectTree.AddRoot('TreeRoot')
            
            dependencies = self.__guiHandler.GetProjectDependencies()
            mainProjectCategories = self.__guiHandler.GetInstanceCategories()
            if mainProjectCategories:
                mainProjectName = mainProjectCategories[0]
            else:
                mainProjectName = self.context.GetInstance()
            
            # loop through super categories
            for super in self.context.GetSubCategoriesOf().keys():
                # tree item
                superItem = self.__projectTree.AppendItem(treeRoot, super, ct_type=1)
                checkSuperItem = True
                for sub in self.context.GetSubCategoriesOf()[super]:
                    checkSuperItem = checkSuperItem and (not sub in self.context.GetFilter())
                superItem.Check(checkSuperItem)
                # if super, add children
                for category, project in categories.items():
                    if category in self.context.GetSubCategoriesOf()[super]:
                        self.__CreateProjectTreeItem(superItem, category, project, dependencies, mainProjectName, mainProjectCategories)
            
            # warn if differences between arrays
            for super in self.context.GetSubCategoriesOf().keys():
                for category in self.context.GetSubCategoriesOf()[super]:
                    if category not in categories:
                        self.__logger.warn("%s in context but not in project." % category)

            # warn if differences between arrays
            for category, project in categories.items():
                contains = False
                for super in self.context.GetSubCategoriesOf().keys():
                    if category in self.context.GetSubCategoriesOf()[super]:
                        contains = True
                if not contains:
                    self.__logger.warn("%s in project but not in context." % category)
                    self.__CreateProjectTreeItem(treeRoot, category, project, dependencies, mainProjectName, mainProjectCategories)
            
            # react when an item is checked (to update the filter and check dependencies)
            # Note: This has to be done *before* the dependency check, it relies on it.
            self.panelSelectProjects.Bind(ct.EVT_TREE_ITEM_CHECKED, self.OnProjectChecked)
            
            # make sure all dependencies are met at the beginning
            for category, project in categories.items():
                # For all active projects
                if not category in self.context.GetFilter():
                    # Activate all dependent projects
                    self.CheckUncheckDependentItems(category, True, self.__projectTreeDependencyCache)
            
            # display
            self.__projectTree.ExpandAll()
            self.panelSelectProjects.GetSizer().Add(self.__projectTree, 1, wx.EXPAND|wx.ALL, 3)
            self.panelSelectProjects.GetSizer().Add(self.btnForceRefreshProjects, 0, 0, 3)
            self.panelSelectProjects.Layout()
            self.panelSelectProjects.FitInside()

            # update flags
            self.__projectTreeIsDrawn = True
            self.projectNeedUpdate = False
            
        self.SetStatus("")
        return True
    
    def __CreateProjectTreeItem(self, superItem, category, project, dependencies, mainProjectName, mainProjectCategories):
        item = self.__projectTree.AppendItem(superItem, category, ct_type = 1, data = project)
        if mainProjectCategories and category in mainProjectCategories:
            # select and grey out the main project
            item.Enable(False)
            item.Check(True)
            self.UpdateContextFilter(category=category, filterOut=False, checkDependencies=False)
            item.SetText("%s (main project)" % category)
            item.SetBold(True)
        elif project in dependencies:
            # select and grey out all dependencies of the main project (deselecting them wouldn't have any effect anyway)
            item.Enable(False)
            item.Check(True)
            self.UpdateContextFilter(category=category, filterOut=False, checkDependencies=False)
            item.SetText("%s (dependency of %s)" % (category, mainProjectName))
        else:
            item.Check( not category in self.context.GetFilter() )
        self.__projectTreeItems[category] = item

        
    def OnProjectChecked(self, event):
        """ Respond to checking a category. """
        self.__OnProjectChecked(event.GetItem())
        
    def __OnProjectChecked(self, item):
        """ Respond to checking a category. """
        project = item.GetData()
        if project:
            # if item is enabled, then write the change to the filter
            if item.IsEnabled():
                for category in project.categories:
                    self.UpdateContextFilter(category, not item.IsChecked())
            # else: if item is disabled, then don't care about the change

        for childItem in item.GetChildren():
            self.__OnProjectChecked(childItem)
    
    def UpdateContextFilter(self, category, filterOut, checkDependencies=True):
        """ Update the context filter. """
        if filterOut and not self.context.HasFilter(category):
            self.context.AddFilter(category)
            if checkDependencies:
                self.CheckUncheckDependentItems(category, False, self.__projectTreeDependencyCache)
        elif not filterOut and self.context.HasFilter(category):
            self.context.RemoveFilter(category)
            if checkDependencies:
                self.CheckUncheckDependentItems(category, True, self.__projectTreeDependencyCache)
                
    def CheckUncheckDependentItems(self, category, selected, dependenciesCache):
        if category in self.__projectTreeItems:
            catTreeItem = self.__projectTreeItems[category]
        else:
            # Name not registered? Then probably the user clicked on a super-category => stop
            return
        catProject = catTreeItem.GetData()

        assert isinstance(catProject, csnProject.GenericProject)

        if selected:
            # Project "catProject" recently selected: Select all projects it depends on
            # Go through all projects that "catProjects" depends on
            for depProject in catProject.dependenciesManager.GetProjects(_recursive=True, _onlyRequiredProjects=True, _cache = dependenciesCache):
                # Get the category/-ies (~ "name") of depProject (can have several ones)
                for depProjectCategory in depProject.categories:
                    # Is there an item in the project-tree for this project?
                    if depProjectCategory in self.__projectTreeItems:
                        # Then select it
                        item = self.__projectTreeItems[depProjectCategory]
                        self.__projectTree.CheckItem(item, True)
        else:
            # Project "catProject" recently deselected: Deselect all projects that depend on it
            # Check all projects in the project-tree, if they depend on it
            for otherCategory, otherTreeItem in self.__projectTreeItems.items():
                otherProject = otherTreeItem.GetData()
                # Depends?
                if catProject in otherProject.dependenciesManager.GetProjects(_recursive=True, _onlyRequiredProjects=True, _cache = dependenciesCache):
                    # "project" depends on "catProject", so deselect it
                    item = self.__projectTreeItems[otherCategory]
                    self.__projectTree.CheckItem(item, False) # Uncheck it
    
    def OnSelectCompiler(self, event):
        self.context.FindCompiler()
        # find visual studio if needed
        if self.context.GetCompilername().startswith('Visual Studio'):
            idePath = csnUtility.GetDefaultVisualStudioPath(self.context.GetCompilername())
            # mention it to the user
            if idePath:
                if idePath != self.context.GetIdePath():
                    message = "CSnake found the corresponding Visual Studio in the registry. Use it?"
                    dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
                    if dlg.ShowModal() == wx.ID_YES:
                        self.context.SetIdePath(idePath)
            else:
                message = "CSnake could not find the corresponding Visual Studio in the registry."
                self.__Warn(message)
                self.context.SetIdePath("")
            
        # update the GUI
        self.UpdateGUI()
        
    def OnRefreshProjects(self, event):
        self.projectNeedUpdate = True
        self.DoActions([self.ActionSelectProjects])

    def GetLastThirdPartyFolder(self):
        return self.context.GetLastThirdPartyFolder( )

    def StateChanged(self, event):
        """ Called by the ChangeListener. """
        self.SetContextModified(True)
        
    def __CheckBuildFolder(self):
        """ Check that the build folder is valid. """
        # Build folder: get them from context (or GUI?)
        folder = self.context.GetBuildFolder()
        # 1. should exist
        if folder == None or not os.path.isdir(folder):
            # focus
            self.txtBuildFolder.SetInsertionPointEnd() # does not seem to work...
            self.txtBuildFolder.SetFocus()
            # message
            message = "The build folder '%s' does not exist, do you want to create it?" % folder
            dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                # also create intermediary folders
                os.makedirs(folder)
            else:
                return False
        # all good
        return True

    def __CheckRootFolders(self):
        """ Check that the root folder is valid. """
        # Root folders: get them from context (or GUI?)
        folders = self.context.GetRootFolders()
        # 1. should exist
        index = 0 # order in list follows order in grid, would be safer to use grid elements
        for folder in folders:
            if folder == None or not os.path.isdir(folder):
                # focus
                self.lbxRootFolders.SetSelection(index)
                self.lbxRootFolders.SetFocus()
                # message
                message = "The root folder '%s' does not exist, please provide a valid one." % folder
                self.Error(message)
                return False
            # increment
            index += 1
        # all good
        return True

    def __CheckCSnakeFile(self):
        """ Check that the csnake file is valid. """
        # CSnake file: get them from context (or GUI?)
        file = self.context.GetCsnakeFile()
        # 1. should exist
        if file == None or not os.path.isfile(file):
            # focus
            self.cmbCSnakeFile.SetFocus()
            # message
            message = "The CSnake file '%s' does not exist, please provide a valid one." % file
            self.Error(message)
            # exit
            return False
        # all good
        return True
    
    def __CheckThirdPartyFolders(self):
        """ Check that the third parties are valid. """
        # Source folders: get them from context (or GUI?)
        tpSrcFolders = self.context.GetThirdPartyFolders()
        index = 0 # order in list follows order in grid, would be safer to use grid elements
        for folder in tpSrcFolders:
            if not self.__CheckThirdPartySrcFolder(folder):
                # focus
                self.gridThirdPartySrcAndBuildFolders.SelectRow(index)
                self.gridThirdPartySrcAndBuildFolders.SetFocus()
                # exit
                return False
            # increment
            index += 1
        
        # Build folders: get them from context (or GUI?)
        tbBuildFolders = self.context.GetThirdPartyBuildFolders()
        index = 0 # order in list follows order in grid, would be safer to use grid elements
        for folder in tbBuildFolders:
            if not self.__CheckThirdPartyBuildFolder(folder):
                # focus
                self.gridThirdPartySrcAndBuildFolders.SelectRow(index)
                self.gridThirdPartySrcAndBuildFolders.SetGridCursor(index, 1)
                self.gridThirdPartySrcAndBuildFolders.SetFocus()
                # exit
                return False
            # increment
            index += 1
        
        # all good
        return True

    def __CheckThirdPartySrcFolder(self, folder):
        """ Check that the third party source folder is valid. """
        # Source folder:
        # 1. should exist
        if folder == None or not os.path.isdir(folder):
            # message
            message = "The third party source folder '%s' does not exist, please provide a valid one." % folder
            self.Error(message)
            # exit
            return False
        # 2. should contain a CMakeLists.txt file
        fileName = "CMakeLists.txt"
        file = "%s/%s" % (folder, fileName)
        if file == None or not os.path.isfile(file):
            # message
            message = "The third party source folder '%s' is not a valid one, it should contain a CMakeLists.txt file." % folder
            self.Error(message)
            # exit
            return False

        # all good
        return True
        
    def __CheckThirdPartyBuildFolder(self, folder):
        """ Check that the third party build folder is valid. """
        # Build folders:
        # 1. should exist
        if not os.path.exists(folder):
            # message
            message = "The third party build folder '%s' does not exist, do you want to create it?" % folder 
            # offer to create the folder
            dlg = wx.MessageDialog(self.frame, message, 'Question', style = wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                # also create intermediary folders
                os.makedirs(folder)
            else:
                # exit
                return False
        
        # all good
        return True
        
    def SetProgressStartAndRange(self, start, range):
        self.__progressRange = range
        self.__progressStart = start

    def ProgressChanged(self, event):
        """ Called by the ProgressListener. """
        if self.__progressBar and self.__progressBar.IsShown():
            progress = self.__progressStart + event.GetProgress()*self.__progressRange/100
            cont, skip = self.__progressBar.Update(progress, event.GetMessage())
            if not cont:
                self.__progressBar.Destroy()
                self.__guiHandler.Cancel()
                self.__cancelAction = True
        
    def __HasUserCanceled(self):
        return self.__cancelAction
    
    def __ResetUserCancel(self):
        self.__cancelAction = False 

if __name__ == "__main__":
    csnUtility.InitialiseLogging()
    
    logger = logging.getLogger("CSnake")
    logger.info("###########################################")
    logger.info("Starting program.")

    app = CSnakeGUIApp(0)
    app.MainLoop()
    
    logger.info("Ending program.")
