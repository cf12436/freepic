#!/bin/bash

# 图床服务部署脚本

set -e

echo "=== 图床服务部署脚本 ==="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p uploads config ssl

# 检查配置文件
if [ ! -f "config/config.json" ]; then
    echo "警告: config/config.json 不存在，将使用默认配置"
fi

# 设置文件权限
chmod +x setup-ssl.sh

echo "构建并启动服务..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
if docker-compose ps | grep -q "Up"; then
    echo "✓ 服务启动成功！"
    echo ""
    echo "服务信息:"
    echo "- HTTP端口: 80"
    echo "- HTTPS端口: 443"
    echo "- 应用端口: 5000"
    echo ""
    echo "API端点:"
    echo "- 上传图片: POST /upload"
    echo "- 删除图片: DELETE /delete/<filename>"
    echo "- 访问图片: GET /image/<filename>"
    echo "- 健康检查: GET /health"
    echo "- 文件列表: GET /list"
    echo ""
    echo "配置文件位置: ./config/config.json"
    echo "上传目录: ./uploads"
    echo "SSL证书目录: ./ssl"
    echo ""
    echo "如需配置SSL证书，请运行: ./setup-ssl.sh"
else
    echo "✗ 服务启动失败，请检查日志:"
    docker-compose logs
    exit 1
fi
