# Huawei SmartHome Plus

华为智慧生活（HiLink / AI Life）的**补充集成**：提供原集成 [`huawei_smarthome`](https://github.com/xiasi0/ha-huawei-smarthome) 未收录的**场景 / 房间 / 设备管理服务**。

## 特性

- **不自行登录**：复用原集成已登录账号的会话（`entry.runtime_data.async_get_session()`），Plus 自身**不存储任何凭据**
- **零侵入**：不修改原集成任何文件，原集成可正常升级
- **纯服务**：不建实体、不做后台轮询，只在你调用 `huawei_smarthome_plus.xxx` 服务时才发请求
- 端点全部经抓包 + 真机实测（2026-10-13，16/16 通过）

## 安装

1. 先安装并登录 [`huawei_smarthome`](https://github.com/xiasi0/ha-huawei-smarthome)
2. 通过 HACS 自定义仓库安装本集成（域名 `integration`），或手动把 `custom_components/huawei_smarthome_plus` 拷贝进 `config/custom_components/`
3. 重启 HA → 设置 → 设备与服务 → 添加集成 → **Huawei SmartHome Plus** → 选择一个已登录账号

## 服务（16 个）

服务命名空间：`huawei_smarthome_plus.*`；`entry_id` 可留空（自动取第一个条目）。

### 场景（11 个）

| 服务 | 说明 | 验证 |
| --- | --- | --- |
| `list_scenes` | 列出账号下全部场景 | 实测 |
| `create_scene` | 创建场景（需带完整 `flow`，空 flow 会被服务端拒 3008） | 实测 |
| `update_scene` | 修改场景（先拉详情合并再整体回传，同 App 编辑保存） | 实测 |
| `delete_scene` | 永久删除场景（不可恢复） | 实测 |
| `scene_move_room` | 场景移动到房间 | 实测 |
| `scene_detail` | 场景触发器/条件/动作全量详情 | 实测 |
| `run_scene` | 立即执行场景 | 实测 |
| `scene_set_enabled` | 启用/禁用场景（手动场景服务端拒绝） | 实测 |
| `scene_rename` | 重命名场景 | 实测 |
| `scene_logs` | 分页查询执行日志 | 实测 |
| `scenes_by_device` | 按设备 deviceId 查关联场景 | 实测 |

### 房间 / 设备管理（5 个）

| 服务 | 说明 | 验证 |
| --- | --- | --- |
| `create_room` | 新建房间（房内不可重名，单家庭上限 64 间，名称 ≤100 字符） | 实测 |
| `update_room` | 重命名房间 | 实测 |
| `delete_room` | 删除房间（房内有设备时服务端拒绝 100100010） | 实测 |
| `transfer_devices` | 设备移动到房间（目标为「未选择房间」时拒绝 100240024） | 实测 |
| `rename_device` | 修改设备别名（禁止连字符，清空传 `alias: ""`） | 实测 |

## 端点来源

| 域 | 端点 | 来源 |
| --- | --- | --- |
| `scenario-drcn.things.dbankcloud.cn` | 场景全集 | 智慧生活 App `classes23.dex` 反编译 + mitmproxy 抓包 |
| `smarthome.dbankcloud.cn` | 房间 / 设备管理 | 主 APK `classes13/25.dex` jadx 反编译 + 抓包 |

请求头：`Authorization: Bearer {HMS access token}`，场景域额外注入 `x-uid`。

## License

MIT
