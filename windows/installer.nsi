Unicode true
SetCompressor /SOLID lzma

!define APP_NAME "NoLags Browser"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Danechka"
!define APP_URL "https://github.com/frizovdanyash/nolagsbrowser"
!define APP_EXE "NoLagsBrowser.exe"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "/home/user/nolagsbrowser/dist/nolagsbrowser-${APP_VERSION}-setup.exe"
InstallDir "$PROGRAMFILES64\NoLags Browser"
InstallDirRegKey HKLM "Software\NoLagsBrowser" "InstallDir"
RequestExecutionLevel admin
SetCompressorDictSize 32

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "${APP_NAME} installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "MIT License"

!include "MUI2.nsh"
!include "x64.nsh"

!define MUI_ICON "/home/user/nolagsbrowser/windows/NoLagsBrowser/Resources/nolagsbrowser.ico"
!define MUI_UNICON "/home/user/nolagsbrowser/windows/NoLagsBrowser/Resources/nolagsbrowser.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Запустить NoLags Browser"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "/home/user/nolagsbrowser/dist/win-x64/${APP_EXE}"
  WriteRegStr HKLM "Software\NoLagsBrowser" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateShortCut "$DESKTOP\NoLags Browser.lnk" "$INSTDIR\${APP_EXE}"
  CreateDirectory "$SMPROGRAMS\NoLags Browser"
  CreateShortCut "$SMPROGRAMS\NoLags Browser\NoLags Browser.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortCut "$SMPROGRAMS\NoLags Browser\Удалить.lnk" "$INSTDIR\uninstall.exe"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "URLInfoAbout" "${APP_URL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser" "UninstallString" "$INSTDIR\uninstall.exe"

  WriteRegStr HKLM "Software\Classes\NoLagsBrowserHTML" "" "NoLags Browser Document"
  WriteRegStr HKLM "Software\Classes\NoLagsBrowserHTML\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
  WriteRegStr HKLM "Software\Classes\http\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
  WriteRegStr HKLM "Software\Classes\https\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\NoLags Browser.lnk"
  Delete "$SMPROGRAMS\NoLags Browser\NoLags Browser.lnk"
  Delete "$SMPROGRAMS\NoLags Browser\Удалить.lnk"
  RMDir "$SMPROGRAMS\NoLags Browser"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoLagsBrowser"
  DeleteRegKey HKLM "Software\NoLagsBrowser"
  DeleteRegKey HKLM "Software\Classes\NoLagsBrowserHTML"
SectionEnd
