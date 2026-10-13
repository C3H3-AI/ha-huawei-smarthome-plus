"""Huawei SmartHome Plus 配置流：选择一个已登录的原集成账号。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_HOST_ENTRY, DOMAIN, HOST_DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _host_entries(hass: "HomeAssistant") -> dict[str, str]:
    """列出原集成已配置条目：entry_id → 标题（账号）。"""

    return {
        entry.entry_id: entry.title or entry.entry_id
        for entry in hass.config_entries.async_entries(HOST_DOMAIN)
    }


class HuaweiSmartHomePlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """选择一个原集成账号作为凭证来源。"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """列出原集成条目供选择。"""

        hosts = await self.hass.async_add_executor_job(_host_entries, self.hass)
        if not hosts:
            return self.async_abort(reason="no_host_integration")
        if user_input is not None:
            host_id = user_input[CONF_HOST_ENTRY]
            await self.async_set_unique_id(host_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Plus · {hosts.get(host_id, host_id)}",
                data={CONF_HOST_ENTRY: host_id},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST_ENTRY): vol.In(hosts),
                }
            ),
        )
