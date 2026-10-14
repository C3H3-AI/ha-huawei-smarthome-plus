# Huawei SmartHome Plus

华为智慧生活（HiLink / AI Life）的**补充集成**：提供原集成 [`huawei_smarthome`](https://github.com/xiasi0/ha-huawei-smarthome) 未收录的**场景 / 房间 / 设备管理服务**。

## 特性

- **不自行登录**：复用原集成已登录账号的会话（`entry.runtime_data.async_get_session()`），Plus 自身**不存储任何凭据**
- **零侵入**：不修改原集成任何文件，原集成可正常升级
- **纯服务**：不建实体、不做后台轮询，只在你调用 `huawei_smarthome_plus.xxx` 服务时才发请求
- 20 个服务全部真机实测通过

## 安装

1. 先安装并登录 [`huawei_smarthome`](https://github.com/xiasi0/ha-huawei-smarthome)
2. 通过 HACS 自定义仓库安装本集成（域名 `integration`），或手动把 `custom_components/huawei_smarthome_plus` 拷贝进 `config/custom_components/`
3. 重启 HA → 设置 → 设备与服务 → 添加集成 → **Huawei SmartHome Plus** → 选择一个已登录账号

## 服务（20 个）

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

### 房间 / 设备管理（9 个）

| 服务 | 说明 | 验证 |
| --- | --- | --- |
| `create_room` | 新建房间（房内不可重名，单家庭上限 64 间，名称 ≤100 字符） | 实测 |
| `update_room` | 重命名房间 | 实测 |
| `delete_room` | 删除房间（房内有设备时服务端拒绝 100100010） | 实测 |
| `list_rooms` | 列出家庭下房间（含 roomId、楼层、设备数） | 实测 |
| `list_devices` | 列出家庭下设备（含 devId、型号、类型、所属房间）；此接口为设备静态档案，`online` 不代表实时在线状态 | 实测 |
| `transfer_devices` | 设备移动到房间（目标为「未选择房间」时拒绝 100240024） | 实测 |
| `rename_device` | 修改设备别名（禁止连字符，清空传 `alias: ""`） | 实测 |
| `delete_device` | 从家庭解绑设备（`DELETE /smart-life/v2/devices/{devId}?homeId=`，网关可设 `associate`，不可恢复） | 实测 |
| `set_room_floors` | 批量设置房间楼层；服务端为全量覆盖语义，默认先拉取现有楼层再合并提交，只传要改的房间也不会清空其他房间 | 实测 |

## License

MIT
