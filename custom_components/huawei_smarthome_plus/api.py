"""Huawei SmartHome Plus 云端 API（场景 / 房间 / 设备管理）。

自包含实现，仅通过 duck-typing 使用原集成的 AuthSession 对象
（只需 ``hms_access_token`` / ``user_id`` / ``base_url`` 三个属性），
不 import 原集成任何模块，因此对上游版本无侵入、无版本耦合。

端点来源：智慧生活 App 17.0.4.312 主体 classes23.dex（场景 NetworkService）
与 classes13/25.dex（房间/设备管理）反编译 + mitmproxy 抓包，全部经真实账号
实测通过（2026-10-13）。
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote, urlencode

from .const import (
    DEVICE_ALIAS_PATH,
    DEVICE_TRANSFER_PATH,
    HOME_SNAPSHOT_PATH,
    ROOM_CREATE_PATH,
    ROOM_DELETE_PATH,
    ROOM_UPDATE_PATH,
    SCENE_BASE_URL,
    SCENE_BY_DEVICE_PATH,
    SCENE_CREATE_V2_PATH,
    SCENE_DELETE_PATH,
    SCENE_DETAIL_V2_PATH,
    SCENE_ENABLED_PATH,
    SCENE_LIST_PATH,
    SCENE_LOGS_PATH,
    SCENE_ROOM_PATH,
    SCENE_RUN_EDGE_PATH,
    SCENE_TITLE_PATH,
    SCENE_UPDATE_V2_PATH,
    SCENE_TYPE_LABELS,
    SMART_HOME_IOS_APP_ID,
    SMART_HOME_USER_AGENT,
)


class PlusApiError(Exception):
    """Plus API 统一异常。"""


class PlusAuthExpired(PlusApiError):
    """会话过期。"""


class PlusPermissionDenied(PlusApiError):
    """403。"""


class PlusInvalidResponse(PlusApiError):
    """响应非法。"""


class HuaweiSmartHomePlusApi:
    """场景 / 房间 / 设备管理 API 客户端。"""

    def __init__(self, session: Any, *, timeout: float = 20.0) -> None:
        self._session = session  # aiohttp ClientSession
        self._timeout = timeout

    # ------------------------------------------------------------------
    # 场景（Home Automation，host = SCENE_BASE_URL，需 x-uid）
    # ------------------------------------------------------------------
    async def async_list_scenes(
        self, session: Any, *, need_check: bool = False
    ) -> tuple[Mapping[str, Any], ...]:
        """列出账号下全部场景（v3）。"""

        response = await self._request(
            session,
            SCENE_LIST_PATH,
            params={"needCheck": str(need_check).lower()},
            base_url=SCENE_BASE_URL,
        )
        return _as_mapping_tuple(scene_payload(self._json(response)))

    async def async_get_scene_detail(
        self, session: Any, scenario_id: str
    ) -> Mapping[str, Any]:
        """场景详情（触发器 / 条件 / 动作全量，v2）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        response = await self._request(
            session,
            SCENE_DETAIL_V2_PATH.format(scenario_id=quote(scenario_id, safe="")),
            base_url=SCENE_BASE_URL,
        )
        payload = scene_payload(self._json(response))
        return payload if isinstance(payload, Mapping) else {}

    async def async_get_scene_logs(
        self,
        session: Any,
        *,
        cursor: str | None = None,
        page_size: int = 20,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Mapping[str, Any]:
        """分页查询场景执行日志（startTime/endTime 必填毫秒，缺省最近 7 天）。"""

        params: dict[str, str] = {"pageSize": str(page_size)}
        if cursor:
            params["cursor"] = cursor
        now_ms = int(time.time() * 1000)
        params["startTime"] = start_time or str(now_ms - 7 * 86400_000)
        params["endTime"] = end_time or str(now_ms)
        response = await self._request(
            session, SCENE_LOGS_PATH, params=params, base_url=SCENE_BASE_URL
        )
        payload = scene_payload(self._json(response))
        return payload if isinstance(payload, Mapping) else {}

    async def async_get_scenes_by_device(
        self, session: Any, device_id: str
    ) -> tuple[Mapping[str, Any], ...]:
        """按设备 deviceId 查关联场景（响应列表在 scenarioCards 键内）。"""

        if not device_id:
            raise ValueError("device_id is required")
        response = await self._request(
            session,
            SCENE_BY_DEVICE_PATH,
            params={"deviceId": device_id},
            base_url=SCENE_BASE_URL,
        )
        return _as_mapping_tuple(scene_payload(self._json(response)))

    async def async_create_scene(
        self,
        session: Any,
        *,
        title: str,
        flow: Sequence[Any] | Mapping[str, Any] | None = None,
        scene_type: int = 1,
        home_id: str | None = None,
        description: str = "",
        enabled: bool = True,
        card_extra: Mapping[str, Any] | None = None,
        need_check: bool = True,
    ) -> Mapping[str, Any]:
        """创建场景（``POST /v2/scenarios``，抓包验证 2026-10-13）。"""

        if not title:
            raise ValueError("title is required")
        flows = _normalize_flow(flow)
        card: dict[str, Any] = {
            "author": "self",
            "backgroundColor": (
                "https://contentcenter-drcn.dbankcdn.com/pub_1/"
                "ActionContentService_UploadResource_100_1/74/v3/"
                "scenariocommonicon/default_logo_foregroundImg.png"
            ),
            "description": description or "",
            "enabled": bool(enabled),
            "foreground": "foreground.png",
            "isTemplate": False,
            "likeEnable": False,
            "logo": (
                "https://contentcenter-drcn.dbankcdn.com/pub_1/"
                "ActionContentService_UploadResource_100_1/74/v3/"
                "scenariocommonicon/default_logo.png"
            ),
            "logoDark": "default_logo_ld.png",
            "order": 1,
            "settings": {
                "analyzed": True,
                "disableOngoing": 0,
                "enableConfirm": 0,
                "isOldAiScene": False,
                "quickMenu": 0,
                "repeatInterval": 0,
                "repeatTimes": 1,
                "supportFormat": True,
            },
            "showFlag": "",
            "title": title,
            "tlpSource": 2,
            "type": int(scene_type),
            "version": "0.0.1",
        }
        if home_id:
            card["homeId"] = home_id
            card["settings"]["devicesBelongHomeId"] = home_id
        if card_extra:
            card.update(card_extra)
        detail = {
            "cardVersion": 0,
            "conflictCheck": False,
            "flow": flows,
            "needCheck": bool(need_check),
            "restoreEdit": False,
            "scenarioCard": card,
        }
        body = json.dumps(detail, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        response = await self._request(
            session,
            SCENE_CREATE_V2_PATH,
            method="POST",
            params={"selectOptimize": "false"},
            body=body,
            base_url=SCENE_BASE_URL,
            extra_headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        payload = scene_payload(self._json(response))
        if not isinstance(payload, Mapping):
            raise PlusInvalidResponse("scene create response is not an object")
        err = payload.get("errInfo")
        if isinstance(err, Mapping) and str(err.get("errorCode", "0")) != "0":
            raise PlusApiError(f"scene create rejected: {err}")
        return payload

    async def async_update_scene(
        self,
        session: Any,
        scenario_id: str,
        *,
        title: str | None = None,
        flow: Sequence[Any] | Mapping[str, Any] | None = None,
        scene_type: int | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        card_extra: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """修改场景（App ``updateV2``：先拉详情合并，再整体回传）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        detail = await self.async_get_scene_detail(session, scenario_id)
        if not isinstance(detail, Mapping) or not isinstance(
            detail.get("scenarioCard"), Mapping
        ):
            raise PlusInvalidResponse("scene detail is incomplete")
        card = dict(detail["scenarioCard"])
        if title is not None:
            card["title"] = title
        if description is not None:
            card["description"] = description
        if enabled is not None:
            card["enabled"] = bool(enabled)
        if scene_type is not None:
            card["type"] = int(scene_type)
        if card_extra:
            card.update(card_extra)
        flows = _normalize_flow(flow) if flow is not None else detail.get("flow", [])
        body_obj = {
            "cardVersion": detail.get("cardVersion", 2),
            "conflictCheck": False,
            "flow": flows,
            "needCheck": True,
            "restoreEdit": False,
            "scenarioCard": card,
        }
        body = json.dumps(
            body_obj, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        response = await self._request(
            session,
            SCENE_UPDATE_V2_PATH.format(scenario_id=quote(scenario_id, safe="")),
            method="PUT",
            params={"updateType": "", "selectOptimize": "false"},
            body=body,
            base_url=SCENE_BASE_URL,
            extra_headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        payload = scene_payload(self._json(response))
        if not isinstance(payload, Mapping):
            raise PlusInvalidResponse("scene update response is not an object")
        err = payload.get("errInfo")
        if isinstance(err, Mapping) and str(err.get("errorCode", "0")) != "0":
            raise PlusApiError(f"scene update rejected: {err}")
        return payload

    async def async_delete_scene(
        self, session: Any, scenario_id: str
    ) -> dict[str, Any]:
        """删除场景（``DELETE /v1/scenarios/{id}``）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        response = await self._request(
            session,
            SCENE_DELETE_PATH.format(scenario_id=quote(scenario_id, safe="")),
            method="DELETE",
            base_url=SCENE_BASE_URL,
        )
        text = response.body.decode("utf-8", errors="replace") if response.body else ""
        try:
            value = json.loads(text) if text else {}
        except (ValueError, TypeError):
            value = {}
        if isinstance(value, Mapping):
            code = value.get("code", value.get("status", 0))
            if code not in (0, "0", None, 200, "200"):
                raise PlusApiError(f"scene delete rejected: {str(value)[:200]}")
            err = value.get("errInfo")
            if isinstance(err, Mapping) and str(err.get("errorCode", "0")) != "0":
                raise PlusApiError(f"scene delete rejected: {err}")
        return {"deleted": scenario_id, "raw": value}

    async def async_move_scene_room(
        self,
        session: Any,
        scenario_id: str,
        room_id: str,
        *,
        home_id: str | None = None,
    ) -> Any:
        """把场景移动到房间（App ``moveSpace``；homeId 缺省从详情补全）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        if not room_id:
            raise ValueError("room_id is required")
        target_home = home_id
        if not target_home:
            detail = await self.async_get_scene_detail(session, scenario_id)
            card = detail.get("scenarioCard") if isinstance(detail, Mapping) else None
            if isinstance(card, Mapping):
                target_home = card.get("homeId")
        body = json.dumps(
            {
                "scenarioId": scenario_id,
                "roomId": room_id,
                "homeId": target_home or "",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            SCENE_ROOM_PATH,
            method="PUT",
            body=body,
            base_url=SCENE_BASE_URL,
        )
        return scene_payload(self._json(response))

    async def async_run_scene(self, session: Any, scenario_id: str) -> Any:
        """**手动执行**一次场景（抓包验证：detail 取 flow id → POST edge）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        detail = await self.async_get_scene_detail(session, scenario_id)
        flow_id = _extract_flow_id(detail)
        if not flow_id:
            raise PlusInvalidResponse("scene detail has no flow id")
        body = json.dumps(
            {
                "extension": {"scenarioId": scenario_id},
                "inputParameter": {
                    "method": "POST",
                    "path": "/run",
                    "body": {"eventType": "huawei.events.manualEvent"},
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            SCENE_RUN_EDGE_PATH.format(flow_id=quote(flow_id, safe="")),
            method="POST",
            body=body,
            base_url=SCENE_BASE_URL,
            extra_headers={
                "Content-Type": "application/json; charset=UTF-8",
                "x-edge-path": "run",
            },
        )
        return scene_payload(self._json(response))

    async def async_set_scene_enabled(
        self, session: Any, scenario_id: str, enabled: bool
    ) -> Any:
        """启用 / 禁用场景（手动场景 type=1 被服务端拒绝）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        body = json.dumps(
            {"scenarioId": scenario_id, "enabled": bool(enabled)},
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            SCENE_ENABLED_PATH,
            method="PUT",
            body=body,
            base_url=SCENE_BASE_URL,
        )
        return scene_payload(self._json(response))

    async def async_rename_scene(
        self, session: Any, scenario_id: str, title: str
    ) -> Any:
        """重命名场景（body 字段必须是 scenarioCardId）。"""

        if not scenario_id:
            raise ValueError("scenario_id is required")
        body = json.dumps(
            {"scenarioCardId": scenario_id, "title": title},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            SCENE_TITLE_PATH,
            method="PUT",
            body=body,
            base_url=SCENE_BASE_URL,
        )
        return scene_payload(self._json(response))

    # ------------------------------------------------------------------
    # 房间 / 设备管理（域 = 原集成默认 SMART_HOME 域）
    # ------------------------------------------------------------------
    async def _resolve_home_id(self, session: Any) -> str:
        """取账号首个家庭 home_id（GET /smart-life/v5/homes → houseInfos[0]）。"""

        response = await self._request(session, HOME_SNAPSHOT_PATH)
        value = self._json(response)
        house_infos = value.get("houseInfos") if isinstance(value, Mapping) else None
        if isinstance(house_infos, Sequence):
            for home in house_infos:
                if isinstance(home, Mapping) and home.get("homeId"):
                    return str(home["homeId"])
        raise PlusInvalidResponse("账号下没有家庭")

    async def async_create_room(
        self,
        session: Any,
        name: str,
        *,
        home_id: str | None = None,
        description: str = "default room",
    ) -> Any:
        """新建房间（``POST /home-manager/v1/homes/{id}/rooms``）。"""

        if not name:
            raise ValueError("name is required")
        hid = home_id or await self._resolve_home_id(session)
        body = json.dumps(
            {"rooms": [{"name": name, "description": description}]},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            ROOM_CREATE_PATH.format(home_id=quote(hid, safe="")),
            method="POST",
            body=body,
            extra_headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        return self._json(response)

    async def async_update_room(
        self,
        session: Any,
        room_id: str,
        *,
        name: str,
        home_id: str | None = None,
        description: str = "",
    ) -> Any:
        """改房间名（``PUT /userApp/v1.2.0/homes/{home}/rooms/{room}``）。"""

        if not room_id or not name:
            raise ValueError("room_id and name are required")
        hid = home_id or await self._resolve_home_id(session)
        body = json.dumps(
            {"name": name, "description": description},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            ROOM_UPDATE_PATH.format(
                home_id=quote(hid, safe=""), room_id=quote(str(room_id), safe="")
            ),
            method="PUT",
            body=body,
            extra_headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        return self._json(response)

    async def async_delete_room(
        self,
        session: Any,
        room_id: str,
        *,
        home_id: str | None = None,
    ) -> Any:
        """删除房间（房内有设备时服务端拒绝 100100010；成功响应体为空）。"""

        if not room_id:
            raise ValueError("room_id is required")
        hid = home_id or await self._resolve_home_id(session)
        response = await self._request(
            session,
            ROOM_DELETE_PATH.format(
                home_id=quote(hid, safe=""), room_id=quote(str(room_id), safe="")
            ),
            method="DELETE",
        )
        if not response.body:
            return {"deleted": str(room_id)}
        value = self._json(response)
        return value if isinstance(value, Mapping) else {"raw": value}

    async def async_transfer_devices(
        self,
        session: Any,
        device_ids: Sequence[str],
        *,
        room_id: str,
        home_id: str | None = None,
        from_home_id: str | None = None,
    ) -> Any:
        """移动设备到房间（``PUT /smart-life/v3/devices/transfer``）。"""

        devices = [d for d in device_ids if d]
        if not devices or not room_id:
            raise ValueError("device_ids and room_id are required")
        hid = home_id or await self._resolve_home_id(session)
        body = json.dumps(
            {
                "devIds": devices,
                "fromHomeId": from_home_id or hid,
                "toHomeId": hid,
                "toRoomId": str(room_id),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            DEVICE_TRANSFER_PATH,
            method="PUT",
            body=body,
            extra_headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        value = self._json(response)
        if isinstance(value, Mapping) and value.get("failedDevList"):
            raise PlusApiError(
                f"device transfer failed for: {value['failedDevList']}"
            )
        return value if isinstance(value, Mapping) else {"raw": value}

    async def async_rename_device(
        self,
        session: Any,
        dev_id: str,
        alias: str,
        *,
        home_id: str | None = None,
    ) -> Any:
        """设备改名（``POST /smart-life/v3/device/alias/{devId}``）。

        别名不含连字符（服务端 400 9999）；成功响应体为空。
        """

        if not dev_id:
            raise ValueError("dev_id is required")
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        if home_id:
            headers["X-HomeId"] = home_id
        body = json.dumps(
            {"aliasNames": [alias] if alias else []},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            session,
            DEVICE_ALIAS_PATH.format(dev_id=quote(dev_id, safe="")),
            method="POST",
            body=body,
            extra_headers=headers,
        )
        if not response.body:
            return {"dev_id": dev_id, "alias": alias or None}
        value = self._json(response)
        return value if isinstance(value, Mapping) else {"raw": value}

    # ------------------------------------------------------------------
    # 传输层
    # ------------------------------------------------------------------
    async def _request(
        self,
        session: Any,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        extra_headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        base_url: str | None = None,
    ) -> Any:
        token = getattr(session, "hms_access_token", None)
        if not token:
            raise PlusAuthExpired("HMS-lite access token is unavailable")
        user_id = getattr(session, "user_id", "") or ""
        origin = base_url or getattr(session, "base_url", None) or ""
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-Hans-CN;q=1",
            "Authorization": f"Bearer {token}",
            "X-AppId": SMART_HOME_IOS_APP_ID,
            "X-AppVersion": "17.0.3.320",
            "X-HomeId": "(null)",
            "X-Huid": user_id,
            "X-Language": "zh_CN",
            "X-Model": "iPhone",
            "X-Ori-App-Name": SMART_HOME_IOS_APP_ID,
            "X-PhoneOs": "iOS",
            "X-RequestId": str(uuid.uuid4()).upper(),
            "User-Agent": SMART_HOME_USER_AGENT,
        }
        if origin == SCENE_BASE_URL:
            # 场景服务要求 x-uid（缺则 401 errcode 1002，抓包验证）
            headers["x-uid"] = user_id
        if extra_headers:
            headers.update(extra_headers)
        if body is not None and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json;charset=UTF-8"
        import aiohttp

        url = f"{origin.rstrip('/')}{path}"
        query = urlencode(params) if params else ""
        if query:
            url = f"{url}?{query}"
        response: Any = None
        for attempt in range(3):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    data=body,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    response = _HttpResponse(
                        status=resp.status,
                        body=await resp.read(),
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as error:
                if attempt == 2:
                    raise PlusApiError("SmartHome HTTP transport failed") from error
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            if response.status in {500, 502, 503, 504} and attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            break
        assert response is not None
        if response.status == 401:
            raise PlusAuthExpired("SmartHome service session expired")
        if response.status == 403:
            raise PlusPermissionDenied(
                self._permission_message(response.body)
            )
        if response.status == 429:
            raise PlusApiError("SmartHome service rate limited the request")
        if response.status >= 400:
            raise PlusApiError(f"SmartHome HTTP status {response.status}")
        return response

    @staticmethod
    def _permission_message(body: bytes) -> str:
        """把 403 响应体里的 error_desc 拼进错误信息（如房内有设备不可删）。"""

        try:
            value = json.loads(body.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            return "SmartHome access denied"
        if isinstance(value, Mapping) and value.get("error_desc"):
            return f"SmartHome access denied: {value['error_desc']}"
        return "SmartHome access denied"

    @staticmethod
    def _json(response: Any) -> Any:
        try:
            value = json.loads(response.body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PlusInvalidResponse("SmartHome response is not JSON") from error
        error_code = _find_error_code(value)
        if error_code in {"200201", "400000021", "400000022", "400000023", "10004"}:
            raise PlusAuthExpired("SmartHome service session expired")
        return value


class _HttpResponse:
    """最小响应对象（aiohttp 读完 body 后的快照）。"""

    __slots__ = ("status", "body")

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body


# ----------------------------------------------------------------------
# 模块级辅助
# ----------------------------------------------------------------------
def _find_error_code(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    code = _direct_error_code(value)
    if code is not None:
        return code
    for key in ("error", "errorInfo", "error_info"):
        error = value.get(key)
        if isinstance(error, Mapping):
            code = _direct_error_code(error)
            if code is not None:
                return code
    return None


def _direct_error_code(value: Mapping[str, Any]) -> str | None:
    for key in ("error_code", "errorCode", "code"):
        candidate = value.get(key)
        if isinstance(candidate, (str, int)):
            return str(candidate)
    return None


def _normalize_flow(
    flow: Sequence[Any] | Mapping[str, Any] | None,
) -> list[Any]:
    """创建场景时把 flow 归一成 list；缺省给「点击卡片」手动触发空流程。"""

    if isinstance(flow, Mapping):
        return [dict(flow)]
    if isinstance(flow, Sequence) and not isinstance(flow, (str, bytes)):
        return list(flow)
    return [
        {
            "actions": [],
            "createTime": "2020-02-04 17:20:20",
            "title": "",
            "trigger": {
                "conditions": [],
                "eventLogic": "any",
                "events": [
                    {
                        "conditions": [],
                        "description": "$$hiscenario_json_manual_click_event##",
                        "enabled": True,
                        "eventId": str(uuid.uuid4()),
                        "eventType": "huawei.events.manualEvent",
                        "isHidden": False,
                        "permission": "string",
                        "tags": "string",
                        "title": "点击此场景卡片",
                        "version": "$latest",
                    }
                ],
            },
            "type": "manual",
            "version": "0.0.1",
        }
    ]


def _extract_flow_id(detail: Any) -> str | None:
    if not isinstance(detail, Mapping):
        return None
    flow = detail.get("flow")
    if not isinstance(flow, Sequence) or isinstance(flow, (str, bytes)):
        return None
    for item in flow:
        if isinstance(item, Mapping) and item.get("id"):
            return str(item["id"])
    return None


def scene_payload(value: Any) -> Any:
    """解开 /scenario-manager 的 Submit<T> 壳；status/code 非 0 抛错。"""

    if not isinstance(value, Mapping):
        return value
    status = value.get("status", value.get("code", 0))
    if status not in (0, "0", None, 200, "200"):
        raise PlusApiError(
            "SmartHome scene service returned status "
            f"{status}: {str(value.get('errorMsg') or value.get('message') or value)[:160]}"
        )
    for key in ("payload", "data"):
        if key in value:
            return value[key]
    return value


def _as_mapping_tuple(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        for key in ("scenarios", "list", "items", "scenarioCards"):
            inner = value.get(key)
            if isinstance(inner, Sequence) and not isinstance(inner, (str, bytes)):
                return tuple(item for item in inner if isinstance(item, Mapping))
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def scene_brief_to_entity(item: Mapping[str, Any]) -> dict[str, Any]:
    """压缩 ScenarioBrief 成服务响应用的精简结构。"""

    scene_type = item.get("type")
    return {
        "scenario_id": item.get("scenarioId") or item.get("scenarioCardId") or "",
        "title": item.get("title") or item.get("name") or "",
        "enabled": bool(item.get("status", item.get("enabled", False))),
        "type": scene_type,
        "type_label": SCENE_TYPE_LABELS.get(scene_type, "未知")
        if isinstance(scene_type, int)
        else "未知",
        "home_id": item.get("homeId") or "",
        "room_name": item.get("roomName") or "",
        "is_template": bool(item.get("isTemplate", False)),
    }
