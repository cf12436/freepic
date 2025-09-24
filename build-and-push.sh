#!/bin/bash

# Docker Hub 镜像构建和推送脚本

set -e

# 配置
DOCKER_USERNAME="maomao12436"  # 你的Docker Hub用户名
IMAGE_NAME="freepics"
VERSION="latest"
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$VERSION"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    print_error "Docker未安装，请先安装Docker"
    exit 1
fi

# 检查是否登录Docker Hub
if ! docker info | grep -q "Username"; then
    print_warning "请先登录Docker Hub"
    echo "运行: docker login"
    exit 1
fi

print_info "开始构建Docker镜像: $FULL_IMAGE_NAME"

# 构建镜像
docker build -t $FULL_IMAGE_NAME .

if [ $? -eq 0 ]; then
    print_success "镜像构建成功"
else
    print_error "镜像构建失败"
    exit 1
fi

# 推送到Docker Hub
print_info "推送镜像到Docker Hub..."
docker push $FULL_IMAGE_NAME

if [ $? -eq 0 ]; then
    print_success "镜像推送成功"
    print_info "镜像地址: https://hub.docker.com/r/$DOCKER_USERNAME/$IMAGE_NAME"
    print_info "拉取命令: docker pull $FULL_IMAGE_NAME"
else
    print_error "镜像推送失败"
    exit 1
fi

# 创建多架构镜像（可选）
read -p "是否创建多架构镜像 (amd64/arm64)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "创建多架构镜像..."
    
    # 创建并使用buildx builder
    docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch
    
    # 构建并推送多架构镜像
    docker buildx build --platform linux/amd64,linux/arm64 -t $FULL_IMAGE_NAME --push .
    
    if [ $? -eq 0 ]; then
        print_success "多架构镜像创建成功"
    else
        print_warning "多架构镜像创建失败，但单架构镜像已成功推送"
    fi
fi

print_success "Docker Hub 镜像发布完成！"
