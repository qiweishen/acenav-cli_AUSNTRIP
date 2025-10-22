#!/bin/bash
# RTK调试测试脚本
# 运行此脚本以测试带有调试输出的RTK功能

echo "=========================================="
echo "RTK调试测试"
echo "=========================================="
echo ""
echo "此脚本将运行acenav-cli并显示RTCM数据流调试信息"
echo ""
echo "预期看到的调试输出："
echo "  [NTRIP DEBUG] - NTRIP客户端解析RTCM消息"
echo "  [RTCM DEBUG]  - RTCM数据接收和发送到设备"
echo ""
echo "按 Ctrl+C 停止测试"
echo ""
echo "=========================================="
echo ""

# 运行
python main.py -i 100base-t1

echo ""
echo "测试结束"
