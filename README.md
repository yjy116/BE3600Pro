# Xiaomi BE3600 Pro Wired p8

基于 [VIKINGYFY/immortalwrt 的 owrt 分支](https://github.com/VIKINGYFY/immortalwrt/tree/owrt)，仅编译 **8 网口版 p8**（`qualcommbe/ipq53xx`）。

保留原默认软件、PoE 管理及中文包、PPE/交换机驱动、分区与镜像规则；对比 AX6600 后增补所需应用。保留 DAED，不加入独立 DAE、Aurora 或 Argon，继续使用上游 Bootstrap 默认主题。排除雅典娜专用插件及 USB 打印、qBittorrent、Samba、Mini Diskmanager、Partexp。

## 插件策略

- [完整对比与来源](docs/plugin-comparison.md)：21 个最终选用应用中，15 个使用官方 LuCI feed，6 个补充外部来源。
- [新增包列表](Config/plugins.config)、[功能配置](Config/features.config)、[源码提交](Config/sources.json) 分别维护。
- 官方已有 HomeProxy、DAED、OpenClash、Passwall 等包保持原实现，不复制 AX6600 的覆盖版本。
- 外部来源仅补缺失 recipe。不修改设备 DTS、镜像规则、NSS 或分区，不迁移 AX6600 的 Wi-Fi 配置。
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

检查会拒绝：错误机型、原默认包被丢弃、所需应用被 defconfig 丢弃、镜像/PoE 包缺失、校验和不符。失败保留诊断资料，不发布假成功固件。

本仓库不改上游管理 IP、主机名或登录密码。应用内置不代表已配置服务；代理订阅、VPN 账户等由使用者设置。

编译成功不等于已通过实机测试。没有执行刷机、PoE 供电、PPE 加速、DAED/eBPF 运行或 USB 外设验证。`factory.ubi` 文件名也不能证明可从原厂网页刷入。

## 基准

- owrt：`cde43ee0d73bef295a96d3a29fe499d69232b448`
- AX6600 插件参考：`696912e6c18113c91cdb5fe1c079c456cbc78cf2`
- 交付进度：[任务记录](.codex-tasks/be3600pro/PROGRESS.md)
