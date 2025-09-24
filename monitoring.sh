#!/bin/bash

# FreePics 监控脚本
# 用于监控服务状态、资源使用情况和日志

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
LOG_DIR="./logs"
ALERT_EMAIL=""  # 设置告警邮箱
DISK_THRESHOLD=80  # 磁盘使用率告警阈值
MEMORY_THRESHOLD=80  # 内存使用率告警阈值

# 创建日志目录
mkdir -p $LOG_DIR

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}   FreePics 服务监控报告${NC}"
    echo -e "${BLUE}   $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}================================${NC}"
}

check_service_status() {
    echo -e "\n${YELLOW}📊 服务状态检查${NC}"
    echo "----------------------------------------"
    
    # 检查容器状态
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Docker 服务运行正常${NC}"
        docker-compose ps
    else
        echo -e "${RED}❌ Docker 服务异常${NC}"
        docker-compose ps
        return 1
    fi
    
    # 检查健康状态
    echo -e "\n${YELLOW}🏥 健康检查${NC}"
    if curl -s -f http://localhost:5000/health > /dev/null; then
        echo -e "${GREEN}✅ API 服务健康${NC}"
    else
        echo -e "${RED}❌ API 服务不可用${NC}"
        return 1
    fi
    
    # 检查SSL证书
    if [ -f "./ssl/fullchain.pem" ]; then
        cert_expiry=$(openssl x509 -enddate -noout -in ./ssl/fullchain.pem | cut -d= -f2)
        cert_expiry_epoch=$(date -d "$cert_expiry" +%s)
        current_epoch=$(date +%s)
        days_left=$(( (cert_expiry_epoch - current_epoch) / 86400 ))
        
        if [ $days_left -lt 30 ]; then
            echo -e "${YELLOW}⚠️  SSL证书将在 $days_left 天后过期${NC}"
        else
            echo -e "${GREEN}✅ SSL证书有效 (剩余 $days_left 天)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  未找到SSL证书${NC}"
    fi
}

check_resource_usage() {
    echo -e "\n${YELLOW}💻 资源使用情况${NC}"
    echo "----------------------------------------"
    
    # 磁盘使用率
    disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "磁盘使用率: ${disk_usage}%"
    if [ $disk_usage -gt $DISK_THRESHOLD ]; then
        echo -e "${RED}⚠️  磁盘使用率过高: ${disk_usage}%${NC}"
    fi
    
    # 内存使用率
    memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    echo "内存使用率: ${memory_usage}%"
    if [ $memory_usage -gt $MEMORY_THRESHOLD ]; then
        echo -e "${RED}⚠️  内存使用率过高: ${memory_usage}%${NC}"
    fi
    
    # Docker 容器资源使用
    echo -e "\n${BLUE}Docker 容器资源使用:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

check_logs() {
    echo -e "\n${YELLOW}📋 日志检查${NC}"
    echo "----------------------------------------"
    
    # 检查错误日志
    echo "最近的错误日志:"
    if docker-compose logs --tail=10 freepics 2>/dev/null | grep -i error; then
        echo -e "${RED}发现错误日志${NC}"
    else
        echo -e "${GREEN}✅ 无错误日志${NC}"
    fi
    
    # 检查访问统计
    if [ -f "$LOG_DIR/nginx/access.log" ]; then
        echo -e "\n${BLUE}今日访问统计:${NC}"
        today=$(date +%d/%b/%Y)
        grep "$today" $LOG_DIR/nginx/access.log | wc -l | xargs echo "总请求数:"
        grep "$today" $LOG_DIR/nginx/access.log | grep "POST /upload" | wc -l | xargs echo "上传请求:"
        grep "$today" $LOG_DIR/nginx/access.log | grep "GET /image" | wc -l | xargs echo "图片访问:"
    fi
}

check_storage() {
    echo -e "\n${YELLOW}💾 存储检查${NC}"
    echo "----------------------------------------"
    
    # 上传目录大小
    if [ -d "./uploads" ]; then
        upload_size=$(du -sh ./uploads | cut -f1)
        upload_count=$(find ./uploads -type f | wc -l)
        echo "上传文件: ${upload_count} 个文件，总大小: ${upload_size}"
    fi
    
    # 检查大文件
    echo -e "\n${BLUE}最大的文件:${NC}"
    find ./uploads -type f -exec ls -lh {} \; 2>/dev/null | sort -k5 -hr | head -5 | awk '{print $5, $9}'
}

generate_report() {
    local report_file="$LOG_DIR/monitor_report_$(date +%Y%m%d_%H%M%S).log"
    
    {
        print_header
        check_service_status
        check_resource_usage
        check_logs
        check_storage
    } | tee $report_file
    
    echo -e "\n${GREEN}📄 报告已保存到: $report_file${NC}"
}

send_alert() {
    local message="$1"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "FreePics 服务告警" $ALERT_EMAIL
        echo -e "${YELLOW}📧 告警邮件已发送到: $ALERT_EMAIL${NC}"
    fi
}

cleanup_logs() {
    echo -e "\n${YELLOW}🧹 清理旧日志${NC}"
    echo "----------------------------------------"
    
    # 清理7天前的监控报告
    find $LOG_DIR -name "monitor_report_*.log" -mtime +7 -delete
    
    # 清理Docker日志
    docker system prune -f --filter "until=168h"
    
    echo -e "${GREEN}✅ 日志清理完成${NC}"
}

show_help() {
    echo "FreePics 监控脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  status    显示服务状态"
    echo "  resource  显示资源使用情况"
    echo "  logs      显示日志信息"
    echo "  storage   显示存储信息"
    echo "  report    生成完整报告"
    echo "  cleanup   清理旧日志"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status   # 检查服务状态"
    echo "  $0 report   # 生成完整监控报告"
}

# 主程序
case "${1:-report}" in
    "status")
        print_header
        check_service_status
        ;;
    "resource")
        print_header
        check_resource_usage
        ;;
    "logs")
        print_header
        check_logs
        ;;
    "storage")
        print_header
        check_storage
        ;;
    "report")
        generate_report
        ;;
    "cleanup")
        cleanup_logs
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "未知选项: $1"
        show_help
        exit 1
        ;;
esac
