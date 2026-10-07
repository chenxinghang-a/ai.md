# 以管理员身份运行本脚本：将下列第三方服务改为 Manual
# （开机不再自动启动，需要时手动启；如需彻底禁用把 Manual 改成 Disabled）
$svc = @(
  'AiXiaobaoSvr',                 # 腾讯 Androws 安卓模拟器
  'AndrowsSvr',                   # 腾讯 Androws 服务
  'MarvisSvr',                    # 腾讯 Marvis
  'Autodesk Access Service Host', # Autodesk 更新宿主
  'Autodesk CER Service',         # Autodesk 错误上报
  'OfficePLUS Service'            # Office 模板插件
)
foreach ($s in $svc) {
  try {
    Set-Service -Name $s -StartupType Manual
    Write-Host "OK -> Manual: $s"
  } catch {
    Write-Host "FAIL: $s -> $($_.Exception.Message)"
  }
}
Write-Host "`n完成。按回车退出。"
Read-Host
