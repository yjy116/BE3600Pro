# DAE / DAED 版本、核心来源与后端切换

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
- `dae`、`daed`：均为 `2026.09.24-r2`，使用维护者的日期版本号。
- `luci-app-daede`：`1.15-r6`，统一替代旧 `luci-app-dae`、`luci-app-daed` 管理入口。
- 前端源码 `apps/web/package.json`：`1.28.0`，已从实际冻结源码包读取确认。
- 冻结源码：`daed-src-2026.09.24-527bb166b1ae.tar.gz`。
- SHA256：`527bb166b1aea6a54330ebbc8be5b0418baed74636b838aeaa78c17b70f2f996`，已实际下载校验。

[维护源的 ci/pins.env](https://github.com/kenzok8/openwrt-daede/blob/0b0e5d671e5748a060fbd79abc2f73733b09f902/ci/pins.env)
记录 DAED `be4ef873c352a9ec930c877a3a821163f4b4ac0a`、
wing `b089b568649f03f909477adb6c7db25535a58782` 以及 core/outbound/quic-go 的固定提交。
因此这次实际升级了源码、后台维护补丁和网页，不是仅修改版本字符串。

## DAE 核心是否同步更新

DAED 集成了 DAE 核心、API 和网页。冻结包中的 `wing/go.mod:133` 使用
`replace github.com/daeuniverse/dae => ./dae-core`，`wing/dae/run.go` 直接调用核心的控制平面 API。
构建配方在 `dae-core` 生成 eBPF 并将 `dae-wing` 安装为 `/usr/bin/daed`，不调用独立 `/usr/bin/dae`。
`go.mod` 里的 `require ... v0.2.0` 被本地 replace 覆盖，不能据此判断实际核心过旧。

上一版 1.27.0 的子模块链固定为 `dae-wing@6bb6a310ef3d98bea691fd5955cc703306835546`
→ `dae@7e67e31e241a6d2cc5f2b5ff228b4fb5faf6d24a`（2025-11-03）。
新维护源的两个组装工作流共同使用 `ci/pins.env`：

| 组成 | 固定来源 |
| --- | --- |
| DAE 性能分支基础 | `kenzok8/dae@be2b6047eff8be8da7dfdcd0c007fd6d9f7f5175` |
| 合入的 DAE 上游 | `daeuniverse/dae@6f2f2aa66084f3d736e4bf86a327e3523b3cdede`（2026-09-24） |
| outbound | `kenzok8/outbound@ebd5cd55cbda1614987db6149eef22144b459fe0` |
| quic-go | `62d80bbebb5b0ff3ff143786ea65077bdfd67853` |

独立 DAE 冻结包为 `dae-src-2026.09.24-17135da7c881.tar.gz`，实际下载 SHA256 为
`17135da7c881800738cc63566160d4ee6d59a8a70ae5043b8005c5d189b05752`。
与上述 DAED 冻结包逐文件比较：520 个核心 Go/C/头文件/汇编文件全部一致；
642 个共同文件中仅 `go.mod`、`go.sum` 有差别，其中包含两种目录布局所需的本地依赖路径差异。
独立包多出的 `default.pgo` 与 DAED 的 `wing/default.pgo` 内容相同，outbound 与 quic-go 内容也一致。
实际逐文件比较结果保存在[审计证据](evidence/dae-core-comparison-20260924.json)。

这是共享冻结核心来源，不表示两种程序最终字节相同：独立 DAE 另应用维护源的
`dae/patches/010-dns-response-ttl.patch`，DAED 还有自己的 wing 补丁。两套补丁保持各自维护者的组合。
构建证据额外保存 `daede-core-pins.env`、`dae-Makefile`、`daed-Makefile` 与替换记录。

## 两个后端如何避免同时接管流量

两种后端都内置；LuCI 的编译 `choice` 只决定自动依赖，保持选择 DAED，独立 DAE 显式加入插件配置。
运行时选择由 `/etc/config/daede` 的 `active_backend` 控制，默认 `daed`，全新配置的两个服务均未启用。

固定维护源的切换逻辑只停止旧进程，没有清除旧服务的 UCI enabled 与开机启动项；两个 init
也没有核对 `active_backend`，因此需要本仓库的最小互斥适配：

- 切换前停止并取消旧后端的开机启用，确认停止成功后才切换；新后端由用户单独启用。
- init 在创建网络和启动进程之前核对当前选择，另一后端仍在运行时明确拒绝启动。
- 两个进程通过同一 `flock` 锁启动并持锁到退出；DAED 包括 guard 清理结束。拿锁后再次核对当前选择，防止并发启动穿过进程检查。
- 停止闲置 DAE 不得清除运行中 DAED 的共享网络资源。
- 适配失败直接中止构建，变更记录在 `daede-source.json`；测试验证启动选择与切换行为，不等同于实机验证。

DAE 的文本配置与 DAED 的数据库分别保留，不自动将数据库转换为 DAE 配置；切换后需核对所选后端的配置。
互斥适配随本仓库构建提供；单独安装维护源原始 DAE/DAED/LuCI 软件包会覆盖相应适配，更新时需保持本仓库构建的配套组合。

## 集成与保留边界

- 完整复制该来源的 `dae`、`daed`、`luci-app-daede`，包含后台补丁、guard、cleanup、配置保留文件；先验证两个官方 recipe 的链接，复制与适配成功后才替换，原 feed 源码保留。
- LuCI 构建显式补充 `luci-base/host` 依赖，确保其 `po2lmo` 翻译工具先构建；此适配记录在构建证据。
- 配置与最终 manifest 都要求 `dae`、`daed`、`luci-app-daede`，拒绝旧 `luci-app-dae`、`luci-app-daed` 两个重复管理入口。
- 两种后端均使用内核 BTF，保留实际 eBPF 能力。
- 统一 LuCI 安装共享锁启动程序并依赖 `flock`，插件清单也显式要求该锁工具。
- 管理入口改为“服务 → daede”。原 `/etc/config/daed`、`/etc/daed/wing.db` 保留，维护源还声明保留 WAL 数据文件；已有数据库迁移仍需实机确认。
- 保留现有 Geo 周更。新服务直接使用 `/usr/share/v2ray`，新 LuCI 的额外 Geo 自动更新默认不启用。

源码要求 Go 1.26，当前 feed 默认 Go 1.27；保持原 BTF/eBPF 内核选择。
最终 manifest 必须符合 `Config/package-versions.json` 的精确版本要求。
完整编译、设备启动、eBPF 加载、旧数据库迁移及代理功能分别验证，不以静态检查代替实际运行。
