"""Huawei SmartHome Plus 补充集成。

不自行登录：复用原集成 ``huawei_smarthome`` 已登录账号的会话
（``entry.runtime_data.async_get_session()``），只在其之上提供
场景 / 房间 / 设备管理等原集成未收录的服务。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import CONF_HOST_ENTRY, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass
class PlusRuntime:
    """Plus 条目的运行时数据。"""

    host_entry_id: str


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry[PlusRuntime]") -> bool:
    """加载一个 Plus 条目。"""

    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = PlusRuntime(
        host_entry_id=str(entry.data[CONF_HOST_ENTRY]),
    )
    from .services import async_register_services

    await async_register_services(hass)
    return True


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry[PlusRuntime]") -> bool:
    """卸载一个 Plus 条目。"""

    return True


__all__ = ["DOMAIN", "PlusRuntime"]
