# SPDX-License-Identifier: GPL-3.0-only
# Separate updater: keep the original upstream v2ray-geodata recipes.
include $(TOPDIR)/rules.mk

PKG_NAME:=v2ray-geodata-updater
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=GPL-3.0-only

include $(INCLUDE_DIR)/package.mk

define Package/v2ray-geodata-updater
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Checksum-verified V2Ray geodata updater
  DEPENDS:=+curl +ca-bundle +v2ray-geoip +v2ray-geosite
  PKGARCH:=all
endef

define Build/Compile
endef

define Package/v2ray-geodata-updater/install
	$(INSTALL_DIR) $(1)/bin $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/v2ray-geodata-updater $(1)/bin/
	$(INSTALL_BIN) ./files/99-geodata-updater $(1)/etc/uci-defaults/
endef

$(eval $(call BuildPackage,v2ray-geodata-updater))
