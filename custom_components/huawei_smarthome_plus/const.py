"""Huawei SmartHome Plus 补充集成常量。"""

DOMAIN = "huawei_smarthome_plus"

# 依赖的原集成 domain（登录凭证来源）
HOST_DOMAIN = "huawei_smarthome"
CONF_HOST_ENTRY = "host_entry_id"

SMART_HOME_BASE_URL = "https://smarthome.hicloud.com"
SMART_HOME_IOS_APP_ID = "com.huawei.smarthome-ios"
SMART_HOME_USER_AGENT = "SmartHome/1.0.842 (iPhone; iOS 15.8.8; Scale/2.00)"

HOME_SNAPSHOT_PATH = "/smart-life/v5/homes"

# 场景（scenario-drcn，独立 host，需 x-uid）
SCENE_BASE_URL = "https://scenario-drcn.things.dbankcloud.cn"
SCENE_BASE_PATH = "/scenario-manager"
SCENE_LIST_PATH = f"{SCENE_BASE_PATH}/v3/scenarios"          # GET，App 当前主用
SCENE_CREATE_V2_PATH = f"{SCENE_BASE_PATH}/v2/scenarios"     # POST，创建场景（抓包验证）
SCENE_DETAIL_V2_PATH = f"{SCENE_BASE_PATH}/v2/scenarios/{{scenario_id}}"
SCENE_UPDATE_V2_PATH = f"{SCENE_BASE_PATH}/v2/scenarios/{{scenario_id}}"  # PUT
SCENE_DELETE_PATH = f"{SCENE_BASE_PATH}/v1/scenarios/{{scenario_id}}"     # DELETE
SCENE_ENABLED_PATH = f"{SCENE_BASE_PATH}/v1/scenarios/enabled"      # PUT
SCENE_ROOM_PATH = f"{SCENE_BASE_PATH}/v1/scenarios/room"            # PUT，移动到房间
SCENE_TITLE_PATH = f"{SCENE_BASE_PATH}/v1/scenarios/title"          # PUT
SCENE_LOGS_PATH = f"{SCENE_BASE_PATH}/v3/scenarios/logs"            # GET，执行日志
SCENE_RUN_EDGE_PATH = f"{SCENE_BASE_PATH}/v2/applications/{{flow_id}}/edge"  # POST，手动执行
SCENE_BY_DEVICE_PATH = f"{SCENE_BASE_PATH}/v3/scenariosByDeviceId"  # GET

# 房间/设备管理（主 App classes13/25.dex 反编译 + 抓包验证，域 = SMART_HOME_BASE_URL）
ROOM_CREATE_PATH = "/home-manager/v1/homes/{home_id}/rooms"           # POST，body {"rooms":[{name,description}]}
ROOM_UPDATE_PATH = "/userApp/v1.2.0/homes/{home_id}/rooms/{room_id}"  # PUT，body {name,description}
ROOM_DELETE_PATH = "/userApp/v1.2.0/homes/{home_id}/rooms/{room_id}"  # DELETE
DEVICE_TRANSFER_PATH = "/smart-life/v3/devices/transfer"              # PUT，设备移动到房间/家庭
DEVICE_ALIAS_PATH = "/smart-life/v3/device/alias/{dev_id}"            # POST，设备改名

SCENE_TYPE_LABELS: dict[int, str] = {
    0: "混合",
    1: "手动",
    2: "面板",
    3: "自动",
    4: "分隔线",
    5: "AIGC",
    7: "模拟点击",
    8: "房间折叠",
}
