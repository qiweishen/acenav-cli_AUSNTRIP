#!/usr/bin/env python3
"""
RTCM日志文件分析工具
分析rtcm_base_*.bin文件，统计RTCM消息类型
"""

import sys
import struct
from pathlib import Path
from collections import Counter


def parse_rtcm_messages(file_path):
    """解析RTCM消息并返回消息类型统计"""
    with open(file_path, 'rb') as f:
        data = f.read()

    msg_stats = Counter()
    msg_sizes = {}
    pos = 0
    total_messages = 0

    while pos < len(data) - 6:
        if data[pos] == 0xD3:  # RTCM preamble
            try:
                # Parse message length (10 bits)
                msg_len = ((data[pos+1] & 0x03) << 8) | data[pos+2]

                # Parse message type (12 bits)
                msg_type = ((data[pos+3] & 0xFF) << 4) | ((data[pos+4] >> 4) & 0x0F)

                # Total packet size: 3 (header) + msg_len + 3 (CRC)
                total_size = 3 + msg_len + 3

                # Verify we have enough data
                if pos + total_size <= len(data):
                    msg_stats[msg_type] += 1
                    if msg_type not in msg_sizes:
                        msg_sizes[msg_type] = []
                    msg_sizes[msg_type].append(total_size)
                    total_messages += 1
                    pos += total_size
                else:
                    pos += 1
            except:
                pos += 1
        else:
            pos += 1

    return msg_stats, msg_sizes, total_messages


def get_message_description(msg_type):
    """获取RTCM消息类型描述"""
    descriptions = {
        1001: "GPS L1-Only RTK Observables",
        1002: "GPS Extended L1-Only RTK Observables",
        1003: "GPS L1/L2 RTK Observables",
        1004: "GPS Extended L1/L2 RTK Observables",
        1005: "Stationary RTK Reference Station ARP",
        1006: "Stationary RTK Reference Station ARP with Height",
        1007: "Antenna Descriptor",
        1008: "Antenna Descriptor & Serial Number",
        1009: "GLONASS L1-Only RTK Observables",
        1010: "GLONASS Extended L1-Only RTK Observables",
        1011: "GLONASS L1/L2 RTK Observables",
        1012: "GLONASS Extended L1/L2 RTK Observables",
        1013: "System Parameters",
        1019: "GPS Ephemerides",
        1020: "GLONASS Ephemerides",
        1033: "Receiver and Antenna Descriptors",
        1042: "BDS Ephemeris Data",
        1044: "QZSS Ephemerides",
        1045: "Galileo F/NAV Satellite Ephemeris Data",
        1046: "Galileo I/NAV Satellite Ephemeris Data",
        1074: "GPS MSM4 (Multiple Signal Messages)",
        1075: "GPS MSM5",
        1076: "GPS MSM6",
        1077: "GPS MSM7 (High precision)",
        1084: "GLONASS MSM4",
        1085: "GLONASS MSM5",
        1086: "GLONASS MSM6",
        1087: "GLONASS MSM7 (High precision)",
        1094: "Galileo MSM4",
        1095: "Galileo MSM5",
        1096: "Galileo MSM6",
        1097: "Galileo MSM7 (High precision)",
        1124: "BeiDou MSM4",
        1125: "BeiDou MSM5",
        1126: "BeiDou MSM6",
        1127: "BeiDou MSM7 (High precision)",
        1230: "GLONASS Code-Phase Biases",
    }
    return descriptions.get(msg_type, "Unknown")


def analyze_file(file_path):
    """分析RTCM文件"""
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return

    file_size = file_path.stat().st_size

    print("="*80)
    print(f"RTCM日志文件分析")
    print("="*80)
    print(f"文件: {file_path.name}")
    print(f"大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print("="*80)
    print()

    msg_stats, msg_sizes, total_messages = parse_rtcm_messages(file_path)

    if total_messages == 0:
        print("警告: 未找到任何有效的RTCM消息！")
        print("可能原因：")
        print("  - 文件格式不正确")
        print("  - 文件已损坏")
        print("  - 不是RTCM3格式")
        return

    print(f"总共解析到 {total_messages} 条RTCM消息")
    print()

    # Check for critical messages
    has_1005 = 1005 in msg_stats or 1006 in msg_stats
    has_obs = any(t in msg_stats for t in [1074, 1075, 1076, 1077, 1084, 1085, 1086, 1087,
                                             1094, 1095, 1096, 1097, 1124, 1125, 1126, 1127])

    print("RTK关键消息检查:")
    print(f"  {'✅' if has_1005 else '❌'} 基站坐标 (1005/1006): {'有' if has_1005 else '无 - 这是问题所在！'}")
    print(f"  {'✅' if has_obs else '❌'} 观测值数据 (MSM): {'有' if has_obs else '无'}")
    print()

    if not has_1005:
        print("⚠️  警告: 缺少RTCM 1005/1006消息（基站坐标）")
        print("   这是RTK无法工作的根本原因！")
        print("   没有基站坐标，设备无法计算RTK解算。")
        print()

    # Sort by message type
    print("RTCM消息类型统计:")
    print("-"*80)
    print(f"{'类型':<8} {'数量':<8} {'描述':<45} {'平均大小':<12}")
    print("-"*80)

    for msg_type in sorted(msg_stats.keys()):
        count = msg_stats[msg_type]
        desc = get_message_description(msg_type)
        avg_size = sum(msg_sizes[msg_type]) / len(msg_sizes[msg_type])

        # Highlight important messages
        marker = ""
        if msg_type in [1005, 1006]:
            marker = " ⭐ 基站坐标"
        elif msg_type in [1077, 1087, 1097, 1127]:
            marker = " 🛰️ 高精度观测值"

        print(f"{msg_type:<8} {count:<8} {desc:<45} {avg_size:.0f}B{marker}")

    print("-"*80)
    print()

    # Calculate data rate
    if 1077 in msg_stats:
        gps_rate = msg_stats[1077]
        print(f"GPS观测值频率: {gps_rate} 条消息")
        if gps_rate > 0:
            print(f"  估计更新率: ~{gps_rate/10:.1f} Hz (假设文件包含10秒数据)")

    print()

    # Recommendations
    print("建议:")
    if not has_1005:
        print("  ❌ 需要更换NTRIP挂载点或服务器！")
        print("     当前挂载点 'ADDE00AUS0' 不发送基站坐标消息")
        print("     RTK必需的消息: 1005 或 1006")
        print()
        print("  解决方案:")
        print("     1. 访问 http://ntrip.data.gnss.ga.gov.au:2101")
        print("     2. 查看可用的挂载点列表")
        print("     3. 选择一个发送1005/1006消息的挂载点")
        print("     4. 更新 ins401.json 中的 mountPoint 配置")
    else:
        print("  ✅ RTCM消息配置正确")
        if has_obs:
            print("  ✅ 具备RTK所需的所有关键消息")
            print("     如果RTK仍未工作，请检查：")
            print("     - 基站距离（应<50km）")
            print("     - 等待时间（可能需要10-20分钟）")
            print("     - 设备固件版本")


def find_latest_rtcm_file():
    """查找最新的rtcm_base文件"""
    data_dir = Path('data')
    if not data_dir.exists():
        return None

    rtcm_files = list(data_dir.glob('ins401_log_*/rtcm_base_*.bin'))
    if not rtcm_files:
        return None

    # Sort by modification time
    rtcm_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return rtcm_files[0]


def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try to find the latest file
        file_path = find_latest_rtcm_file()
        if not file_path:
            print("错误: 未找到RTCM日志文件")
            print()
            print("用法:")
            print("  python debug/analyze_rtcm.py [rtcm_base_file]")
            print()
            print("示例:")
            print("  python debug/analyze_rtcm.py data/ins401_log_20251006_152618/rtcm_base_2025_10_06_15_26_18.bin")
            sys.exit(1)

        print(f"使用最新的RTCM文件: {file_path}")
        print()

    analyze_file(file_path)


if __name__ == '__main__':
    main()
