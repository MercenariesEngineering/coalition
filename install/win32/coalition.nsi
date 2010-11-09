!include "Sections.nsh"


Icon "images\coalition.ico"
UninstallIcon "${NSISDIR}\contrib\graphics\icons\classic-uninstall.ico"

InstallDir $PROGRAMFILES\Coalition

Page components
Page directory

Page instfiles

Section "Common Files" 
SectionIn RO
	SetShellVarContext all

	ReadRegStr $R1 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "UninstallString"
	StrCmp $R1 "" UninstallMSI_nomsi
		IfSilent noUninstallWarning
			MessageBox MB_YESNOCANCEL|MB_ICONQUESTION  "A previous version of Coalition was found. It is recommended that you uninstall it first.$\n$\nDo you want to do that now?" IDNO UninstallMSI_nomsi IDYES UninstallMSI_yesmsi
				Quit
noUninstallWarning:
	UninstallMSI_yesmsi:
		ExecWait '$R1 /S _?=$INSTDIR'
	UninstallMSI_nomsi: 

	CreateDirectory "$INSTDIR"
	CreateDirectory "$SMPROGRAMS\Coalition"
	CreateDirectory "$APPDATA\Coalition"
	AccessControl::GrantOnFile "$APPDATA\Coalition" "(BU)" "FullAccess"

	ExecWait 'net stop CoalitionServer'

	; Write the registry
	WriteRegStr HKLM "Software\Mercenaries Engineering\Coalition" "Installdir" $INSTDIR
	WriteRegStr HKLM "Software\Mercenaries Engineering\Coalition" "Datadir" "$APPDATA\Coalition"

	; Write the uninstall keys for Windows
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "DisplayName" "Coalition"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "DisplayIcon" '"$INSTDIR\coalition.ico"'
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "UninstallString" '"$INSTDIR\uninstall.exe"'
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "NoModify" 1
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition" "NoRepair" 1

	; Set output path to the installation directory.
	WriteUninstaller "uninstall.exe"

	CreateShortCut "$SMPROGRAMS\Coalition\Configuration File.lnk" "$INSTDIR\coalition.ini" "" ""

	; Set output path to the installation directory.
__INSTALL_FILES__

	; Install msvc redist
	ExecWait '"$INSTDIR\vcredist_x86.exe /q"'
	Delete $INSTDIR\vcredist_x86.exe

SectionEnd

Section /o "Server (the master computer)" 
	SetShellVarContext all

	CreateShortCut "$SMPROGRAMS\Coalition\Coalition Server Monitor.lnk" "http://localhost:19211" "" "$INSTDIR\coalition.ico"
	CreateShortCut "$SMPROGRAMS\Coalition\Coalition Server Start.lnk" "net" "start CoalitionServer" "$INSTDIR\server_start.ico"
	CreateShortCut "$SMPROGRAMS\Coalition\Coalition Server Stop.lnk" "net" "stop CoalitionServer" "$INSTDIR\server_stop.ico"
	CreateShortCut "$SMPROGRAMS\Coalition\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe"
	CreateShortCut "$DESKTOP\Coalition Server Monitor.lnk" "http://localhost:19211" "" "$INSTDIR\coalition.ico"
	CreateShortCut "$DESKTOP\Coalition Server Start.lnk" "net" "start CoalitionServer" "$INSTDIR\server_start.ico"
	CreateShortCut "$DESKTOP\Coalition Server Stop.lnk" "net" "stop CoalitionServer" "$INSTDIR\server_stop.ico"

	ExecWait '"$INSTDIR\server" remove'
	ExecWait '"$INSTDIR\server" -install -auto'
	ExecWait 'net start CoalitionServer'
SectionEnd

Section "Worker (computers composing the farm)"
	SetShellVarContext all

	CreateShortCut "$SMPROGRAMS\Coalition\Coalition Worker Start.lnk" "net" "start CoalitionWorker" "$INSTDIR\worker_start.ico"
	CreateShortCut "$SMPROGRAMS\Coalition\Coalition Worker Stop.lnk" "net" "stop CoalitionWorker" "$INSTDIR\worker_stop.ico"
	CreateShortCut "$SMPROGRAMS\Coalition\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
	CreateShortCut "$DESKTOP\Coalition Worker Start.lnk" "net" "start CoalitionWorker" "$INSTDIR\worker_start.ico"
	CreateShortCut "$DESKTOP\Coalition Worker Stop.lnk" "net" "stop CoalitionWorker" "$INSTDIR\worker_stop.ico"

	ExecWait '"$INSTDIR\worker" remove'
	ExecWait '"$INSTDIR\worker" -install -auto'
	ExecWait 'net start CoalitionWorker'
SectionEnd

;Section /o "Autorun the worker on idle"
;	ExecWait 'schtasks /Create /TN "Coalition Worker" /SC ONIDLE /IT /I 1 /TR "\"$INSTDIR\worker.exe\""'
;SectionEnd

Section "Uninstall"
	SetShellVarContext all

	; ** Ask the user for a confirmation
	IfSilent noUninstallWarning
		MessageBox MB_YESNO|MB_ICONQUESTION  "Do you want to uninstall Coalition from this computer ?" IDYES Uninstall_yes
			Quit
		Uninstall_yes:
noUninstallWarning:

	;ExecWait 'schtasks /Delete /TN "Coalition Worker" /F'
	ExecWait 'net stop CoalitionServer'
	ExecWait '"$INSTDIR\server" -remove'
	ExecWait 'net stop CoalitionWorker'
	ExecWait '"$INSTDIR\worker" -remove'
	Delete $INSTDIR\uninstall.exe ; delete self (see explanation below why this works) 
	RMDir /r "$SMPROGRAMS\Coalition"
	Delete "$DESKTOP\Coalition Server Monitor.lnk"
	Delete "$DESKTOP\Coalition Server Start.lnk"
	Delete "$DESKTOP\Coalition Server Stop.lnk"
	Delete "$DESKTOP\Coalition Worker Start.lnk"
	DeleteRegKey HKLM "Software\Mercenaries Engineering\Coalition"
	DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Coalition"
__REMOVE_FILES__
Sectionend

Name "Coalition v__VERSION__"
OutFile "Coalition-Win32-__VERSION__.exe"
