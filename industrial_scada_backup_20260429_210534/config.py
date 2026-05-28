"""
系统配置文件
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# Flask配置
class FlaskConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'industrial-scada-secret-key')
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000

# 数据库配置
class DatabaseConfig:
    # SQLite数据库路径
    DB_PATH = BASE_DIR / 'data' / 'scada.db'
    
    # 数据保留天数
    RETENTION_DAYS = 30
    
    # 数据压缩间隔（小时）
    COMPRESSION_INTERVAL = 24

# Modbus配置
class ModbusConfig:
    # 默认采集间隔（秒）
    DEFAULT_INTERVAL = 5
    
    # 连接超时（秒）
    CONNECTION_TIMEOUT = 10
    
    # 重试次数
    MAX_RETRIES = 3
    
    # 重试间隔（秒）
    RETRY_INTERVAL = 5

# 报警配置
class AlarmConfig:
    # 报警检查间隔（秒）
    CHECK_INTERVAL = 10
    
    # 报警记录保留天数
    RETENTION_DAYS = 90
    
    # 邮件通知配置
    EMAIL_ENABLED = False
    SMTP_SERVER = 'smtp.example.com'
    SMTP_PORT = 587
    SMTP_USERNAME = ''
    SMTP_PASSWORD = ''

# 日志配置
class LogConfig:
    # 日志级别
    LEVEL = 'DEBUG'
    
    # 日志文件路径
    LOG_DIR = BASE_DIR / 'logs'
    
    # 日志保留天数
    RETENTION_DAYS = 30

# 导出配置
class ExportConfig:
    # 导出目录
    EXPORT_DIR = BASE_DIR / 'exports'
    
    # 支持的导出格式
    FORMATS = ['csv', 'excel', 'json']
