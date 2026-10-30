; Inno Setup 脚本 - 用于创建 AutoCutVideo 的安装包
; 请下载并安装 Inno Setup 编译器后运行此脚本：https://jrsoftware.org/isinfo.php

[Setup]
; 应用程序的基本信息
AppName=AutoCutVideo
AppVersion=2.6.5
AppPublisher=您的公司或名字
; 默认安装目录，{autopf} 代表 Program Files
DefaultDirName={autopf}\AutoCutVideo
; 开始菜单文件夹名称
DefaultGroupName=AutoCutVideo
; 输出安装包的文件名和存放目录
OutputDir=d:\AutoCutVideo_v2\dist
OutputBaseFilename=AutoCutVideo_Setup_v2.6.5
; 压缩方式
Compression=lzma2/ultra
SolidCompression=yes
; 卸载程序设置
UninstallDisplayIcon={app}\AutoCutVideo.exe
; 安装包图标（可选，这里用项目里的 logo）
SetupIconFile=d:\AutoCutVideo_v2\logo.ico

[Tasks]
; 提供在桌面上创建快捷方式的选项
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
; 这里的 Source 必须指向你用 AutoCutVideo_Directory.spec 导出的单目录版本
; \dist\AutoCutVideo\* 会把打包出来的文件夹内所有内容拷贝到用户的安装目录
Source: "d:\AutoCutVideo_v2\dist\AutoCutVideo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 创建开始菜单和桌面快捷方式
Name: "{group}\AutoCutVideo"; Filename: "{app}\AutoCutVideo.exe"; IconFilename: "{app}\AutoCutVideo.exe"
Name: "{group}\卸载 AutoCutVideo"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AutoCutVideo"; Filename: "{app}\AutoCutVideo.exe"; Tasks: desktopicon; IconFilename: "{app}\AutoCutVideo.exe"

[Run]
; 安装完成后提供运行程序的选项
Filename: "{app}\AutoCutVideo.exe"; Description: "启动 AutoCutVideo"; Flags: nowait postinstall skipifsilent
