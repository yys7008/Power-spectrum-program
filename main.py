#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from gui.main_window import MainWindow
from core.controller import LaserSystemController

def main():
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 创建主窗口和控制器
    window = MainWindow()
    controller = LaserSystemController()
    
    # 连接设备控制信号
    window.connect_btn.clicked.connect(
        lambda: controller.connect_devices(
            window.laser_gpib.text(),
            window.spec_gpib.text(),
            window.analyzer_model.currentText()
        )
    )
    window.auto_detect_btn.clicked.connect(controller.auto_connect_devices)
    controller.device_found.connect(window.on_device_found)
    controller.analyzer_model_detected.connect(window.on_analyzer_model_detected)
    controller.scan_progress.connect(window.update_progress)
    controller.sweep_time_updated.connect(window.update_sweep_time)
    
    # 连接激光器功率控制信号
    # 使用valueChanged仅更新UI显示，不直接发送命令
    window.power_control.valueChanged.connect(
        lambda: window.update_power_display(window.power_control.value())
    )
    # 使用editingFinished信号，只有当用户完成编辑时才发送命令到激光器
    # 直接设置功率，不检查激光器是否连接
    window.power_control.editingFinished.connect(
        lambda: controller.set_laser_power(window.power_control.value())
    )
    window.apc_mode.toggled.connect(
        lambda checked: controller.set_laser_apc_mode(checked) if controller.laser else None
    )
    window.output_enable.toggled.connect(
        lambda checked: controller.set_laser_output(checked) if controller.laser else None
    )
    
    # 连接参数更新信号
    window.start_freq.valueChanged.connect(
        lambda: update_sweep_points(window, controller)
    )
    window.stop_freq.valueChanged.connect(
        lambda: update_sweep_points(window, controller)
    )
    window.rbw.valueChanged.connect(
        lambda: update_sweep_points(window, controller)
    )
    controller.points_calculated.connect(window.update_sweep_points)
    
    # 连接内存监控信号
    controller.memory_warning.connect(
        lambda usage, msg: show_memory_warning(window, usage, msg)
    )
    
    # 频谱仪型号变更时更新界面和参数
    window.analyzer_model.currentTextChanged.connect(
        lambda: update_analyzer_model(window, controller)
    )
    
    # 连接扫描控制信号
    window.start_btn.clicked.connect(
        lambda: check_save_path_and_start(window, controller)
    )
    window.stop_btn.clicked.connect(lambda: stop_scan(window, controller))
    window.pause_btn.clicked.connect(lambda checked: toggle_pause_scan(window, controller, checked))
    
    # 连接数据更新信号
    controller.data_updated.connect(window.update_plot)
    controller.scan_progress.connect(window.update_progress)
    controller.scan_complete.connect(lambda: scan_complete(window, controller))
    controller.alarm_triggered.connect(
        lambda msg: window.alarm_label.setText(f"报警: {msg}")
    )
    
    # 连接频谱仪控制信号
    window.auto_scale_btn.clicked.connect(
        lambda: controller.analyzer.auto_scale() if controller.analyzer else None
    )
    window.auto_tune_btn.clicked.connect(
        lambda: controller.analyzer.auto_tune() if controller.analyzer else None
    )
    
    # 连接数据保存信号
    window.save_btn.clicked.connect(lambda: save_data(window, controller))
    
    # 显示窗口
    window.show()
    
    # 初始计算采样点数
    update_sweep_points(window, controller)
    
    return app.exec_()

def show_memory_warning(window, usage, message):
    """显示内存使用警告"""
    if usage > 1000:  # 超过1GB时用红色
        style = "color: red; font-weight: bold;"
    elif usage > 500:  # 超过500MB时用橙色
        style = "color: orange; font-weight: bold;"
    else:
        style = "color: blue; font-weight: bold;"
        
    QMessageBox.warning(
        window,
        "内存使用警告",
        f"<p style='{style}'>预计内存使用: {usage:.1f} MB</p>"
    )
    
    # 在状态栏显示简短提示
    window.status_bar.showMessage(f"内存警告: {usage:.1f}MB", 5000)

def update_analyzer_model(window, controller):
    """频谱仪型号变更处理"""
    window.update_analyzer_limits(window.analyzer_model.currentText())
    update_sweep_points(window, controller)

def update_sweep_points(window, controller):
    """更新采样点数"""
    if controller.analyzer:
        # 获取手动设置的采样点数
        manual_points = window.points_combo.currentData()
        
        if manual_points > 0:
            # 使用手动设置的点数
            points = manual_points
            message = f"手动设置的采样点数: {points}"
            window.update_sweep_points(points, message)
        else:
            # 自动计算采样点数
            points, message = controller.calculate_sweep_points(
                window.start_freq.value() * 1e3,  # kHz转Hz
                window.stop_freq.value() * 1e3,   # kHz转Hz
                window.rbw.value() * 1e3          # kHz转Hz
            )
            window.update_sweep_points(points, message)

def check_save_path_and_start(window, controller):
    """检查设备并开始扫描"""
    # 检查设备连接状态
    if not controller.laser or not controller.analyzer:
        QMessageBox.warning(
            window,
            "设备错误",
            "请先连接激光器和频谱仪"
        )
        return
    
    # 开始扫描
    try:
        start_scan(window, controller)
    except Exception as e:
        QMessageBox.warning(
            window,
            "扫描错误",
            f"启动扫描失败: {str(e)}"
        )

def start_scan(window, controller):
    """开始扫描"""
    # 检查设备连接状态
    if not controller.analyzer or not controller.laser:
        QMessageBox.warning(
            window,
            "设备错误",
            "请确保激光器和频谱仪都已连接"
        )
        return
        
    try:
        # 获取手动设置的采样点数
        manual_points = window.points_combo.currentData()
        
        # 设置扫描参数
        controller.set_scan_parameters(
            window.start_wl.value(),
            window.stop_wl.value(),
            window.step_size.value(),
            window.dwell_time.value() / 1000.0,  # ms转s
            window.start_freq.value() * 1e3,     # kHz转Hz
            window.stop_freq.value() * 1e3,      # kHz转Hz
            window.rbw.value() * 1e3,            # kHz转Hz
            manual_points                        # 手动设置的采样点数，-1表示自动计算
        )
        
        # 更新按钮状态
        window.start_btn.setEnabled(False)
        window.stop_btn.setEnabled(True)
        window.pause_btn.setEnabled(True)
        window.save_btn.setEnabled(False)
        window.auto_scale_btn.setEnabled(False)
        window.auto_tune_btn.setEnabled(False)
        
        # 清除旧数据
        window.frequencies = []
        window.powers = []
        window.plot_curve.setData([], [])
        window.progress_bar.setValue(0)
        window.alarm_label.setText("状态: 扫描中")
        window.alarm_label.setStyleSheet("background-color: blue; color: white;")
        
        # 开始扫描
        controller.start_scan()
        window.status_bar.showMessage("扫描已启动")
            
    except ValueError as e:
        QMessageBox.warning(window, "参数错误", str(e))
        
    except Exception as e:
        QMessageBox.critical(window, "错误", f"扫描启动失败: {str(e)}")

def stop_scan(window, controller):
    """停止扫描"""
    controller.stop_scan()
    window.stop_btn.setEnabled(False)
    window.pause_btn.setEnabled(False)
    window.pause_btn.setChecked(False)
    window.pause_btn.setText("暂停")
    window.start_btn.setEnabled(True)
    window.auto_scale_btn.setEnabled(True)
    window.auto_tune_btn.setEnabled(True)
    window.save_btn.setEnabled(True)
    window.alarm_label.setText("状态: 已停止")
    window.alarm_label.setStyleSheet("background-color: orange; color: white;")

def scan_complete(window, controller):
    """扫描完成处理"""
    window.start_btn.setEnabled(True)
    window.stop_btn.setEnabled(False)
    window.pause_btn.setEnabled(False)
    window.pause_btn.setChecked(False)
    window.pause_btn.setText("暂停")
    window.save_btn.setEnabled(True)
    window.auto_scale_btn.setEnabled(True)
    window.auto_tune_btn.setEnabled(True)
    window.status_bar.showMessage("扫描完成", 3000)
    window.alarm_label.setText("状态: 正常")
    window.alarm_label.setStyleSheet("background-color: green; color: white;")
    window.progress_bar.setValue(100)
    
    # 如果启用了自动保存，则自动保存数据
    if window.is_auto_save():
        save_data(window, controller)
        
    # 在状态栏显示简要统计信息
    try:
        data_info = controller.get_data_info()
        wl_points = data_info.get('wave_length_points', 0)
        freq_points = data_info.get('frequency_points', 0)
        window.status_bar.showMessage(f"扫描完成: {wl_points}波长点, {freq_points}频率点", 5000)
    except:
        window.status_bar.showMessage("扫描完成", 3000)

def save_data(window, controller):
    """保存数据(统一使用simple_save_data)"""
    try:
        filename = window.get_save_filename()
        if controller.simple_save_data(filename):
            window.status_bar.showMessage(f"数据已保存到: {filename}", 3000)
            return True
        return False
    except Exception as e:
        QMessageBox.warning(
            window,
            "保存失败",
            f"保存数据时出错: {str(e)}"
        )
        return False

def toggle_pause_scan(window, controller, checked):
    """切换暂停/继续扫描"""
    if checked:
        # 暂停扫描
        if controller.pause_scan():
            window.status_bar.showMessage("扫描已暂停", 3000)
    else:
        # 继续扫描
        if controller.resume_scan():
            window.status_bar.showMessage("扫描已继续", 3000)
    
    # 更新按钮文本
    window.toggle_pause(checked)

if __name__ == "__main__":
    sys.exit(main())