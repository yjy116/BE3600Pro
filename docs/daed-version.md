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

## 本次采用正式版 2.1.1

核查时项目最新正式发布是 [v2.1.1](https://github.com/daeuniverse/daed/releases/tag/v2.1.1)，发布于 2026-09-24。
发布提交为 `b3043aa7ce07c774c65e546112aa2c7a1c12edb5`；仓库于同日归档。
该发布的 `apps/web/package.json` 仍写 1.28.0，因此网页显示此数字不等于后端仍未升级。

本次保留官方 LuCI 管理入口、服务脚本、内核依赖与数据包规则；
通过 [`002-daed-2.1.1.patch`](../patches/002-daed-2.1.1.patch) 定向更新现有 recipe，
不复制 AX6600 的整套覆盖脚本。前端、wing 与 dae-core 使用同一正式发布：

- wing：`dc503088945812c11235b35362d2bfa1a4c3bdf0`。
- dae-core：`85a1fc3c06e3765d143c868ba97ecd0be2aab4ea`。
- 完整源码 `daed-full-src.zip` SHA256：`86a64e92a5d075f67938fb0c89126dc3067dc5fec8cfec6d16013f8d5f778f47`。
- 前端 `web.zip` SHA256：`7eb8f42d4860ab7311f87bda2a921bad34a6d54db7edad47466dcb8d9382fea8`。

两个官方发布包已实际下载并核对 SHA256；完整源码包含嵌套核心源码，无需动态拉取核心分支。
源码要求 Go 1.26，已核查官方 feed 默认 Go 1.27 满足这一版本要求。
原有 `run`、配置目录、监听地址等启动参数保留；新版包含数据库结构迁移，因此实机升级和原有数据库兼容性仍需验证。

构建必须验证 manifest 中 DAED 及两个数据依赖包均为 `2.1.1-r1`；记录 package feed 的实际差异。
完整编译、DAED 启动、eBPF 加载及实际代理功能是不同验证阶段，不能以本地静态检查替代。
