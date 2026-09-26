# DAED 版本核查与更新

核查日期：2026-09-27。软件包版本、LuCI 包版本和网页的前端版本是不同字段。

## 为什么上一版是 1.27.0

[完整构建 36246077535](https://github.com/yjy116/BE3600Pro/actions/runs/36246077535)
的实际 manifest 包含 `daed`、`daed-geoip`、`daed-geosite`，均为 `1.27.0-r1`。
该构建使用 `immortalwrt/packages` 提交 `6d68ffeb270860be5d73ee2898d58e7c6019d9a4`；
其 [`net/daed/Makefile`](https://github.com/immortalwrt/packages/blob/6d68ffeb270860be5d73ee2898d58e7c6019d9a4/net/daed/Makefile)
明确指定 1.27.0，核查时 master 也仍为该版本。因此是 feed 配方落后于 DAED 项目发布，构建没有自动追踪项目最新版。

LuCI 管理入口 `luci-app-daed` 的版本是 `26.261.08411~adc898b`，来自官方 LuCI feed，不能用它判断 DAED 后端版本。

## AX6600 的 1.28.0 从哪里来

AX6600 的 [`Scripts/Packages.sh`](https://github.com/yjy116/Immortalwrt-CI-JDC-AX6600/blob/696912e6c18113c91cdb5fe1c079c456cbc78cf2/Scripts/Packages.sh)
引入 `QiuSimons/luci-app-daed:kix`，覆盖与定制的路径和 BE3600 Pro 原方案不同。
核查到该源提交 `bc9a40e08b3c926a4d324f87911cba5e85dce8e6` 的后端包版本为 `2026.08.26`，
前端源码固定到 `daeuniverse/daed@671e65d2fdcd62fe6a3ec18ecda209c5addea898`。
该提交的 [`apps/web/package.json`](https://github.com/daeuniverse/daed/blob/671e65d2fdcd62fe6a3ec18ecda209c5addea898/apps/web/package.json)
标注 1.28.0，与用户看到的前端数字一致；但不据此断言已安装 AX6600 的精确后端提交。

## 改用持续维护的 kenzok8 来源

原 DAED 项目发布过 [v2.1.1](https://github.com/daeuniverse/daed/releases/tag/v2.1.1)，随后归档；
`QiuSimons/luci-app-daed` 也已归档。前一轮曾配置官方 v2.1.1，用户进一步要求维护中的 fork 后，
本次切换至 [kenzok8/openwrt-daede](https://github.com/kenzok8/openwrt-daede)，不再应用旧的官方 2.1.1 补丁。

选择依据是实际维护和构建证据：9月24日修复初始化向导，9月25日修复日志和 netns 状态；
[维护源构建 36165368501](https://github.com/kenzok8/openwrt-daede/actions/runs/36165368501)
已成功完成包括 aarch64 Cortex-A53 在内的 SDK 构建。这不等同于我们的 p8 固件或实机验证。
另查到的 `ksong008/DaedNext` 已转为 Rust/DaeNext 架构，不能作为现有 Go DAED 的直接包替换，本次不采用。

固定来源如下，数字保持维护者定义，不将旧代码伪装为新版本：

- 配方提交：`0b0e5d671e5748a060fbd79abc2f73733b09f902`。
- `daed`：`2026.09.24-r2`，使用维护者的日期版本号。
- `luci-app-daede`：`1.15-r6`，替代旧 `luci-app-daed` 管理入口。
- 前端源码 `apps/web/package.json`：`1.28.0`，已从实际冻结源码包读取确认。
- 冻结源码：`daed-src-2026.09.24-527bb166b1ae.tar.gz`。
- SHA256：`527bb166b1aea6a54330ebbc8be5b0418baed74636b838aeaa78c17b70f2f996`，已实际下载校验。

[维护源的 ci/pins.env](https://github.com/kenzok8/openwrt-daede/blob/0b0e5d671e5748a060fbd79abc2f73733b09f902/ci/pins.env)
记录 DAED `be4ef873c352a9ec930c877a3a821163f4b4ac0a`、
wing `b089b568649f03f909477adb6c7db25535a58782` 以及 core/outbound/quic-go 的固定提交。
因此这次实际升级了源码、后台维护补丁和网页，不是仅修改版本字符串。

## 集成与保留边界

- 完整复制该来源的 `daed`、`luci-app-daede`，包含后台补丁、guard、cleanup、配置保留文件；只替换官方 DAED recipe 的安装链接，原 feed 源码保留。
- LuCI 构建显式补充 `luci-base/host` 依赖，确保其 `po2lmo` 翻译工具先构建；此适配记录在构建证据。
- 选择 LuCI 的 DAED 后端，禁用独立 `dae`、`luci-app-dae` 和旧 `luci-app-daed`，配置与最终 manifest 都检查排除项。
- 新 LuCI 打包时需要相邻 `dae/files/dae.config` 作为默认资源；只复制该资源，不复制 `dae/Makefile`，因此不会为此引入独立 DAE。
- 管理入口改为“服务 → daede”。原 `/etc/config/daed`、`/etc/daed/wing.db` 保留，维护源还声明保留 WAL 数据文件；已有数据库迁移仍需实机确认。
- 保留现有 Geo 周更。新服务直接使用 `/usr/share/v2ray`，新 LuCI 的额外 Geo 自动更新默认不启用。

源码要求 Go 1.26，当前 feed 默认 Go 1.27；保持原 BTF/eBPF 内核选择。
最终 manifest 必须符合 `Config/package-versions.json` 的精确版本要求。
完整编译、设备启动、eBPF 加载、旧数据库迁移及代理功能分别验证，不以静态检查代替实际运行。
