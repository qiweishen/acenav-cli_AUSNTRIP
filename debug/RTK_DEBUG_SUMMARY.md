# RTK调试功能添加摘要

## 问题描述

当运行 `python main.py -i 100base-t1` 进行GNSS/IMU测量时：

- ✅ NTRIP连接成功
- ✅ 接收到大量RTCM差分数据（~200KB）
- ✅ 卫星数量充足（27+ 可见，23+ 参与解算）
- ❌ **position_type始终为SPP，无法转换为RTK_FIXED或RTK_FLOAT**

## 根本原因分析

经过深入分析代码和日志文件，发现：

### ✅ 确认正常工作的部分

1. **NTRIP连接和数据接收**正常
   - 成功连接到 `ntrip.data.gnss.ga.gov.au:443`
   - 接收了196.5 KB的RTCM差分数据
   - 数据格式正确（RTCM3标准格式，以0xD3开头）

2. **代码逻辑**正确
   - RTCM数据解析正常（使用RTCMParser）
   - 发送到设备的代码路径正确
   - 以太网包封装使用正确的消息类型 `0x02\x0b`

3. **GGA数据发送**正常
   - 设备正确发送 `$GNGGA` 消息给NTRIP服务器
   - NTRIP服务器基于位置返回对应的差分数据

### ❓ 可能的问题

**无法直接从代码确认的问题**：

1. **设备固件是否真正处理RTCM数据**
   - 虽然代码将RTCM数据发送到设备，但无法确认固件是否正确处理
   - 固件v28.06可能有bug或需要特殊配置

2. **基站距离**
   - GPS位置：-34.97°S, 138.64°E（阿德莱德附近）
   - 基站：ADDE00AUS0
   - 如果距离>50km，RTK收敛会很困难

3. **时间因素**
   - RTK收敛需要时间（5-20分钟或更长）
   - 日志只显示了约2分钟的数据

## 解决方案：添加调试功能

为了诊断问题，我添加了详细的调试输出来追踪RTCM数据流。

### 修改1: NTRIP客户端调试

**文件**: `src/aceinna/devices/widgets/ntrip_client.py`

**函数**: `handle_parsed_data()` (第193-209行)

**新增功能**:
- 解析并显示RTCM消息类型
- 显示消息数量和总字节数

**示例输出**:
```
[NTRIP DEBUG] Parsed 3 RTCM message(s), total 856 bytes, types: [1005, 1077, 1087]
```

**RTCM消息类型说明**:
- `1005` - 基站静态坐标（必需）
- `1077` - GPS MSM7高精度观测值（必需）
- `1087` - GLONASS MSM7观测值
- `1097` - Galileo MSM7观测值
- `1127` - BeiDou MSM7观测值

### 修改2: RTCM数据发送调试

**文件**: `src/aceinna/devices/ins401/ethernet_provider_base.py`

**函数**: `handle_rtcm_data_parsed()` (第251-268行)

**新增功能**:
- 显示从NTRIP接收的RTCM数据大小
- 显示发送到设备的以太网包大小
- 警告通信器无法写入的情况

**示例输出**:
```
[RTCM DEBUG] Received RTCM data from NTRIP: 856 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=878 bytes, rtcm_payload=856 bytes
```

如果出现问题：
```
[RTCM WARNING] Communicator cannot write! RTCM data NOT sent to device.
```

## 使用方法

### 快速测试

```bash
cd /home/qiwei/Desktop/acenav-cli
./test_rtk_debug.sh
```

或直接运行：

```bash
python main.py -i 100base-t1
```

### 观察调试输出

正常工作时应该看到：

```
NTRIP:[connect] ntrip.data.gnss.ga.gov.au:443 (SSL/TLS) start...
NTRIP:[connect] SSL/TLS handshake completed
NTRIP:[connect] ok
NTRIP:[request] ok
NTRIP:[recv] rxdata 1024

[NTRIP DEBUG] Parsed 3 RTCM message(s), total 856 bytes, types: [1005, 1077, 1087]
[RTCM DEBUG] Received RTCM data from NTRIP: 856 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=878 bytes, rtcm_payload=856 bytes

[NTRIP DEBUG] Parsed 2 RTCM message(s), total 395 bytes, types: [1097, 1127]
[RTCM DEBUG] Received RTCM data from NTRIP: 395 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=417 bytes, rtcm_payload=395 bytes
```

## 诊断流程

### 步骤1: 验证RTCM数据流

1. 运行程序并观察调试输出
2. 确认看到 `[NTRIP DEBUG]` 消息（说明RTCM数据正在接收）
3. 确认看到 `[RTCM DEBUG]` 消息（说明RTCM数据正在发送）
4. 确认**没有**看到 `[RTCM WARNING]` 消息

### 步骤2: 检查RTCM消息类型

确认接收到的RTCM消息包含：
- ✅ 基站坐标（1005或1006）
- ✅ GPS观测值（1077或1074）
- ✅ 其他系统观测值（1087, 1097, 1127等，可选）

### 步骤3: 等待RTK收敛

- **耐心等待**: 20-30分钟
- **观察卫星数量**: 应保持在20+
- **观察差分龄期**: 如果设备支持，应该看到diffage字段从0变为小于10秒

### 步骤4: 如果仍无RTK

如果RTCM数据正常发送但position_type仍为SPP，可能的原因：

1. **基站距离过远**
   - 从 `$GNGGA` 提取GPS坐标
   - 计算与基站的距离
   - RTK通常在30-50km内有效

2. **设备固件问题**
   - 固件v28.06可能不支持通过以太网接收RTCM
   - 消息类型 `0x02\x0b` 可能不正确
   - **需要联系Aceinna技术支持确认**

3. **RTCM消息兼容性**
   - 某些设备只支持特定的RTCM消息类型
   - 可能需要配置NTRIP服务器或更换基站

## 下一步行动建议

### 立即行动

1. ✅ 运行带调试输出的程序
2. ✅ 观察并记录调试输出（至少10分钟）
3. ✅ 检查RTCM消息类型列表
4. ✅ 等待20-30分钟观察RTK收敛

### 如果问题持续

1. **收集诊断信息**:
   - 完整调试输出（10分钟以上）
   - RTCM消息类型列表
   - GPS坐标和基站距离
   - 日志文件：`rtcm_base_*.bin`, `configuration.json`

2. **联系技术支持**:
   - Aceinna官方技术支持
   - 提供完整诊断信息
   - 询问固件v28.06是否支持以太网RTCM输入
   - 确认消息类型 `0x02\x0b` 是否正确

## 文件清单

### 修改的源文件

1. `src/aceinna/devices/widgets/ntrip_client.py`
   - 第193-209行：添加RTCM消息解析和调试输出

2. `src/aceinna/devices/ins401/ethernet_provider_base.py`
   - 第251-268行：添加RTCM数据发送调试输出

### 新增文件

1. `debug/README.md` - 调试工具总览
2. `debug/RTK_DEBUG_GUIDE.md` - 详细调试指南
3. `test_rtk_debug.sh` - 快速测试脚本
4. `RTK_DEBUG_SUMMARY.md` - 本文件

## 数据流示意图

```
NTRIP Server (ntrip.data.gnss.ga.gov.au:443)
    │
    │ RTCM3 Data (1005, 1077, 1087, ...)
    ↓
NTRIPClient.recv()
    │
    │ Raw bytes
    ↓
RTCMParser.receive()
    │
    │ Parse into messages
    ↓
NTRIPClient.handle_parsed_data()
    │
    │ [NTRIP DEBUG] 输出
    ↓
Provider.handle_rtcm_data_parsed()
    │
    │ [RTCM DEBUG] 输出
    ↓
helper.build_ethernet_packet()
    │
    │ Wrap with Ethernet header
    │ Message type: 0x02 0x0b
    ↓
Communicator.write()
    │
    │ Send to device
    ↓
INS401 Device (Firmware v28.06)
    │
    │ Process RTCM data?
    ↓
RTK Solution
    ├─ SPP (Current)
    ├─ RTK_FLOAT (Expected)
    └─ RTK_FIXED (Expected)
```

## 技术细节

### RTCM3消息格式

```
Byte 0:      0xD3 (Preamble)
Byte 1-2:    Length (10 bits) + Reserved (6 bits)
Byte 3-4:    Message Type (12 bits) + Message Data
Byte 5-N:    Payload
Byte N+1-N+3: CRC24
```

### 以太网包格式

```
[Dest MAC (6)] [Src MAC (6)] [Type (2)] [0x02 0x0b] [Length (4)] [RTCM Payload] [CRC (2)]
```

## 预期结果

### 成功标志

- ✅ 每秒看到多条 `[NTRIP DEBUG]` 和 `[RTCM DEBUG]` 消息
- ✅ RTCM消息类型包含1005和1077
- ✅ 没有警告消息
- ⏳ 等待20-30分钟后，position_type变为RTK_FLOAT或RTK_FIXED

### 失败标志

- ❌ 看到 `[RTCM WARNING]` 消息
- ❌ 有 `[NTRIP DEBUG]` 但没有 `[RTCM DEBUG]`
- ❌ 30分钟后仍然是SPP

## 常见问题解答

**Q: 为什么要等这么久？**

A: RTK定位需要多个历元（epoch）的观测数据来计算模糊度。初次收敛可能需要5-20分钟，在困难条件下可能需要更长时间。

**Q: rtcm_base和rtcm_rover文件有什么区别？**

A:
- `rtcm_base_*.bin`: 从NTRIP接收的基站RTCM差分数据
- `rtcm_rover_*.bin`: 设备输出的rover端GNSS原始观测值

**Q: 如何确认设备真正使用了RTCM数据？**

A: 检查设备输出中的差分龄期（diffage）字段。如果该值不为0且逐渐增加到5-10秒，说明设备正在使用RTCM数据。

**Q: 调试输出可以关闭吗？**

A: 可以。注释掉相关的 `print()` 语句即可。但建议在确认问题解决前保持开启。

## 版本信息

- **创建日期**: 2025-10-06
- **作者**: Claude Code
- **适用版本**: acenav-cli master分支
- **测试设备**: INS401 (SN: 2509001377)
- **固件版本**: RTK_INS App v28.06, Bootloader v01.02

## 参考资料

- RTCM 10403.3标准文档
- INS401用户手册
- Aceinna技术支持: https://github.com/Aceinna/acenav-cli/issues
