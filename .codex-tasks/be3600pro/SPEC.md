# Xiaomi BE3600 Pro Wired firmware

- 用户要求：基于 VIKINGYFY/immortalwrt 建立公开仓库 yjy116/BE3600Pro，通过 GitHub Actions 编译 Xiaomi BE3600 Pro Wired。
- 插件基准：yjy116/Immortalwrt-CI-JDC-AX6600，提交 696912e6c18113c91cdb5fe1c079c456cbc78cf2。迁移已启用插件，不迁移京东云分区、NSS 或无线专用修改。
- 用户确认机型为 8 网口 p8；保留 raw owrt 默认包，以 AX6600 补充缺少应用。
- 用户明确移除独立 DAE，保留 DAED；不加入 Aurora/Argon，继续使用上游默认 Bootstrap 主题。网络默认值也不作迁移。
- 正确设备目标以当前上游源码审计为准，保留上游分区布局和设备镜像规则。
- 构建失败必须可见；核对 defconfig 和最终 manifest，不能把静默丢失插件当成功。
- 交付：仓库、构建脚本、插件清单与来源、完整构建日志、固件和校验和；记录实际构建状态。
- 不刷机。编译成功不能代表实机、PPE、eBPF 运行或外围接口验证。
