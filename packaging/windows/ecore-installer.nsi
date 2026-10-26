Unicode True

!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef SOURCE_DIR
  !error "SOURCE_DIR is required"
!endif
!ifndef OUTPUT_FILE
  !error "OUTPUT_FILE is required"
!endif
!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION "0.0.0"
!endif
!ifndef PRODUCT_FILE_VERSION
  !define PRODUCT_FILE_VERSION "0.0.0.0"
!endif

!define PRODUCT_NAME "Bambu Studio E-Core"
!define PRODUCT_PUBLISHER "E-Core Team"
!define PRODUCT_WEB_SITE "https://github.com/WDGame/BambuStudio"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\BambuStudioECore"
!define PRODUCT_DATA_DIR "$LOCALAPPDATA\BambuStudio-PrintFins-Data"
!define PRODUCT_BACKUP_DIR "$LOCALAPPDATA\Programs\Bambu Studio PrintFins.previous"

Name "${PRODUCT_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Bambu Studio PrintFins"
InstallDirRegKey HKCU "${PRODUCT_UNINST_KEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${PRODUCT_FILE_VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${PRODUCT_NAME} installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Bambu Studio contributors and E-Core Team"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\bambu-studio.exe"
!define MUI_FINISHPAGE_RUN_PARAMETERS "--datadir $\"${PRODUCT_DATA_DIR}$\""
!define MUI_FINISHPAGE_RUN_TEXT "Run Bambu Studio E-Core"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} "$R0" "/UPDATE" $R1
  ${IfNot} ${Errors}
    SetSilent silent
  ${EndIf}
FunctionEnd

Section "Bambu Studio E-Core" SEC_MAIN
  SetShellVarContext current
  IfFileExists "$INSTDIR\bambu-studio.exe" 0 install_files
  RMDir /r "${PRODUCT_BACKUP_DIR}"
  ClearErrors
  Rename "$INSTDIR" "${PRODUCT_BACKUP_DIR}"
  ; If an external process still holds a file, keep the existing installation
  ; and fall back to an in-place overwrite instead of deleting user data.

install_files:
  SetOutPath "$INSTDIR"
  File /r "${SOURCE_DIR}\*.*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Bambu Studio E-Core"
  CreateShortcut "$SMPROGRAMS\Bambu Studio E-Core\Bambu Studio E-Core.lnk" \
    "$INSTDIR\bambu-studio.exe" '--datadir "${PRODUCT_DATA_DIR}"' "$INSTDIR\bambu-studio.exe"
  CreateShortcut "$DESKTOP\Bambu Studio E-Core.lnk" \
    "$INSTDIR\bambu-studio.exe" '--datadir "${PRODUCT_DATA_DIR}"' "$INSTDIR\bambu-studio.exe"

  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\bambu-studio.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoRepair" 1

  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} "$R0" "/UPDATE" $R1
  ${IfNot} ${Errors}
    Exec '"$INSTDIR\bambu-studio.exe" --datadir "${PRODUCT_DATA_DIR}"'
  ${EndIf}
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\Bambu Studio E-Core.lnk"
  RMDir /r "$SMPROGRAMS\Bambu Studio E-Core"
  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
  RMDir /r "$INSTDIR"
  RMDir /r "${PRODUCT_BACKUP_DIR}"
  ; User profiles, projects and the network plug-in remain in PRODUCT_DATA_DIR.
SectionEnd
