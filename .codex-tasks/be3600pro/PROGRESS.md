# Progress

## Recovery
- 当前：用户要求扩展为DAE/DAED双后端，旧单后端构建run36255985960已取消；正在补齐维护源的互斥逻辑并重新验证。
- 用户已确认：插件与 AX6600 相同，公开仓库。
- 本地目录原为空，gh 已认证 yjy116；无可用 WSL Linux，实际编译放在 GitHub Actions Ubuntu runner。
- 只读参考克隆：.reference/ax6600（已 gitignore）。
- 下一步：完成双后端互斥测试、提交并启动新完整构建；核对两后端、统一LuCI与Aurora版本，保留PoE/Gecoos和70.1地址。

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

## 用户要求重新编译
- 使用最新配置提交c5be9bea64703fb3ffd8dff2eeeda99893cf9877；工作区干净，本地与远程main一致。
- 已请求取消旧Node20工作流run 36245537360，避免重复完整编译。
- 新完整构建：https://github.com/yjy116/BE3600Pro/actions/runs/36246077535
- workflow_dispatch，config_only=false；PoE与Gecoos AC保留，QModem排除，默认地址192.168.70.1。
- 仅确认新运行已创建，最终固件产物仍待实际编译结果。

## 2026-09-27 恢复 Aurora 并升级 DAED
- 已核实 run 36246077535 完整成功，编译/校验/发布全部通过；Release p8-36246077535 包含 p8 两种镜像及校验文件。
- 已下载上一版 manifest 和 feeds.buildinfo；PoE、中文、RTL837x 与 Gecoos 前后端均在；DAED 三包实际为1.27.0-r1。
- 恢复源 CI VIKINGYFY/OpenWRT-CI 使用的 eamonxg Aurora 主题1.4.0-r20260920及设置1.2.5-r20260920，固定提交；不删除原 Bootstrap。
- DAED官方feed仍1.27.0；AX使用QiuSimons/kix，前端package.json标注1.28.0。最新正式v2.1.1前端也保留该数字，不能混同前端标注与后端包版本。
- 对官方DAED recipe应用2.1.1定向补丁，采用正式版完整源码与web.zip，已下载校验两个SHA256；Go1.27满足源码Go1.26要求，CLI与eBPF生成参数核对兼容。
- 独立审查补充unzip -o，避免重新prepare时旧的源码顶层文件触发交互式覆盖提示。
- 新增真实manifest精确版本验收：DAED三包和Aurora两包必须符合声明，不能误用旧包；版本声明和feed补丁同时保存在构建证据。
- 整合复验通过：33项测试5.010秒（60秒硬超时）、actionlint、Bash/Python语法、git diff --check；补丁对实际官方Makefile无偏移应用成功。
- 配置提交e83fe4ebf4640566448337eb15a23b3c5ee51a96已推送，本地和远程main SHA核对一致；push验证run36254769164已成功。
- 新完整编译：https://github.com/yjy116/BE3600Pro/actions/runs/36254780793，workflow_dispatch、config_only=false，目标提交e83fe4e。
- 新run的validate及真实准备/defconfig步骤均成功，已进入Compile and verify firmware；升级补丁、主题补包及原默认/请求包保留检查通过。
- 本轮新固件尚待完整编译结果；未执行实机、旧数据库迁移或eBPF运行验证。

## 维护项目迁移
- 用户要求从1.27.0实际升级至1.28.0或更高，并检查正常维护的fork；进一步明确询问kenzok8/openwrt-daede。
- QiuSimons和daeuniverse/daed均已归档。kenzok8有9月24至25日人工修复及16个SDK构建成功证据，选择固定SHA0b0e5d671e5748a060fbd79abc2f73733b09f902。
- 后端2026.09.24-r2、配套LuCI1.15-r6；已实际下载冻结源并校验527bb166...，读取其中前端package.json为1.28.0。
- 采用完整维护recipe/patches/guard/cleanup，停止使用旧002-daed-2.1.1.patch；已请求取消归档源run36254780793。
- 只选择DAED后端；定向替换旧recipe链接，保留feed源码；相邻dae只复制LuCI打包所需配置资源，不复制Makefile。
- 保留PoE、Gecoos、Aurora和192.168.70.1；Geo周更与新服务读取路径兼容，旧数据库迁移仍待实机验证。
- run36254780793已确认cancelled，因维护源需求调整主动取消。
- 本地整合48项测试：46通过、2项真实符号链接测试因Windows权限不足明确跳过；Linux CI必须完整执行。actionlint、Bash/Python语法与diff检查通过。
- 配置提交34fb4b6efb9ec5c8a84cdb419067a7eceed393ad已推送，本地与远程main SHA一致。
- push验证run36255945821成功：Linux实际48项全部通过（2.374秒，无跳过），包含两项真实symlink操作。
- 新完整构建：https://github.com/yjy116/BE3600Pro/actions/runs/36255985960，config_only=false，编译目标提交34fb4b6。
- 新run的真实Prepare/defconfig检查通过，已进入Compile and verify firmware；原默认与核心包保留、只选DAED及新recipe集成通过配置验收，最终编译与manifest仍待结果。

## DAE / DAED 同步迁移与互斥
- 用户最新要求覆盖此前独立 DAE 排除项：两个后端都迁移，luci-app-daede 统一切换，禁止同时接管流量。
- 实际冻结包确认 DAED 的 wing/go.mod 将 dae 替换为内嵌 dae-core，调用核心 Go API；原方案没有删除 DAED 的核心，但此前未打包独立 dae。
- 旧 1.27.0 内嵌核心为 7e67e31e（2025-11-03）；维护源冻结核心由 be2b6047 性能分支合并上游 6f2f2aa6（2026-09-24），前端 1.28.0 与核心版本不是同一个字段。
- 当前上游切换只 stop 旧服务，没有清除 enabled/rc.d；init 也未检查 active_backend，重启可能双启。需修复持久化互斥并做针对性验证。
- 已请求取消单后端构建 run36255985960，准备双后端新构建。
- run36255985960已确认cancelled。两后台冻结包实际SHA256均通过，520个核心源码文件相同；独立DAE另带DNS response_ttl补丁，不能声称最终核心完全一致。证据写入docs/evidence。
- 配置与manifest测试先验证旧DAE排除规则会失败，再改为双后端必需、旧管理入口排除；26项配置/产物测试及10项版本测试通过。
- 两后台完整recipe已同步替换，原feed源码保留；新增统一启动锁、选择复核、切换持久化禁用、严格RPC错误、guard尾阶段重复停止保护和共享网络清理锁。DAE正常SIGTERM已由真实核心源码确认自行detach/netns.Close，异常强杀清理不作保证。
- 本地最终验证：unittest报告70项、无失败、10条Windows跳过记录（Linux进程锁/信号与真实symlink权限）；耗时10.386秒，60秒硬超时。actionlint、Bash/Python语法、diff和Python文件/函数行限检查通过；待Linux完整执行。
