"""
REST API模块
提供数据查询和设备控制接口
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)


# ==================== 设备相关API ====================

@api_bp.route('/devices', methods=['GET'])
def get_devices():
    """获取所有设备列表"""
    device_manager = current_app.device_manager
    devices = device_manager.get_all_status()
    return jsonify({'devices': devices})


@api_bp.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """获取单个设备信息"""
    device_manager = current_app.device_manager
    device = device_manager.get_device_status(device_id)
    
    if 'error' in device:
        return jsonify(device), 404
    
    return jsonify(device)


@api_bp.route('/devices/<device_id>/connect', methods=['POST'])
def connect_device(device_id):
    """连接设备"""
    device_manager = current_app.device_manager
    success = device_manager.connect_device(device_id)
    
    return jsonify({
        'success': success,
        'message': '连接成功' if success else '连接失败'
    })


@api_bp.route('/devices/<device_id>/disconnect', methods=['POST'])
def disconnect_device(device_id):
    """断开设备"""
    device_manager = current_app.device_manager
    device_manager.disconnect_device(device_id)
    
    return jsonify({'success': True, 'message': '已断开连接'})


# ==================== 数据查询API ====================

@api_bp.route('/data/realtime', methods=['GET'])
def get_realtime_data():
    """获取实时数据"""
    database = current_app.database
    device_id = request.args.get('device_id')
    limit = request.args.get('limit', 100, type=int)
    
    data = database.get_realtime_data(device_id=device_id, limit=limit)
    
    return jsonify({'data': data})


@api_bp.route('/data/latest/<device_id>', methods=['GET'])
def get_latest_data(device_id):
    """获取设备最新数据"""
    database = current_app.database
    register_name = request.args.get('register_name')
    
    data = database.get_latest_data(device_id=device_id, register_name=register_name)
    
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '没有数据'}), 404


@api_bp.route('/data/history/<device_id>/<register_name>', methods=['GET'])
def get_history_data(device_id, register_name):
    """获取历史数据"""
    database = current_app.database
    
    # 解析时间参数
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    interval = request.args.get('interval', '1min')
    
    if start_time:
        start_time = datetime.fromisoformat(start_time)
    else:
        start_time = datetime.now() - timedelta(hours=1)
    
    if end_time:
        end_time = datetime.fromisoformat(end_time)
    else:
        end_time = datetime.now()
    
    data = database.get_history_data(
        device_id=device_id,
        register_name=register_name,
        start_time=start_time,
        end_time=end_time,
        interval=interval
    )
    
    return jsonify({'data': data})


# ==================== 报警相关API ====================

@api_bp.route('/alarms', methods=['GET'])
def get_alarms():
    """获取报警记录"""
    database = current_app.database
    
    device_id = request.args.get('device_id')
    alarm_level = request.args.get('alarm_level')
    acknowledged = request.args.get('acknowledged')
    limit = request.args.get('limit', 100, type=int)
    
    if acknowledged is not None:
        acknowledged = acknowledged.lower() == 'true'
    
    data = database.get_alarm_records(
        device_id=device_id,
        alarm_level=alarm_level,
        acknowledged=acknowledged,
        limit=limit
    )
    
    return jsonify({'alarms': data})


@api_bp.route('/alarms/active', methods=['GET'])
def get_active_alarms():
    """获取活动报警"""
    alarm_manager = current_app.alarm_manager
    alarms = alarm_manager.get_active_alarms()
    
    return jsonify({'alarms': alarms})


@api_bp.route('/alarms/<alarm_id>/acknowledge', methods=['POST'])
def acknowledge_alarm(alarm_id):
    """确认报警"""
    alarm_manager = current_app.alarm_manager
    
    data = request.get_json()
    device_id = data.get('device_id')
    register_name = data.get('register_name')
    acknowledged_by = data.get('acknowledged_by', 'operator')
    
    success = alarm_manager.acknowledge_alarm(
        alarm_id=alarm_id,
        device_id=device_id,
        register_name=register_name,
        acknowledged_by=acknowledged_by
    )
    
    return jsonify({
        'success': success,
        'message': '报警已确认' if success else '确认失败'
    })


@api_bp.route('/alarms/statistics', methods=['GET'])
def get_alarm_statistics():
    """获取报警统计"""
    alarm_manager = current_app.alarm_manager
    stats = alarm_manager.get_alarm_statistics()
    
    return jsonify(stats)


# ==================== 系统信息API ====================

@api_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    database = current_app.database
    device_manager = current_app.device_manager
    data_collector = current_app.data_collector
    alarm_manager = current_app.alarm_manager
    
    # 计算运行时间
    start_time = getattr(current_app, 'system_start_time', None)
    uptime_seconds = 0
    if start_time:
        uptime_seconds = (datetime.now() - start_time).total_seconds()
    
    return jsonify({
        'database': database.get_database_stats(),
        'devices': device_manager.get_all_status(),
        'collector': data_collector.get_stats(),
        'alarms': alarm_manager.get_alarm_statistics(),
        'uptime_seconds': uptime_seconds,
        'start_time': start_time.isoformat() if start_time else None,
        'simulation_mode': device_manager.simulation_mode
    })


@api_bp.route('/system/database', methods=['GET'])
def get_database_stats():
    """获取数据库统计"""
    database = current_app.database
    stats = database.get_database_stats()
    
    return jsonify(stats)


# ==================== 数据导出API ====================

@api_bp.route('/export/device/<device_id>', methods=['POST'])
def export_device_data(device_id):
    """导出设备数据"""
    from 存储层.data_export import DataExport
    
    database = current_app.database
    data = request.get_json()
    
    start_time = datetime.fromisoformat(data.get('start_time'))
    end_time = datetime.fromisoformat(data.get('end_time'))
    format = data.get('format', 'csv')
    
    exporter = DataExport()
    filepath = exporter.export_device_data(
        database=database,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        format=format
    )
    
    if filepath:
        return jsonify({'success': True, 'filepath': filepath})
    else:
        return jsonify({'success': False, 'message': '导出失败'}), 500


@api_bp.route('/export/alarms', methods=['POST'])
def export_alarms():
    """导出报警记录"""
    from 存储层.data_export import DataExport
    
    database = current_app.database
    data = request.get_json() or {}
    
    start_time = datetime.fromisoformat(data.get('start_time')) if data.get('start_time') else None
    end_time = datetime.fromisoformat(data.get('end_time')) if data.get('end_time') else None
    format = data.get('format', 'csv')
    
    exporter = DataExport()
    filepath = exporter.export_alarm_records(
        database=database,
        start_time=start_time,
        end_time=end_time,
        format=format
    )
    
    if filepath:
        return jsonify({'success': True, 'filepath': filepath})
    else:
        return jsonify({'success': False, 'message': '没有报警记录可导出'})
