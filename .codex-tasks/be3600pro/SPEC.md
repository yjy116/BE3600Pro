# Xiaomi BE3600 Pro Wired firmware

- 用户要求：基于 VIKINGYFY/immortalwrt 建立公开仓库 yjy116/BE3600Pro，通过 GitHub Actions 编译 Xiaomi BE3600 Pro Wired。
- 插件基准：yjy116/Immortalwrt-CI-JDC-AX6600，提交 696912e6c18113c91cdb5fe1c079c456cbc78cf2。迁移已启用插件，不迁移京东云分区、NSS 或无线专用修改。
- 用户确认机型为 8 网口 p8；保留 raw owrt 默认包，以 AX6600 补充缺少应用。
- 核心用途：作为 AC 管理集客 AP。PoE 管理、中文界面、RTL837x 驱动及 Gecoos AC 前端/后端均为必需验收项。
- 2026-09-27 要求恢复源 CI 使用的 Aurora 主题及其设置插件，保留 Bootstrap 包，不加入 Argon。
- 最新要求覆盖此前独立 DAE 排除项：同步迁移 dae 与 daed 至 kenzok8/openwrt-daede，核验两者核心来源，由 luci-app-daede 统一管理并可切换；同一时间只能一个后端接管流量，重新编译验证。
- 用户最终指定新固件 LAN 默认地址为192.168.70.1/24；只改初始默认值，不强制覆写保留配置升级时的网络。
- 用户明确机身无 USB 接口，移除 USB 打印服务和专用依赖；已确认同时移除 qBittorrent、Samba、Mini Diskmanager、Partexp。原设备默认驱动保持不变。
- 用户明确排除 QModem 及附属应用：不引入其外源，不选择其软件包。
- 正确设备目标以当前上游源码审计为准，保留上游分区布局和设备镜像规则。
- 构建失败必须可见；核对 defconfig 和最终 manifest，不能把静默丢失插件当成功。
- 交付：仓库、构建脚本、插件清单与来源、完整构建日志、固件和校验和；记录实际构建状态。
- 不刷机。编译成功不能代表实机、PPE、eBPF 运行或外围接口验证。
