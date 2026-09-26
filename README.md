# Xiaomi BE3600 Pro Wired p8

基于 [VIKINGYFY/immortalwrt 的 owrt 分支](https://github.com/VIKINGYFY/immortalwrt/tree/owrt)，仅编译 **8 网口版 p8**（`qualcommbe/ipq53xx`）。

用途：**作为 AC 管理集客 AP**。PoE 管理（含中文）以及 Gecoos AC 前端和后端是核心功能，配置和最终固件均检查其存在。

保留原默认软件、PoE 管理及中文包、PPE/交换机驱动、分区与镜像规则；对比 AX6600 后增补所需应用。DAE 与 DAED 同时内置，由统一界面切换运行。恢复上游 CI 使用的 Aurora 主题及设置插件，Bootstrap 包仍保留。不加入 Argon、QModem、雅典娜专用插件及 USB 打印、qBittorrent、Samba、Mini Diskmanager、Partexp。

## 插件策略

- [完整对比与来源](docs/plugin-comparison.md)：保留 AX6600 的 22 项选用应用功能，DAE/DAED 合并为一个管理入口；14 个入口使用官方 LuCI feed，7 个使用外部来源；另添加 Aurora 主题及设置插件。
- [新增包列表](Config/plugins.config)、[功能配置](Config/features.config)、[源码提交](Config/sources.json) 分别维护。
- 官方已有 HomeProxy、OpenClash、Passwall 等包保持原实现。DAE 与 DAED 同步迁移至持续维护的 `kenzok8/openwrt-daede`，均为 `2026.09.24-r2`，由 `luci-app-daede 1.15-r6` 统一管理；[版本、核心来源及互斥说明](docs/daed-version.md)。
- 外部来源通常只补缺失 recipe；DAE/DAED 是明确授权的定向替换，保留完整维护补丁和服务脚本，并修复双后端的启动互斥。不修改设备 DTS、镜像规则、NSS 或分区，不迁移 AX6600 的 Wi-Fi 配置。
- Tailscale 的界面与后端都提供同名配置/启动文件；保留官方后端二进制版本，明确让新增 LuCI 包拥有这两个文件，变更记录在构建日志中。
- GeoIP/Geosite 初始数据继续使用上游包；单独提供更新脚本，保留 AX6600 的周日 04:00 更新安排。下载或 SHA256 校验失败直接失败，不使用代理回退下载。

## 编译

在 **Actions → BE3600 Pro Wired p8 → Run workflow** 运行。`config_only` 只执行真实 feeds/defconfig 和保留检查；默认为完整编译。普通 push/PR 只执行脚本验收检查。

Ubuntu 24.04 本地编译同样可执行：

```sh
bash scripts/install_dependencies.sh
bash scripts/prepare.sh
bash scripts/build.sh
```

使用新的工作目录执行准备步骤。源码与外部 recipe 使用记录的提交；默认 feeds 跟随上游配置，每次构建记录实际 feed SHA，因此并不宣称不同时间构建逐字节相同。

## 产物和验证

完整构建成功且检查通过后创建 Release，保留原文件名的 `sysupgrade.bin`、`factory.ubi`、manifest、`profiles.json`、`sha256sums` 和 buildinfo。实际配置、源码 SHA、feeds SHA、准备/下载/编译日志保存在 Actions artifact。

检查会拒绝：错误机型、原默认包被丢弃、所需应用被 defconfig 丢弃、镜像或 PoE/Gecoos AC 核心包缺失、指定 DAE/DAED/Aurora 版本不符、校验和不符。失败保留诊断资料，不发布假成功固件。

新固件默认管理地址为 **192.168.70.1/24**，只修改 LAN 初始默认值，保留主机名和登录密码规则。保留配置升级时已有 LAN 配置可能继续生效；恢复默认或首次安装使用新地址。应用内置不代表已配置服务；代理订阅、VPN 账户等由使用者设置。

Aurora 使用源 CI 的 `eamonxg/luci-theme-aurora` 和 `eamonxg/luci-app-aurora-config`。全新配置由主题自带初始化脚本设为 Aurora；保留配置升级时，已有主题设置可能继续生效，可在 LuCI 中选择 Aurora。

DAE/DAED 在“服务 → daede”选择后端，默认选择 DAED，首次安装均未启用代理服务。切换会停止并取消旧后端的开机启用，再选择新后端；新后端需要单独启用。两套配置分别保留，DAED 的数据库不会自动转为 DAE 配置。启动脚本核对当前选择和另一后端进程，并使用覆盖进程生命周期的共享锁，避免同时接管流量。

Gecoos AC 的上游默认配置为未启用，首次使用需在其管理页面启用并启动服务；后端使用端口 `60650`，配置数据库位于 `/etc/gecoosac`。PoE 的上游配置默认启用，p8 机型控制 7 个供电 LAN 口。这里描述源码默认值，实际 AP 接入和供电仍需设备验证。

编译成功不等于已通过实机测试。没有执行刷机、PoE 供电、PPE 加速、DAED/eBPF 运行或 USB 外设验证。`factory.ubi` 文件名也不能证明可从原厂网页刷入。

## 基准

- owrt：`cde43ee0d73bef295a96d3a29fe499d69232b448`
- AX6600 插件参考：`696912e6c18113c91cdb5fe1c079c456cbc78cf2`
- 交付进度：[任务记录](.codex-tasks/be3600pro/PROGRESS.md)
