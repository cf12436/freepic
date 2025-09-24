#!/bin/bash

# FreePics 备份脚本
# 用于备份配置文件、上传的图片和数据库

set -e

# 配置
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="freepics_backup_$TIMESTAMP"
RETENTION_DAYS=30  # 保留30天的备份

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

create_backup() {
    print_info "开始创建备份: $BACKUP_NAME"
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    # 备份配置文件
    if [ -d "./config" ]; then
        print_info "备份配置文件..."
        cp -r ./config "$BACKUP_DIR/$BACKUP_NAME/"
        print_success "配置文件备份完成"
    else
        print_warning "配置目录不存在，跳过"
    fi
    
    # 备份上传的图片
    if [ -d "./uploads" ] && [ "$(ls -A ./uploads 2>/dev/null)" ]; then
        print_info "备份上传文件..."
        cp -r ./uploads "$BACKUP_DIR/$BACKUP_NAME/"
        
        # 统计文件信息
        file_count=$(find ./uploads -type f | wc -l)
        total_size=$(du -sh ./uploads | cut -f1)
        print_success "上传文件备份完成 ($file_count 个文件, $total_size)"
    else
        print_warning "上传目录为空或不存在，跳过"
    fi
    
    # 备份SSL证书
    if [ -d "./ssl" ] && [ "$(ls -A ./ssl 2>/dev/null)" ]; then
        print_info "备份SSL证书..."
        cp -r ./ssl "$BACKUP_DIR/$BACKUP_NAME/"
        print_success "SSL证书备份完成"
    else
        print_warning "SSL证书目录为空或不存在，跳过"
    fi
    
    # 备份Docker配置
    print_info "备份Docker配置文件..."
    cp docker-compose.yml "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    cp docker-compose.prod.yml "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    cp nginx.conf "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    cp Dockerfile "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    print_success "Docker配置文件备份完成"
    
    # 备份脚本文件
    print_info "备份脚本文件..."
    cp *.sh "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    cp requirements.txt "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    cp app.py "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
    print_success "脚本文件备份完成"
    
    # 创建备份信息文件
    cat > "$BACKUP_DIR/$BACKUP_NAME/backup_info.txt" << EOF
FreePics 备份信息
================

备份时间: $(date)
备份名称: $BACKUP_NAME
服务器信息: $(uname -a)
Docker版本: $(docker --version 2>/dev/null || echo "未安装")
Docker Compose版本: $(docker-compose --version 2>/dev/null || echo "未安装")

目录结构:
$(ls -la "$BACKUP_DIR/$BACKUP_NAME/")

备份大小:
$(du -sh "$BACKUP_DIR/$BACKUP_NAME")
EOF
    
    print_success "备份信息文件创建完成"
}

compress_backup() {
    print_info "压缩备份文件..."
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    if [ $? -eq 0 ]; then
        # 删除未压缩的目录
        rm -rf "$BACKUP_NAME"
        
        backup_size=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
        print_success "备份压缩完成: ${BACKUP_NAME}.tar.gz ($backup_size)"
    else
        print_error "备份压缩失败"
        return 1
    fi
    
    cd - > /dev/null
}

cleanup_old_backups() {
    print_info "清理旧备份文件..."
    
    if [ -d "$BACKUP_DIR" ]; then
        # 删除超过保留天数的备份
        find "$BACKUP_DIR" -name "freepics_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
        
        # 统计当前备份数量
        backup_count=$(find "$BACKUP_DIR" -name "freepics_backup_*.tar.gz" | wc -l)
        print_success "清理完成，当前保留 $backup_count 个备份文件"
        
        # 显示备份列表
        if [ $backup_count -gt 0 ]; then
            print_info "当前备份列表:"
            find "$BACKUP_DIR" -name "freepics_backup_*.tar.gz" -printf "%T@ %Tc %p\n" | sort -n | cut -d' ' -f2- | tail -10
        fi
    fi
}

restore_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        print_error "请指定要恢复的备份文件"
        list_backups
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "备份文件不存在: $backup_file"
        return 1
    fi
    
    print_warning "恢复备份将覆盖当前配置和数据！"
    read -p "确认要继续吗？(y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "恢复操作已取消"
        return 0
    fi
    
    print_info "开始恢复备份: $backup_file"
    
    # 停止服务
    print_info "停止服务..."
    docker-compose down || true
    
    # 创建当前状态的紧急备份
    emergency_backup="emergency_backup_$(date +%Y%m%d_%H%M%S)"
    print_info "创建紧急备份: $emergency_backup"
    mkdir -p "$BACKUP_DIR/$emergency_backup"
    cp -r config uploads ssl "$BACKUP_DIR/$emergency_backup/" 2>/dev/null || true
    
    # 解压备份文件
    print_info "解压备份文件..."
    temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    backup_dir_name=$(ls "$temp_dir" | head -1)
    backup_path="$temp_dir/$backup_dir_name"
    
    # 恢复文件
    print_info "恢复配置文件..."
    [ -d "$backup_path/config" ] && cp -r "$backup_path/config" ./ || true
    
    print_info "恢复上传文件..."
    [ -d "$backup_path/uploads" ] && cp -r "$backup_path/uploads" ./ || true
    
    print_info "恢复SSL证书..."
    [ -d "$backup_path/ssl" ] && cp -r "$backup_path/ssl" ./ || true
    
    print_info "恢复配置文件..."
    [ -f "$backup_path/docker-compose.yml" ] && cp "$backup_path/docker-compose.yml" ./ || true
    [ -f "$backup_path/nginx.conf" ] && cp "$backup_path/nginx.conf" ./ || true
    
    # 清理临时目录
    rm -rf "$temp_dir"
    
    # 重启服务
    print_info "重启服务..."
    docker-compose up -d
    
    print_success "备份恢复完成！"
    print_info "紧急备份保存在: $BACKUP_DIR/$emergency_backup"
}

list_backups() {
    print_info "可用的备份文件:"
    
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "freepics_backup_*.tar.gz" -printf "%T@ %Tc %p %s\n" | \
        sort -nr | \
        awk '{
            size = $NF
            if (size > 1024*1024*1024) {
                size_str = sprintf("%.1fGB", size/1024/1024/1024)
            } else if (size > 1024*1024) {
                size_str = sprintf("%.1fMB", size/1024/1024)
            } else if (size > 1024) {
                size_str = sprintf("%.1fKB", size/1024)
            } else {
                size_str = sprintf("%dB", size)
            }
            $NF = size_str
            for(i=2; i<=NF-1; i++) printf "%s ", $i
            printf "%s\n", $NF
        }'
    else
        print_warning "备份目录不存在"
    fi
}

show_help() {
    echo "FreePics 备份脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  create              创建新备份"
    echo "  list                列出所有备份"
    echo "  restore <file>      恢复指定备份"
    echo "  cleanup             清理旧备份"
    echo "  help                显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 create                                    # 创建备份"
    echo "  $0 restore backups/freepics_backup_xxx.tar.gz  # 恢复备份"
    echo "  $0 list                                      # 列出备份"
    echo "  $0 cleanup                                   # 清理旧备份"
}

# 主程序
case "${1:-create}" in
    "create")
        create_backup
        compress_backup
        cleanup_old_backups
        ;;
    "list")
        list_backups
        ;;
    "restore")
        restore_backup "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
