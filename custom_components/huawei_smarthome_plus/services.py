"""Huawei SmartHome Plus 服务。

16 个服务，分两组：
- 场景（Home Automation）11 个：list/create/update/delete/move_room/detail/
  run/enable/rename/logs/by_device
- 房间 / 设备管理 5 个：create_room/update_room/delete_room/
  transfer_devices/rename_device

凭证复用原集成 ``huawei_smarthome`` 已登录账号（``runtime_data.async_get_session()``），
Plus 自身不存储任何凭据。端点来源与验证状态见 README。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import SupportsResponse

from .api import scene_brief_to_entity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse

_LOGGER = logging.getLogger(__name__)

SERVICE_LIST_SCENES = "list_scenes"
SERVICE_CREATE_SCENE = "create_scene"
SERVICE_UPDATE_SCENE = "update_scene"
SERVICE_DELETE_SCENE = "delete_scene"
SERVICE_SCENE_MOVE_ROOM = "scene_move_room"
SERVICE_SCENE_DETAIL = "scene_detail"
SERVICE_RUN_SCENE = "run_scene"
SERVICE_SCENE_SET_ENABLED = "scene_set_enabled"
SERVICE_SCENE_RENAME = "scene_rename"
SERVICE_SCENE_LOGS = "scene_logs"
SERVICE_SCENES_BY_DEVICE = "scenes_by_device"

SERVICE_CREATE_ROOM = "create_room"
SERVICE_UPDATE_ROOM = "update_room"
SERVICE_DELETE_ROOM = "delete_room"
SERVICE_TRANSFER_DEVICES = "transfer_devices"
SERVICE_RENAME_DEVICE = "rename_device"

SCENE_SERVICES = (
    SERVICE_LIST_SCENES,
    SERVICE_CREATE_SCENE,
    SERVICE_UPDATE_SCENE,
    SERVICE_DELETE_SCENE,
    SERVICE_SCENE_MOVE_ROOM,
    SERVICE_SCENE_DETAIL,
    SERVICE_RUN_SCENE,
    SERVICE_SCENE_SET_ENABLED,
    SERVICE_SCENE_RENAME,
    SERVICE_SCENE_LOGS,
    SERVICE_SCENES_BY_DEVICE,
)

ALL_SERVICES = SCENE_SERVICES + (
    SERVICE_CREATE_ROOM,
    SERVICE_UPDATE_ROOM,
    SERVICE_DELETE_ROOM,
    SERVICE_TRANSFER_DEVICES,
    SERVICE_RENAME_DEVICE,
)


async def async_register_services(hass: "HomeAssistant") -> None:
    """注册服务（幂等，可重复调用）。"""

    if hass.services.has_service(DOMAIN, SERVICE_LIST_SCENES):
        return

    def _resolve_host(
        entry_id: str | None,
    ) -> tuple[Any | None, dict[str, Any] | None]:
        """取一个原集成条目的 client（runtime_data）。"""

        plus_entries = [
            item
            for item in hass.config_entries.async_loaded_entries(DOMAIN)
            if getattr(item, "runtime_data", None) is not None
        ]
        if entry_id:
            target = next((e for e in plus_entries if e.entry_id == entry_id), None)
        else:
            target = plus_entries[0] if plus_entries else None
        if target is None:
            return None, {"ok": False, "error": "没有可用的 Plus 配置条目"}
        host_id = target.runtime_data.host_entry_id
        host_entry = hass.config_entries.async_get_entry(host_id)
        client = getattr(host_entry, "runtime_data", None) if host_entry else None
        if client is None:
            return None, {
                "ok": False,
                "error": "原集成 huawei_smarthome 条目不可用（未加载或已删除）",
            }
        return client, None

    async def _get_session(client: Any) -> Any:
        """从原集成 client 取有效会话（兼容上游 / plus 两种 client 版本）。

        - plus 版本 client 提供 ``async_get_session()``（本分支上游 PR 已加）
        - 上游 master 版本无此方法，退回私有 ``_ensure_hms_session()``
        - 再退回到直接读 ``session`` 属性（可能已过期，由 API 层 401 兜底）
        """

        getter = getattr(client, "async_get_session", None)
        if callable(getter):
            return await getter()
        getter = getattr(client, "_ensure_hms_session", None)
        if callable(getter):
            return await getter()
        session = getattr(client, "session", None)
        if session is None:
            raise RuntimeError("原集成 client 未提供可用会话")
        return session

    async def _call_plus(
        call: "ServiceCall",
        action: str,
        invoke: Any,
    ) -> "ServiceResponse":
        """统一外壳：取原集成 client → 取会话 → 调 API → 兜住异常。"""

        from .api import (
            HuaweiSmartHomePlusApi,
            PlusAuthExpired,
            PlusPermissionDenied,
        )

        client, err = _resolve_host(call.data.get("entry_id"))
        if err:
            return err
        try:
            session = await _get_session(client)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("获取原集成会话失败: %s", exc)
            return {"ok": False, "action": action, "error": f"获取会话失败: {exc}"}
        try:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession

            plus_api = HuaweiSmartHomePlusApi(async_get_clientsession(hass))
            result = await invoke(plus_api, session)
        except PlusAuthExpired as exc:
            _LOGGER.error("会话已过期 %s: %s", action, exc)
            return {
                "ok": False,
                "action": action,
                "error": "会话已过期，请检查原集成登录状态",
            }
        except PlusPermissionDenied as exc:
            _LOGGER.error("权限不足 %s: %s", action, exc)
            return {"ok": False, "action": action, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("操作 %s 失败: %s", action, exc)
            return {"ok": False, "action": action, "error": str(exc)}
        return {"ok": True, "action": action, "result": result}

    # ------------------------------------------------------------------
    # 场景
    # ------------------------------------------------------------------
    async def _list_scenes(call: "ServiceCall") -> "ServiceResponse":
        async def invoke(api: Any, session: Any) -> Any:
            scenes = await api.async_list_scenes(
                session, need_check=bool(call.data.get("need_check", False))
            )
            items = [scene_brief_to_entity(item) for item in scenes]
            return {"count": len(items), "scenes": items}

        return await _call_plus(call, SERVICE_LIST_SCENES, invoke)

    async def _create_scene(call: "ServiceCall") -> "ServiceResponse":
        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_create_scene(
                session,
                title=call.data["title"],
                flow=call.data.get("flow"),
                scene_type=int(call.data.get("type", 1)),
                home_id=call.data.get("home_id"),
                description=call.data.get("description", ""),
                enabled=bool(call.data.get("enabled", True)),
                card_extra=call.data.get("card"),
            )

        return await _call_plus(call, SERVICE_CREATE_SCENE, invoke)

    async def _update_scene(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_update_scene(
                session,
                scenario_id,
                title=call.data.get("title"),
                flow=call.data.get("flow"),
                scene_type=call.data.get("type"),
                description=call.data.get("description"),
                enabled=call.data.get("enabled"),
                card_extra=call.data.get("card"),
            )

        return await _call_plus(call, SERVICE_UPDATE_SCENE, invoke)

    async def _delete_scene(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]
        _LOGGER.warning("收到 delete_scene 服务调用：将删除场景 %s", scenario_id)

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_delete_scene(session, scenario_id)

        return await _call_plus(call, SERVICE_DELETE_SCENE, invoke)

    async def _scene_move_room(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]
        room_id = call.data["room_id"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_move_scene_room(
                session, scenario_id, room_id, home_id=call.data.get("home_id")
            )

        return await _call_plus(call, SERVICE_SCENE_MOVE_ROOM, invoke)

    async def _scene_detail(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_get_scene_detail(session, scenario_id)

        return await _call_plus(call, SERVICE_SCENE_DETAIL, invoke)

    async def _run_scene(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]
        _LOGGER.warning("收到 run_scene 服务调用：将立即执行场景 %s", scenario_id)

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_run_scene(session, scenario_id)

        return await _call_plus(call, SERVICE_RUN_SCENE, invoke)

    async def _scene_set_enabled(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]
        enabled = bool(call.data["enabled"])

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_set_scene_enabled(session, scenario_id, enabled)

        response = await _call_plus(call, SERVICE_SCENE_SET_ENABLED, invoke)
        if response.get("ok"):
            response["enabled"] = enabled
        return response

    async def _scene_rename(call: "ServiceCall") -> "ServiceResponse":
        scenario_id = call.data["scenario_id"]
        title = call.data["title"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_rename_scene(session, scenario_id, title)

        return await _call_plus(call, SERVICE_SCENE_RENAME, invoke)

    async def _scene_logs(call: "ServiceCall") -> "ServiceResponse":
        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_get_scene_logs(
                session,
                cursor=call.data.get("cursor"),
                page_size=int(call.data.get("page_size", 20)),
                start_time=call.data.get("start_time"),
                end_time=call.data.get("end_time"),
            )

        return await _call_plus(call, SERVICE_SCENE_LOGS, invoke)

    async def _scenes_by_device(call: "ServiceCall") -> "ServiceResponse":
        device_id = call.data["device_id"]

        async def invoke(api: Any, session: Any) -> Any:
            scenes = await api.async_get_scenes_by_device(session, device_id)
            items = [scene_brief_to_entity(item) for item in scenes]
            return {"count": len(items), "scenes": items}

        return await _call_plus(call, SERVICE_SCENES_BY_DEVICE, invoke)

    # ------------------------------------------------------------------
    # 房间 / 设备管理
    # ------------------------------------------------------------------
    async def _create_room(call: "ServiceCall") -> "ServiceResponse":
        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_create_room(
                session,
                call.data["name"],
                home_id=call.data.get("home_id"),
                description=call.data.get("description", "default room"),
            )

        return await _call_plus(call, SERVICE_CREATE_ROOM, invoke)

    async def _update_room(call: "ServiceCall") -> "ServiceResponse":
        room_id = call.data["room_id"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_update_room(
                session,
                room_id,
                name=call.data["name"],
                home_id=call.data.get("home_id"),
                description=call.data.get("description", ""),
            )

        return await _call_plus(call, SERVICE_UPDATE_ROOM, invoke)

    async def _delete_room(call: "ServiceCall") -> "ServiceResponse":
        room_id = call.data["room_id"]
        _LOGGER.warning("收到 delete_room 服务调用：将删除房间 %s", room_id)

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_delete_room(
                session, room_id, home_id=call.data.get("home_id")
            )

        return await _call_plus(call, SERVICE_DELETE_ROOM, invoke)

    async def _transfer_devices(call: "ServiceCall") -> "ServiceResponse":
        device_ids = call.data["device_ids"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_transfer_devices(
                session,
                device_ids,
                room_id=str(call.data["room_id"]),
                home_id=call.data.get("home_id"),
            )

        return await _call_plus(call, SERVICE_TRANSFER_DEVICES, invoke)

    async def _rename_device(call: "ServiceCall") -> "ServiceResponse":
        dev_id = call.data["dev_id"]

        async def invoke(api: Any, session: Any) -> Any:
            return await api.async_rename_device(
                session,
                dev_id,
                call.data.get("alias", ""),
                home_id=call.data.get("home_id"),
            )

        return await _call_plus(call, SERVICE_RENAME_DEVICE, invoke)

    entry_field = {vol.Optional("entry_id"): str}
    scenario_id_field = {vol.Required("scenario_id"): str}

    registration = (
        (
            SERVICE_LIST_SCENES,
            _list_scenes,
            {**entry_field, vol.Optional("need_check"): bool},
        ),
        (
            SERVICE_CREATE_SCENE,
            _create_scene,
            {
                **entry_field,
                vol.Required("title"): str,
                vol.Optional("type", default=1): vol.All(
                    vol.Coerce(int), vol.In((0, 1, 3))
                ),
                vol.Optional("home_id"): str,
                vol.Optional("description"): str,
                vol.Optional("enabled", default=True): bool,
                vol.Optional("flow"): vol.Or(dict, list),
                vol.Optional("card"): dict,
            },
        ),
        (
            SERVICE_UPDATE_SCENE,
            _update_scene,
            {
                **entry_field,
                **scenario_id_field,
                vol.Optional("title"): str,
                vol.Optional("type"): vol.All(vol.Coerce(int), vol.In((0, 1, 3))),
                vol.Optional("description"): str,
                vol.Optional("enabled"): bool,
                vol.Optional("flow"): vol.Or(dict, list),
                vol.Optional("card"): dict,
            },
        ),
        (
            SERVICE_DELETE_SCENE,
            _delete_scene,
            {**entry_field, **scenario_id_field},
        ),
        (
            SERVICE_SCENE_MOVE_ROOM,
            _scene_move_room,
            {
                **entry_field,
                **scenario_id_field,
                vol.Required("room_id"): str,
                vol.Optional("home_id"): str,
            },
        ),
        (
            SERVICE_SCENE_DETAIL,
            _scene_detail,
            {**entry_field, **scenario_id_field},
        ),
        (
            SERVICE_RUN_SCENE,
            _run_scene,
            {**entry_field, **scenario_id_field},
        ),
        (
            SERVICE_SCENE_SET_ENABLED,
            _scene_set_enabled,
            {**entry_field, **scenario_id_field, vol.Required("enabled"): bool},
        ),
        (
            SERVICE_SCENE_RENAME,
            _scene_rename,
            {**entry_field, **scenario_id_field, vol.Required("title"): str},
        ),
        (
            SERVICE_SCENE_LOGS,
            _scene_logs,
            {
                **entry_field,
                vol.Optional("cursor"): str,
                vol.Optional("page_size", default=20): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
                vol.Optional("start_time"): str,
                vol.Optional("end_time"): str,
            },
        ),
        (
            SERVICE_SCENES_BY_DEVICE,
            _scenes_by_device,
            {**entry_field, vol.Required("device_id"): str},
        ),
        (
            SERVICE_CREATE_ROOM,
            _create_room,
            {
                **entry_field,
                vol.Required("name"): str,
                vol.Optional("home_id"): str,
                vol.Optional("description"): str,
            },
        ),
        (
            SERVICE_UPDATE_ROOM,
            _update_room,
            {
                **entry_field,
                vol.Required("room_id"): vol.Or(str, int),
                vol.Required("name"): str,
                vol.Optional("home_id"): str,
                vol.Optional("description"): str,
            },
        ),
        (
            SERVICE_DELETE_ROOM,
            _delete_room,
            {
                **entry_field,
                vol.Required("room_id"): vol.Or(str, int),
                vol.Optional("home_id"): str,
            },
        ),
        (
            SERVICE_TRANSFER_DEVICES,
            _transfer_devices,
            {
                **entry_field,
                vol.Required("device_ids"): [str],
                vol.Required("room_id"): vol.Or(str, int),
                vol.Optional("home_id"): str,
            },
        ),
        (
            SERVICE_RENAME_DEVICE,
            _rename_device,
            {
                **entry_field,
                vol.Required("dev_id"): str,
                vol.Optional("alias", default=""): str,
                vol.Optional("home_id"): str,
            },
        ),
    )

    for name, handler, schema in registration:
        hass.services.async_register(
            DOMAIN,
            name,
            handler,
            schema=vol.Schema(schema),
            supports_response=SupportsResponse.ONLY,
        )

    _LOGGER.debug("已注册 %d 个服务", len(ALL_SERVICES))
