Option Explicit

Dim shell, fso, projectRoot, scriptPath, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectRoot = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fso.BuildPath(projectRoot, "scripts\start_deepscientist_silent.ps1")

If Not fso.FileExists(scriptPath) Then
    WScript.Echo "Missing silent launcher: " & scriptPath
    WScript.Quit 1
End If

command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """ -ProjectRoot """ & projectRoot & """ -SkipDoctor"
shell.Run command, 0, False

