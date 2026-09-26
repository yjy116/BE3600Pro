# Progress

## Recovery
- 当前：阶段 3，应用配置已通过前轮真实defconfig；192.168.70.1最终配置已推送并启动编译。
- 用户已确认：插件与 AX6600 相同，公开仓库。
- 本地目录原为空，gh 已认证 yjy116；无可用 WSL Linux，实际编译放在 GitHub Actions Ubuntu runner。
- 只读参考克隆：.reference/ax6600（已 gitignore）。
- 下一步：跟踪run 36245537360，检查编译与固件产物；如失败保留日志并定位根因。

## 已核实与用户调整
- owrt cde43ee0d73bef295a96d3a29fe499d69232b448：qualcommbe/ipq53xx，p8。
- 原 PoE 管理及中文包、RTL837x、全部原默认软件保留。不修改 DTS 或分区。
- AX 27 个应用：19 已在官方feed、8 需外源；用户取消独立DAE后最终选26个，DAED保留。
- 不加入Aurora/Argon，只用原默认Bootstrap。
- 外源recipe已固定SHA，原feed存在recipe不会被覆盖。
- 2026-09-26 本地 actionlint、Bash/sh语法、Python编译检查通过；20项验收测试通过（2.218秒，60秒硬超时）。
- 以上为脚本验证，尚未真实编译，也未实机测试。

## 首次交付与编译启动
- 公开仓库：https://github.com/yjy116/BE3600Pro
- 首次提交：7e92b33b8ee38d2eeafa125552b5d91aee988216，本地与远程main SHA一致。
- 完整构建：https://github.com/yjy116/BE3600Pro/actions/runs/36244852058
- 最后本地验证：23项测试通过（2.811秒，60秒超时），actionlint/Bash/sh/Python检查通过。
- 独立审查发现旧Passwall符号与官方feed不匹配，已更正Geoview符号并移除不存在的旧开关。
- 编译尚未完成；尚无固件产物或实机验证。

## 用户进一步精简
- 排除雅典娜LED/屏幕等AX6600专属内容（从未引入）。
- 用户确认无USB，排除USB打印、p910nd、kmod-usb-printer。
- 用户确认同时排除qBittorrent、Samba、Mini Diskmanager、Partexp；同步删除新增后端和对应外源。
- 最终新增21个LuCI应用：15个使用原feeds，6个补充外源。
- run 36244852058 于依赖准备前被主动取消（cancelled），不是固件编译错误；其validate已通过。push run 36244851511也已成功。
- 最终精简提交：6c00812be39498f41d56a4850909bf8109eb486a，本地/远程main一致。
- 新完整构建：https://github.com/yjy116/BE3600Pro/actions/runs/36245100934
- 用户进一步强调核心用途为AC带集客AP：PoE管理与Gecoos AC不可缺失；现有选择已包含，进一步强化前后端/设备驱动验收，不改变本轮插件选择。
- 核心检查已加入配置与manifest两处，缺少PoE前端/中文、RTL837x或Gecoos前后端均失败；24项测试通过（3.094秒，60秒硬超时）。
- 用户指定默认LAN地址192.168.60.1；增加仅修改config_generate中LAN默认值的补丁，保留既有升级配置语义。
- run 36245100934 已通过真实准备与defconfig检查并进入编译；因新的管理IP要求主动取消，准备以最新提交重启。
- 已下载该run配置再次使用强化验收器验证：210项原默认包保留、40项请求包及5项PoE/Gecoos核心包均选择成功。
- feed元数据存在未选择bmx7/librespeed等依赖警告，准备步骤成功，未隐藏日志；完整编译结果仍待验证。
- 用户将管理IP进一步改为192.168.70.1，原60.1构建36245460911也主动取消；70.1为最终生效需求。
- 最终地址提交：d3dcf8fd7d851ba4a6adbbe8ea7959a127a9e22d，本地与远程main一致。
- 最新完整构建：https://github.com/yjy116/BE3600Pro/actions/runs/36245537360
- 70.1补丁已对固定上游文件实际应用、检查新值并通过sh语法；workflow actionlint通过。

## Node.js Actions 弃用警告
- 用户截图来自run 36245537360的validate注释，明确为Node20弃用警告，validate本身成功。
- 根因：两处checkout v4和upload-artifact v4的action.yml都声明node20；GitHub现强制它们使用Node24。
- 修复：改用官方原生Node24版本并固定完整提交SHA；不增加强制旧版本或隐藏警告环境变量。
- 当前完整固件编译保持运行，另用config_only验证新的checkout和artifact上传。插件及70.1默认地址不变。
- 修复提交f50bbfa52a4afc60baed147647dde44ca23f913a已推送，本地/远程main一致。
- push run 36245727885已成功；配置验证run 36245730318的validate通过，annotations为空，artifact上传仍待结果。
- 最终验证：run 36245730318成功，checkout、真实defconfig和upload-artifact全部通过；validate与firmware两个job的annotations均为空。
- 已实际下载新artifact（131664 bytes）并用本地验收器检查：210项原默认包保留、40项请求包和5项PoE/Gecoos核心包均存在；70.1补丁记录正确。
- 此run为config_only，明确跳过完整编译；完整固件仍由run 36245537360继续。

## QModem 排除核查
- 用户要求检查去掉QModem。当前源码锁定清单、插件配置、补包脚本均没有引入它。
- 已核对run 36245100934真实build.config：不存在QModem配置；luci-proto-modemmanager、modemmanager、sms-tool均未选中。
- 固定owrt提交完整树检索也无QModem；保持当前有效插件配置，明确记录排除要求，不为未选择的软件包重启编译。
- 新run 36245730318实际build.config再次验证：选中QModem包列表为空；PoE、Gecoos AC前后端及中文包已选中。
