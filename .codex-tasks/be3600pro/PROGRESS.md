# Progress

## Recovery
- 当前：阶段 3，按用户新增排除项更新配置，首次构建已主动取消。
- 用户已确认：插件与 AX6600 相同，公开仓库。
- 本地目录原为空，gh 已认证 yjy116；无可用 WSL Linux，实际编译放在 GitHub Actions Ubuntu runner。
- 只读参考克隆：.reference/ax6600（已 gitignore）。
- 下一步：推送最终21个应用配置，启动新构建并检查真实配置与编译结果。

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
