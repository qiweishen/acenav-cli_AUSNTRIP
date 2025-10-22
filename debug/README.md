# RTK调试工具和文档

## 目录结构

```
debug/
├── README.md              # 本文件
└── RTK_DEBUG_GUIDE.md     # 详细调试指南
```

## 快速开始

### 1. 运行带调试输出的测试

```bash
cd /home/qiwei/Desktop/acenav-cli
./test_rtk_debug.sh
```

或者直接运行：

```bash
python main.py -i 100base-t1
```

### 2. 观察调试输出

当NTRIP连接成功并接收RTCM数据时，您应该看到类似以下的输出：

```
NTRIP:[recv] rxdata 1024
[NTRIP DEBUG] Parsed 3 RTCM message(s), total 856 bytes, types: [1005, 1077, 1087]
[RTCM DEBUG] Received RTCM data from NTRIP: 856 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=878 bytes, rtcm_payload=856 bytes
```

### 3. 等待RTK收敛

- **SPP → RTK_FLOAT**: 1-5分钟
- **RTK_FLOAT → RTK_FIXED**: 5-20分钟（取决于条件）

## 已修改的文件

### 1. `src/aceinna/devices/ins401/ethernet_provider_base.py`

**修改内容**: 在 `handle_rtcm_data_parsed()` 函数中添加了调试输出

**新增功能**:
- 显示从NTRIP接收的RTCM数据大小
- 显示发送到设备的以太网包大小
- 警告通信器无法写入的情况

### 2. `src/aceinna/devices/widgets/ntrip_client.py`

**修改内容**: 在 `handle_parsed_data()` 函数中添加了RTCM消息解析和调试输出

**新增功能**:
- 显示解析的RTCM消息数量
- 显示RTCM消息类型（如1005, 1077, 1087等）
- 显示RTCM数据总字节数

## 代码更改摘要

### 更改1: RTCM数据接收和发送调试

```python
# 文件: src/aceinna/devices/ins401/ethernet_provider_base.py
# 函数: handle_rtcm_data_parsed()

# 新增调试输出
print(f'[RTCM DEBUG] Received RTCM data from NTRIP: {len(data)} bytes')

# 在发送前调试
print(f'[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size={len(command.actual_command)} bytes, rtcm_payload={len(data)} bytes')

# 警告信息
print('[RTCM WARNING] Communicator cannot write! RTCM data NOT sent to device.')
```

### 更改2: RTCM消息类型识别

```python
# 文件: src/aceinna/devices/widgets/ntrip_client.py
# 函数: handle_parsed_data()

# 解析RTCM消息类型
msg_types = []
for item in data:
    if len(item) >= 3 and item[0] == 0xD3:
        msg_type = ((item[3] & 0xFF) << 4) | ((item[4] >> 4) & 0x0F)
        msg_types.append(msg_type)

# 输出调试信息
print(f'[NTRIP DEBUG] Parsed {len(data)} RTCM message(s), total {len(combined_data)} bytes, types: {msg_types}')
```

## 问题诊断流程图

```
NTRIP连接成功
    ↓
是否看到 [NTRIP DEBUG] 输出？
    ↓ 是
RTCM数据正在接收
    ↓
是否看到 [RTCM DEBUG] 输出？
    ↓ 是
RTCM数据正在发送到设备
    ↓
是否看到 [RTCM WARNING]？
    ↓ 否
RTCM数据成功发送
    ↓
等待5-20分钟
    ↓
position_type是否变为RTK_FLOAT或RTK_FIXED？
    ↓ 否
可能是以下问题之一:
    1. 基站距离过远
    2. 设备固件问题
    3. RTCM消息类型不兼容
    4. 需要更长等待时间
```

## 验证RTCM数据发送成功的标志

✅ **成功标志**:
1. 看到 `[NTRIP DEBUG]` 消息，显示接收到RTCM数据
2. 看到 `[RTCM DEBUG]` 消息，显示数据已发送到设备
3. RTCM消息类型包含基站坐标（1005/1006）和观测值（1077/1074）
4. **没有**看到 `[RTCM WARNING]` 消息

❌ **失败标志**:
1. 看到 `[RTCM WARNING] Communicator cannot write!`
2. 看到 `[NTRIP DEBUG]` 但没有 `[RTCM DEBUG]`
3. 完全没有调试输出

## 下一步行动

### 如果RTCM数据成功发送但仍无RTK

1. **等待更长时间**（20-30分钟）
2. **检查基站距离**
   - 从日志提取GPS坐标
   - 计算与基站ADDE00AUS0的距离
   - RTK通常在50km内有效

3. **联系Aceinna技术支持**
   - 确认固件v28.06是否支持以太网RTCM输入
   - 确认消息类型 `0x02\x0b` 是否正确
   - 可能需要固件升级

### 如果RTCM数据未成功发送

1. **检查以太网连接**
2. **检查设备状态**
3. **查看完整日志**

## 相关资源

- **详细调试指南**: `debug/RTK_DEBUG_GUIDE.md`
- **测试脚本**: `test_rtk_debug.sh`
- **日志位置**: `data/ins401_log_YYYYMMDD_HHMMSS/`

## 技术细节

### RTCM消息格式

RTCM3消息格式：
```
Byte 0:    0xD3 (preamble)
Byte 1-2:  Message length (10 bits) + reserved (6 bits)
Byte 3-4:  Message type (12 bits) + ...
Byte N-3:  CRC24 (3 bytes)
```

### 以太网包封装

RTCM数据通过以太网发送时的封装：
```
Ethernet Header (14 bytes):
  - Destination MAC (6 bytes)
  - Source MAC (6 bytes)
  - EtherType (2 bytes)

Custom Protocol Header (~8 bytes):
  - Message type: 0x02 0x0b
  - Payload length
  - ...

RTCM Payload (variable):
  - 原始RTCM数据

CRC (2 bytes)
```

消息类型 `0x02\x0b` 表示"RTCM Base数据"。

## 常见问题

**Q: 为什么rtcm_rover文件这么大？**

A: `rtcm_rover_*.bin` 文件保存的是设备输出的rover端GNSS原始观测值，不是RTCM差分数据。这是正常的。

**Q: 如何知道设备是否真正使用了RTCM数据？**

A: 检查设备输出中的差分龄期（diffage）字段。如果该值不为0且逐渐增加，说明设备正在使用RTCM数据。

**Q: 调试输出会影响性能吗？**

A: 调试输出的性能影响很小（<1%），但会增加终端输出量。如果需要关闭，可以注释掉相关的 `print()` 语句。

## 版本信息

- **创建日期**: 2025-10-06
- **适用版本**: acenav-cli master分支
- **固件版本**: INS401 v28.06
- **Python版本**: 3.x

## 贡献

如果您发现问题或有改进建议，请提交Issue或Pull Request。
