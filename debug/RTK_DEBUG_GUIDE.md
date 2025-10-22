# RTK调试指南

## 概述

本文档说明如何使用新增的调试功能来诊断RTK定位问题。

## 已添加的调试功能

### 1. NTRIP客户端调试输出

**位置**: `src/aceinna/devices/widgets/ntrip_client.py:206`

**输出格式**:
```
[NTRIP DEBUG] Parsed N RTCM message(s), total XXX bytes, types: [1005, 1077, 1087, ...]
```

**说明**:
- `N` - 本次解析的RTCM消息数量
- `XXX bytes` - RTCM数据总字节数
- `types` - RTCM消息类型列表

**常见RTCM消息类型**:
- `1005` - 基站坐标（静态）
- `1006` - 基站坐标（动态）
- `1074` - GPS MSM4观测数据
- `1077` - GPS MSM7观测数据（高精度）
- `1084` - GLONASS MSM4观测数据
- `1087` - GLONASS MSM7观测数据
- `1094` - Galileo MSM4观测数据
- `1097` - Galileo MSM7观测数据
- `1124` - BeiDou MSM4观测数据
- `1127` - BeiDou MSM7观测数据

### 2. RTCM数据处理调试输出

**位置**: `src/aceinna/devices/ins401/ethernet_provider_base.py:253-268`

**输出格式**:
```
[RTCM DEBUG] Received RTCM data from NTRIP: XXX bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=YYY bytes, rtcm_payload=XXX bytes
```

**说明**:
- `XXX bytes` - 从NTRIP接收的RTCM原始数据大小
- `YYY bytes` - 封装成以太网包后的总大小（包含以太网头部）

**警告信息**:
```
[RTCM WARNING] Communicator cannot write! RTCM data NOT sent to device.
```
如果看到此警告，说明以太网通信器未就绪，RTCM数据无法发送到设备。

## 使用方法

### 方法1: 使用测试脚本

```bash
./test_rtk_debug.sh
```

### 方法2: 直接运行

```bash
conda activate acenav_cli
python main.py -i 100base-t1
```

## 预期输出示例

正常工作时的输出应该类似：

```
NTRIP:[connect] ntrip.data.gnss.ga.gov.au:443 (SSL/TLS) start...
NTRIP:[connect] SSL/TLS handshake completed
NTRIP:[connect] ok
NTRIP:[request] ok
NTRIP:[recv] rxdata 1024
[NTRIP DEBUG] Parsed 3 RTCM message(s), total 856 bytes, types: [1005, 1077, 1087]
[RTCM DEBUG] Received RTCM data from NTRIP: 856 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=878 bytes, rtcm_payload=856 bytes
NTRIP:[recv] rxdata 407
[NTRIP DEBUG] Parsed 2 RTCM message(s), total 395 bytes, types: [1097, 1127]
[RTCM DEBUG] Received RTCM data from NTRIP: 395 bytes
[RTCM DEBUG] Sending RTCM to device via Ethernet: packet_size=417 bytes, rtcm_payload=395 bytes
```

## 诊断问题

### 问题1: 没有看到 `[NTRIP DEBUG]` 输出

**可能原因**:
- NTRIP连接失败
- RTCM解析器未能正确解析数据

**解决方法**:
- 检查NTRIP服务器连接状态
- 检查日志文件中是否有 `NTRIP:[recv] rxdata` 消息

### 问题2: 看到 `[NTRIP DEBUG]` 但没有 `[RTCM DEBUG]`

**可能原因**:
- NTRIP客户端的事件监听器未正确连接
- `handle_rtcm_data_parsed` 函数未被调用

**解决方法**:
- 检查 `ntrip_client.on('parsed', self.handle_rtcm_data_parsed)` 是否正确设置

### 问题3: 看到 `[RTCM WARNING]` 消息

**可能原因**:
- 以太网通信器未初始化
- 设备断开连接

**解决方法**:
- 检查设备连接状态
- 重启程序

### 问题4: RTCM数据正常发送但position_type仍为SPP

**可能原因**:
1. **基站距离过远** (>50km)
   - 检查日志中的GPS位置，计算与基站的距离

2. **需要等待更长时间**
   - SPP → RTK_FLOAT: 通常需要1-5分钟
   - RTK_FLOAT → RTK_FIXED: 可能需要5-20分钟

3. **设备固件问题**
   - 固件v28.06可能有bug
   - 可能需要固件升级

4. **RTCM消息类型不兼容**
   - 检查 `types` 列表，应包含:
     - 1005或1006（基站坐标）
     - 1077或1074（GPS观测值）
     - 1087或1084（GLONASS观测值，可选）

5. **设备未真正接收RTCM数据**
   - 虽然代码发送了，但设备固件可能未正确处理
   - 需要联系Aceinna技术支持确认消息类型 `0x02\x0b` 是否正确

## 收集诊断信息

如果问题仍未解决，请收集以下信息提供给技术支持：

1. **完整的调试输出**（运行5-10分钟）
2. **日志文件**:
   - `data/ins401_log_XXXXXX/rtcm_base_*.bin`（前10KB）
   - `data/ins401_log_XXXXXX/configuration.json`
3. **RTCM消息类型列表**（从调试输出中提取）
4. **GPS位置信息**（从 `$GNGGA` 消息中提取）
5. **基站信息**:
   - 基站名称: ADDE00AUS0
   - 基站服务器: ntrip.data.gnss.ga.gov.au

## RTCM消息分析工具

### 查看接收到的RTCM消息类型

```bash
python3 << 'EOF'
import struct

rtcm_file = 'data/ins401_log_XXXXXX/rtcm_base_*.bin'  # 替换为实际文件
with open(rtcm_file, 'rb') as f:
    data = f.read()

msg_types = {}
pos = 0
while pos < len(data) - 6:
    if data[pos] == 0xD3:
        # RTCM3 message
        msg_type = ((data[pos+3] & 0xFF) << 4) | ((data[pos+4] >> 4) & 0x0F)
        msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        # Skip to next message
        msg_len = ((data[pos+1] & 0x03) << 8) | data[pos+2]
        pos += msg_len + 6
    else:
        pos += 1

print("RTCM消息统计:")
for msg_type, count in sorted(msg_types.items()):
    print(f"  Type {msg_type}: {count} messages")
EOF
```

## 联系支持

如果以上方法都无法解决问题，请联系：
- Aceinna技术支持
- 提供Issue: https://github.com/Aceinna/acenav-cli/issues

确保提供完整的调试输出和诊断信息。
