# BE3600 Pro Wired p8 插件对比与保留规则

审计日期：2026-09-26。目标为 `qualcommbe/ipq53xx` 的
`xiaomi_be3600-pro-wired-p8`。本文记录源码与配置的静态对比，不代表已完成固件编译或实机验证。

用户最终选择：保留 DAED；排除独立 DAE、USB 打印，以及 qBittorrent、Samba、Mini Diskmanager、Partexp 四项 NAS 应用。不增加 Argon、Aurora，继续使用原默认 Bootstrap 主题。下文保留 AX6600 原 27 个应用的比较记录，排除上述 6 项后，本次最终选择 21 个：官方 feeds 15 个，外部补充 6 个。

不追加 `qbittorrent`、`p910nd`、`kmod-usb-printer` 后端或驱动，不拉取 Mini Diskmanager、Partexp 外源。原始设备已有的存储、文件系统与 USB 基础包继续保留。

## 比较基准

- 原始源码：[`VIKINGYFY/immortalwrt`，`owrt`](https://github.com/VIKINGYFY/immortalwrt/tree/cde43ee0d73bef295a96d3a29fe499d69232b448)，审计提交 `cde43ee0d73bef295a96d3a29fe499d69232b448`。
- AX6600 参考：[`Config/GENERAL.txt`](https://github.com/yjy116/Immortalwrt-CI-JDC-AX6600/blob/696912e6c18113c91cdb5fe1c079c456cbc78cf2/Config/GENERAL.txt)，审计提交 `696912e6c18113c91cdb5fe1c079c456cbc78cf2`；该文件显式选择 26 个 LuCI 应用，[`Scripts/Settings.sh`](https://github.com/yjy116/Immortalwrt-CI-JDC-AX6600/blob/696912e6c18113c91cdb5fe1c079c456cbc78cf2/Scripts/Settings.sh) 再选择 SQM，共比较 27 个应用。
- 原始源码的 [`feeds.conf.default`](https://github.com/VIKINGYFY/immortalwrt/blob/cde43ee0d73bef295a96d3a29fe499d69232b448/feeds.conf.default) 使用 `immortalwrt/luci` 与 `immortalwrt/packages` 等 feeds，没有固定提交；此次查验的 [LuCI feed](https://github.com/immortalwrt/luci/tree/adc898b447eb4ee8023398182f5d0de2e8817e81) 提交为 `adc898b447eb4ee8023398182f5d0de2e8817e81`。

“原始默认”按源码的全局、平台、子平台、设备默认包和 LuCI 依赖判断。“feeds 可用”仅表示该次审计能找到包定义；最终依赖和选择结果仍须经过 feeds 安装、`make defconfig` 及构建 manifest 核对。

## 原设备内容完整保留

[`target/linux/qualcommbe/image/ipq53xx.mk`](https://github.com/VIKINGYFY/immortalwrt/blob/cde43ee0d73bef295a96d3a29fe499d69232b448/target/linux/qualcommbe/image/ipq53xx.mk#L78) 的 Wired 设备定义明确添加：

- `luci-app-tmi-poe`：原设备 PoE 管理应用。
- `luci-i18n-tmi-poe-zh-cn`：原 PoE 应用中文翻译。
- `kmod-dsa-rtl837x`：原设备交换芯片驱动。

同一定义移除 `kmod-ath12k` 和 `kmod-leds-gpio`。保留该上游规则和 p8 的设备继承、镜像、分区与驱动布局，不移植 AX6600 的删除无线、NSS 驱动或扩展内核分区脚本。

同时保留 [`include/target.mk`](https://github.com/VIKINGYFY/immortalwrt/blob/cde43ee0d73bef295a96d3a29fe499d69232b448/include/target.mk)、[`qualcommbe/Makefile`](https://github.com/VIKINGYFY/immortalwrt/blob/cde43ee0d73bef295a96d3a29fe499d69232b448/target/linux/qualcommbe/Makefile) 和 [`ipq53xx/target.mk`](https://github.com/VIKINGYFY/immortalwrt/blob/cde43ee0d73bef295a96d3a29fe499d69232b448/target/linux/qualcommbe/ipq53xx/target.mk) 中其余原始默认包及其设备级调整，包括 PPE、DSA、文件系统、USB、基础网络服务和系统管理组件。插件补充不得通过重写这些文件裁剪原功能。

`wpad-openssl` 和 `ath12k-firmware-ipq5332-ddwrt` 仍在原继承链中；Wired 定义只减去指定驱动，不据设备名称进一步删除这些原默认包。

原平台选择 `luci`；官方 [`luci`](https://github.com/immortalwrt/luci/blob/adc898b447eb4ee8023398182f5d0de2e8817e81/collections/luci/Makefile) 与 [`luci-light`](https://github.com/immortalwrt/luci/blob/adc898b447eb4ee8023398182f5d0de2e8817e81/collections/luci-light/Makefile) 的依赖带入防火墙、软件包管理、管理界面、IPv6/PPP 协议和 Bootstrap 默认主题，均应保留。

注意：`include/target.mk` 虽定义 `DEFAULT_PACKAGES.tweak`，其加入默认包的语句已被注释，不能将其中的 `luci-app-cpufreq` 或 `default-settings-chn` 误记为默认启用。平台默认已有 `cpufreq` 后端，但其 LuCI 前端是另一软件包。

## AX6600 的 27 个应用逐项比较

| 类别 | 数量 | 本次策略 |
| --- | ---: | --- |
| 原始 owrt/p8 默认已启用 | 0 | 原有 PoE、防火墙等应用继续保留，但不属于这 27 项 |
| 官方 LuCI feed 有定义，原始默认未启用 | 19 | 最终选择 15 项；排除 DAE、USB 打印、qBittorrent、Samba |
| 官方 LuCI feed 与原始源码均无定义 | 8 | 最终补充 6 项；排除 Mini Diskmanager、Partexp 及其外源 |

官方 feeds 已有的 19 个参考应用如下，其中 15 项纳入最终选择。此表中的“启用”表示本次应追加的构建选择；不代表相关服务已经在设备上启动或验证。

| 包名 | 原始状态 | 本次处理 |
| --- | --- | --- |
| `luci-app-adguardhome` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-autoreboot` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-cpufreq` | feeds 可用，仅后端默认已有 | 启用官方前端 |
| `luci-app-dae` | feeds 可用，未默认启用 | 按最终要求排除，不添加独立 DAE 应用 |
| `luci-app-daed` | feeds 可用，未默认启用 | 启用官方包及其依赖 |
| `luci-app-ddns-go` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-homeproxy` | feeds 可用，未默认启用 | 启用官方包及其依赖 |
| `luci-app-openclash` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-passwall` | feeds 可用，未默认启用 | 启用官方包，核对参考配置中的 nftables、Geoview、Haproxy、Xray 选项 |
| `luci-app-qbittorrent` | feeds 可用，未默认启用 | 按最终要求排除，同时不追加 `qbittorrent` 后端 |
| `luci-app-samba4` | feeds 可用，未默认启用 | 按最终要求排除 |
| `luci-app-sqm` | feeds 可用，未默认启用 | 使用标准 `sqm-scripts`，不搬入 `sqm-scripts-nss` |
| `luci-app-statistics` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-ttyd` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-upnp` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-usb-printer` | feeds 可用，未默认启用 | 按最终要求排除，同时不追加 `p910nd`、`kmod-usb-printer` |
| `luci-app-vlmcsd` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-vnstat2` | feeds 可用，未默认启用 | 启用官方包 |
| `luci-app-zerotier` | feeds 可用，未默认启用 | 启用官方包 |

历史比较中缺失的 8 个应用按照 AX6600 [`Scripts/Packages.sh`](https://github.com/yjy116/Immortalwrt-CI-JDC-AX6600/blob/696912e6c18113c91cdb5fe1c079c456cbc78cf2/Scripts/Packages.sh) 追溯来源。最终使用其中 6 项；Mini Diskmanager、Partexp 仅保留历史来源记录，本次不拉取、不添加：

| 包名 | 外部来源 | 参考分支 | 补充边界 |
| --- | --- | --- | --- |
| `luci-app-nikki` | [nikkinikki-org/OpenWrt-nikki](https://github.com/nikkinikki-org/OpenWrt-nikki) | `main` | 补充缺失的前端与必要依赖 |
| `luci-app-gecoosac` | [VIKINGYFY/packages](https://github.com/VIKINGYFY/packages) | `main` | 定向补包，保留已有 HomeProxy、sing-box 等 |
| `luci-app-mini-diskmanager` | [4IceG/luci-app-mini-diskmanager](https://github.com/4IceG/luci-app-mini-diskmanager) | `main` | 历史参考；本次排除，不拉取此来源 |
| `luci-app-partexp` | [sirpdboy/luci-app-partexp](https://github.com/sirpdboy/luci-app-partexp) | `main` | 历史参考；本次排除，不拉取此来源 |
| `luci-app-tailscale` | [asvow/luci-app-tailscale](https://github.com/asvow/luci-app-tailscale) | `main` | 补充前端，后端优先沿用官方 feeds |
| `luci-app-easytier` | [EasyTier/luci-app-easytier](https://github.com/EasyTier/luci-app-easytier) | `main` | 补充缺失应用，已有依赖优先保留 |
| `luci-app-wolultra` | [VIKINGYFY/packages](https://github.com/VIKINGYFY/packages) | `main` | 定向补包，不整库覆盖官方 feeds |
| `luci-app-lucky` | [gdy666/luci-app-lucky](https://github.com/gdy666/luci-app-lucky) | `main` | 补充缺失应用，已有依赖优先保留 |

这些是参考仓库采用的分支，不是固定版本。构建证据应记录实际源码与外部包提交；静态发现包定义不保证该版本在 p8 上能够编译或运行。外部包与官方包若出现依赖、文件归属或版本冲突，必须显式报告并处理，不能通过静默删除官方包解决。

## 主题与其他参考配置

| 项目 | 原始状态 | 本次处理 |
| --- | --- | --- |
| `luci-theme-bootstrap` | 原 LuCI 默认主题 | 保留默认 |
| `luci-theme-argon` | 官方 LuCI feed 可用，未默认选择 | 按最终要求不添加 |
| `luci-theme-aurora` | 官方 LuCI feed 无定义 | 按最终要求不添加，也不拉取 Aurora 来源 |
| `luci-proto-wireguard`、`luci-proto-relay` | AX6600 的额外协议选择 | 单独核对并追加，不替换原 IPv6/PPP 协议 |

不执行 AX6600 脚本中的全局主题替换，也不照搬其主机名、LAN 地址或无线设置。按用户要求，排除 AX6600 专用 `luci-app-athena-led`（雅典娜 LED 屏幕插件）和 `files/etc/uci-defaults/99-athena-led-config-migration` 迁移脚本，不为 BE3600 Pro Wired 添加这些设备专属内容。AX6600 下载了但没有显式选择的 `momo、passwall2、kucat、diskman、mosdns、openlist2、qmodem、quickfile、vnt、pushbot`，不因下载脚本中出现就视为本次新增要求。

AX6600 本地 `package/dae` 使用 `olicesx/dae:kdae`、自定义 outbound 和动态 Go 依赖，另有本地 `luci-app-dae`、`v2ray-geodata` 覆盖包。本次原有包优先，保留官方 feeds 中的 daed、HomeProxy 及相关已有后端和数据包实现；不复制这些覆盖包，也不删除 feeds 中同名包。保留 DAED 所需的 eBPF/BTF 等实际内核能力，不能整段移植旧 `qualcommax` 内核配置。独立 DAE 不作显式构建选择；必要依赖仍以官方包定义为准。

## 原始源码与独立 CI 配置的区别

[`VIKINGYFY/OpenWRT-CI`](https://github.com/VIKINGYFY/OpenWRT-CI) 是独立构建配置仓库，其 `Config/GENERAL.txt` 会追加大量插件；它不是 `VIKINGYFY/immortalwrt:owrt` 的源码默认包清单。其 [`QCB-ALL.yml`](https://github.com/VIKINGYFY/OpenWRT-CI/blob/main/.github/workflows/QCB-ALL.yml) 和 [`IPQ53XX-WIFI-NO.txt`](https://github.com/VIKINGYFY/OpenWRT-CI/blob/main/Config/IPQ53XX-WIFI-NO.txt) 可佐证平台使用 `owrt`、`qualcommbe/ipq53xx` 以及 p5/p8 目标，但不能据此把 CI 的 GENERAL 插件当作设备原生默认。本次用户已选 p8，不同时生成 p5 镜像。

## 验证状态与交付证据

已完成源码默认包、官方 LuCI 包定义和 AX6600 选择项的静态比较。首轮 CI 因用户调整插件范围主动取消，尚未取得本次最终配置的完整编译成功证据；未执行 BE3600 Pro Wired p8 刷机、启动、PoE、交换端口、USB 外设、硬件加速或代理功能实机验证。

后续构建须保存实际 `.config`、源码/feeds/外部包提交、构建日志、manifest、校验文件与镜像信息，并核对：原 PoE 应用及中文、RTL837x 驱动仍在；原设备/分区/驱动布局未被定制脚本改写；最终选择的 21 个追加应用没有被 `make defconfig` 静默丢弃；被排除的 6 个参考应用、qBittorrent/打印配套包及新增主题未被显式加入；默认主题仍为 Bootstrap。编译结果和硬件运行结果分别报告，不能相互替代。
