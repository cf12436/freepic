from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import hashlib
import io
import uuid
import shutil
import zipfile
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置文件路径
CONFIG_PATH = os.getenv('CONFIG_PATH', './config')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_PATH, exist_ok=True)

def load_config():
    """加载配置文件"""
    config_file = os.path.join(CONFIG_PATH, 'config.json')
    default_config = {
        "allowed_origins": ["*"],
        "api_keys": [],
        "max_file_size": MAX_FILE_SIZE,
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # 创建默认配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return default_config

# 加载配置
config = load_config()

# 配置CORS
CORS(app, 
     origins=['*'],  # 本地开发允许所有来源
     methods=['GET', 'POST', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'X-API-Key'],
     supports_credentials=True)

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.get('allowed_extensions', ALLOWED_EXTENSIONS)

def verify_api_key():
    """验证API密钥"""
    api_keys = config.get('api_keys', [])
    if not api_keys:  # 如果没有配置API密钥，则不验证
        return True
    
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    return api_key in api_keys

def generate_filename(original_filename):
    """生成唯一的文件名"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{unique_id}.{ext}"

def optimize_image(image_data, max_size=(1920, 1080), quality=85):
    """优化图片大小和质量"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # 如果图片过大，进行缩放
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 转换为RGB模式（如果需要）
        if image.mode in ('RGBA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # 保存优化后的图片
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception as e:
        logger.error(f"图片优化失败: {e}")
        return image_data

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传图片接口"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'不支持的文件类型，支持的格式: {", ".join(config.get("allowed_extensions", ALLOWED_EXTENSIONS))}'
            }), 400
        
        # 检查文件大小
        file_data = file.read()
        if len(file_data) > config.get('max_file_size', MAX_FILE_SIZE):
            return jsonify({'error': f'文件大小超过限制 ({config.get("max_file_size", MAX_FILE_SIZE) // 1024 // 1024}MB)'}), 400
        
        # 获取文件夹参数（可选）
        folder = request.form.get('folder', 'tmp').strip()
        if not folder:
            folder = 'tmp'
        
        # 验证文件夹名称（防止路径遍历攻击）
        folder = secure_filename(folder)
        if not folder or folder in ['.', '..']:
            folder = 'tmp'
        
        # 生成文件名
        filename = generate_filename(secure_filename(file.filename))
        
        # 优化图片（可选）
        optimize = request.form.get('optimize', 'false').lower() == 'true'
        logger.info(f"上传文件: {file.filename}, 文件夹: {folder}, 大小: {len(file_data)}, 优化: {optimize}")
        
        if optimize and file.content_type and file.content_type.startswith('image/'):
            try:
                original_size = len(file_data)
                file_data = optimize_image(file_data)
                logger.info(f"图片优化: {original_size} -> {len(file_data)} bytes")
            except Exception as e:
                logger.warning(f"图片优化失败，使用原图: {e}")
                # 继续使用原始图片数据
        
        # 创建目标文件夹路径
        target_folder = os.path.join(UPLOAD_FOLDER, folder)
        file_path = os.path.join(target_folder, filename)
        logger.info(f"保存文件到: {file_path}")
        
        try:
            # 确保目标文件夹存在
            os.makedirs(target_folder, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"文件保存成功: {folder}/{filename}")
            
        except Exception as e:
            logger.error(f"文件保存失败: {e}", exc_info=True)
            return jsonify({'error': f'文件保存失败: {str(e)}'}), 500
        
        # 生成访问URL
        base_url = request.url_root.rstrip('/')
        file_url = f"{base_url}/image/{folder}/{filename}"
        
        # 计算文件哈希
        file_hash = hashlib.md5(file_data).hexdigest()
        
        logger.info(f"文件上传成功: {filename}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': file_url,
            'size': len(file_data),
            'hash': file_hash,
            'upload_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """删除图片接口（支持文件夹）"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        # 查找文件的完整路径
        file_found = False
        file_path = None
        
        # 递归搜索文件
        for root, dirs, filenames in os.walk(UPLOAD_FOLDER):
            if filename in filenames:
                file_path = os.path.join(root, filename)
                file_found = True
                break
        
        if not file_found or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 确保文件在上传目录内（安全检查）
        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
            return jsonify({'error': '无效的文件路径'}), 400
        
        # 删除文件
        os.remove(file_path)
        
        logger.info(f"文件删除成功: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功',
            'delete_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        return jsonify({'error': '文件删除失败'}), 500

@app.route('/image/<path:filepath>')
def serve_image(filepath):
    """提供图片访问接口（支持文件夹）"""
    try:
        # 安全处理文件路径，保留文件夹结构
        filepath = filepath.replace('/', os.sep)
        # 对路径的每个部分进行安全处理
        path_parts = filepath.split(os.sep)
        safe_parts = [secure_filename(part) for part in path_parts if part]
        safe_filepath = os.sep.join(safe_parts)
        
        full_path = os.path.join(UPLOAD_FOLDER, safe_filepath)
        
        # 确保文件在上传目录内（防止路径遍历攻击）
        if not os.path.abspath(full_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
            return jsonify({'error': '无效的文件路径'}), 400
            
        if os.path.exists(full_path) and os.path.isfile(full_path):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            return send_from_directory(directory, filename)
        else:
            return jsonify({'error': '图片不存在'}), 404
    except Exception as e:
        logger.error(f"图片访问失败: {e}")
        return jsonify({'error': '图片访问失败'}), 500

@app.route('/list', methods=['GET'])
def list_files():
    """列出所有图片接口（管理用）"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        files = []
        base_url = request.url_root.rstrip('/')
        
        # 递归遍历所有文件夹
        for root, dirs, filenames in os.walk(UPLOAD_FOLDER):
            for filename in filenames:
                # 跳过非图片文件（如.gitkeep等）
                if not allowed_file(filename):
                    continue
                    
                file_path = os.path.join(root, filename)
                # 计算相对路径
                rel_path = os.path.relpath(file_path, UPLOAD_FOLDER)
                folder = os.path.dirname(rel_path) if os.path.dirname(rel_path) != '.' else ''
                
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    url_path = rel_path.replace(os.sep, '/')
                    files.append({
                        'filename': filename,
                        'folder': folder,
                        'path': rel_path,
                        'url': f"{base_url}/image/{url_path}",
                        'size': stat.st_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        }), 200
        
    except Exception as e:
        logger.error(f"文件列表获取失败: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500

@app.route('/delete-all', methods=['DELETE'])
def delete_all_files():
    """批量删除所有图片接口"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        deleted_files = []
        failed_files = []
        
        # 获取所有文件
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify({
                'success': True,
                'message': '上传目录不存在，无文件需要删除',
                'deleted_count': 0,
                'failed_count': 0,
                'delete_time': datetime.now().isoformat()
            }), 200
        
        # 递归遍历并删除所有文件
        for root, dirs, filenames in os.walk(UPLOAD_FOLDER):
            for filename in filenames:
                # 跳过非图片文件（如.gitkeep等）
                if not allowed_file(filename):
                    continue
                    
                file_path = os.path.join(root, filename)
                try:
                    os.remove(file_path)
                    # 计算相对路径用于显示
                    rel_path = os.path.relpath(file_path, UPLOAD_FOLDER)
                    deleted_files.append(rel_path)
                    logger.info(f"文件删除成功: {rel_path}")
                except Exception as e:
                    rel_path = os.path.relpath(file_path, UPLOAD_FOLDER)
                    failed_files.append({'filename': rel_path, 'error': str(e)})
                    logger.error(f"文件删除失败: {rel_path}, 错误: {e}")
        
        # 删除空的子文件夹
        for root, dirs, filenames in os.walk(UPLOAD_FOLDER, topdown=False):
            for dirname in dirs:
                dir_path = os.path.join(root, dirname)
                try:
                    # 只删除空文件夹
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        logger.info(f"空文件夹删除成功: {dirname}")
                except Exception as e:
                    logger.warning(f"文件夹删除失败: {dirname}, 错误: {e}")
        
        total_deleted = len(deleted_files)
        total_failed = len(failed_files)
        
        logger.info(f"批量删除完成: 成功 {total_deleted} 个，失败 {total_failed} 个")
        
        response_data = {
            'success': True,
            'message': f'批量删除完成: 成功删除 {total_deleted} 个文件',
            'deleted_count': total_deleted,
            'failed_count': total_failed,
            'deleted_files': deleted_files,
            'delete_time': datetime.now().isoformat()
        }
        
        # 如果有失败的文件，添加失败信息
        if failed_files:
            response_data['failed_files'] = failed_files
            response_data['message'] += f'，{total_failed} 个文件删除失败'
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"批量删除失败: {e}", exc_info=True)
        return jsonify({'error': f'批量删除失败: {str(e)}'}), 500

@app.route('/config', methods=['GET'])
def get_config():
    """获取配置信息（不包含敏感信息）"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        safe_config = {
            'allowed_extensions': config.get('allowed_extensions', list(ALLOWED_EXTENSIONS)),
            'max_file_size': config.get('max_file_size', MAX_FILE_SIZE),
            'max_file_size_mb': config.get('max_file_size', MAX_FILE_SIZE) // 1024 // 1024,
            'has_api_keys': len(config.get('api_keys', [])) > 0
        }
        
        return jsonify(safe_config), 200
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({'error': '获取配置失败'}), 500

@app.route('/move', methods=['POST'])
def move_file():
    """转移文件到指定文件夹"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据格式错误'}), 400
            
        filename = data.get('filename')
        current_folder = data.get('current_folder', '')
        target_folder = data.get('target_folder', 'tmp')
        
        if not filename:
            return jsonify({'error': '文件名不能为空'}), 400
        
        # 安全处理文件夹名称
        filename = secure_filename(filename)
        current_folder = secure_filename(current_folder) if current_folder else ''
        target_folder = secure_filename(target_folder) if target_folder else 'tmp'
        
        # 构建源文件路径
        if current_folder:
            source_path = os.path.join(UPLOAD_FOLDER, current_folder, filename)
        else:
            source_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 构建目标文件路径
        target_dir = os.path.join(UPLOAD_FOLDER, target_folder)
        target_path = os.path.join(target_dir, filename)
        
        # 检查源文件是否存在
        if not os.path.exists(source_path):
            return jsonify({'error': '源文件不存在'}), 404
        
        # 创建目标文件夹
        os.makedirs(target_dir, exist_ok=True)
        
        # 检查目标文件是否已存在
        if os.path.exists(target_path):
            return jsonify({'error': '目标文件夹中已存在同名文件'}), 409
        
        # 移动文件
        shutil.move(source_path, target_path)
        
        # 生成新的URL
        base_url = request.url_root.rstrip('/')
        new_url = f"{base_url}/image/{target_folder}/{filename}"
        
        logger.info(f"文件移动成功: {filename} 从 {current_folder or '根目录'} 到 {target_folder}")
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 已移动到 {target_folder} 文件夹',
            'new_url': new_url,
            'new_folder': target_folder
        }), 200
        
    except Exception as e:
        logger.error(f"文件移动失败: {e}")
        return jsonify({'error': f'文件移动失败: {str(e)}'}), 500

@app.route('/backup', methods=['POST'])
def create_backup():
    """创建备份ZIP文件"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        import zipfile
        from datetime import datetime
        
        # 创建备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"freepics_backup_{timestamp}.zip"
        # 使用应用目录下的临时文件夹，确保有写权限
        backup_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 创建ZIP文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(UPLOAD_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, UPLOAD_FOLDER)
                    zipf.write(file_path, arcname)
        
        # 获取文件大小
        backup_size = os.path.getsize(backup_path)
        
        logger.info(f"备份创建成功: {backup_filename}, 大小: {backup_size} bytes")
        
        return jsonify({
            'success': True,
            'backup_file': backup_filename,
            'backup_size': backup_size,
            'download_url': f"/download-backup/{backup_filename}"
        }), 200
        
    except Exception as e:
        logger.error(f"备份创建失败: {e}")
        return jsonify({'error': f'备份创建失败: {str(e)}'}), 500

@app.route('/download-backup/<filename>')
def download_backup(filename):
    """下载备份文件"""
    try:
        filename = secure_filename(filename)
        backup_dir = os.path.join(os.path.dirname(__file__), 'temp')
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': '备份文件不存在'}), 404
        
        return send_file(backup_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"备份下载失败: {e}")
        return jsonify({'error': '备份下载失败'}), 500

@app.route('/restore', methods=['POST'])
def restore_backup():
    """从备份ZIP文件恢复数据"""
    try:
        # 验证API密钥
        if not verify_api_key():
            return jsonify({'error': '无效的API密钥'}), 401
        
        # 检查是否有文件
        if 'backup_file' not in request.files:
            return jsonify({'error': '没有选择备份文件'}), 400
        
        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            return jsonify({'error': '没有选择备份文件'}), 400
        
        # 检查文件类型
        if not backup_file.filename.endswith('.zip'):
            return jsonify({'error': '备份文件必须是ZIP格式'}), 400
        
        import zipfile
        import tempfile
        
        # 保存上传的ZIP文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            backup_file.save(temp_file.name)
            temp_zip_path = temp_file.name
        
        try:
            # 验证ZIP文件
            with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
                # 检查ZIP文件是否有效
                zipf.testzip()
                
                # 清空现有文件（可选，根据需求决定）
                clear_existing = request.form.get('clear_existing', 'false').lower() == 'true'
                if clear_existing:
                    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # 解压文件到上传目录
                zipf.extractall(UPLOAD_FOLDER)
                
                # 统计恢复的文件数量
                restored_count = len(zipf.namelist())
                
            logger.info(f"数据恢复成功: 恢复了 {restored_count} 个文件")
            
            return jsonify({
                'success': True,
                'message': f'数据恢复成功，恢复了 {restored_count} 个文件',
                'restored_count': restored_count
            }), 200
            
        finally:
            # 清理临时文件
            os.unlink(temp_zip_path)
        
    except zipfile.BadZipFile:
        return jsonify({'error': '无效的ZIP文件'}), 400
    except Exception as e:
        logger.error(f"数据恢复失败: {e}")
        return jsonify({'error': f'数据恢复失败: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(5001)
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"图床服务启动中...")
    logger.info(f"上传目录: {UPLOAD_FOLDER}")
    logger.info(f"配置目录: {CONFIG_PATH}")
    logger.info(f"端口: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
