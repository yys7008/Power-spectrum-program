from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QPushButton, QLabel, QLineEdit,
                             QDoubleSpinBox, QComboBox, QTabWidget, QStatusBar,
                             QFileDialog, QProgressBar, QCheckBox, QSizePolicy,
                             QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QResizeEvent
import pyqtgraph as pg
from pyqtgraph import exporters  # 添加导入exporters模块
import numpy as np
import os
import time
from datetime import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("激光器与频谱仪控制系统")
        self.setGeometry(100, 100, 1200, 800)
        self.scan_start_time = 0
        self.setMinimumSize(800, 600)  # 设置最小窗口尺寸
        
        # 窗口尺寸调整策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 初始化UI
        self.init_ui()
        
    def resizeEvent(self, event: QResizeEvent):
        """窗口尺寸变化事件处理"""
        super().resizeEvent(event)
        # 自动调整布局以适应窗口尺寸
        self.adjustForScreenSize()
        
    def init_ui(self):
        """初始化UI组件"""
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 使用QSplitter代替固定布局，提供更好的响应式调整
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(main_splitter)
        
        # 左侧控制面板容器（使用滚动区域提高适应性）
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_panel = QWidget()
        control_scroll.setWidget(control_panel)
        control_layout = QVBoxLayout(control_panel)
        
        # 设备连接组
        connection_group = QGroupBox("设备连接")
        connection_layout = QVBoxLayout()
        
        self.laser_gpib = QLineEdit("GPIB0::1::INSTR")
        self.spec_gpib = QLineEdit("GPIB0::2::INSTR")
        
        # 添加频谱仪型号选择
        self.analyzer_model = QComboBox()
        self.analyzer_model.addItems(["N9010B", "CEYEAR4037"])
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("频谱仪型号:"))
        model_layout.addWidget(self.analyzer_model)
        
        connection_layout.addWidget(QLabel("激光器地址:"))
        connection_layout.addWidget(self.laser_gpib)
        connection_layout.addWidget(QLabel("频谱仪地址:"))
        connection_layout.addWidget(self.spec_gpib)
        connection_layout.addLayout(model_layout)
        
        self.auto_detect_btn = QPushButton("自动搜索设备")
        self.connect_btn = QPushButton("连接设备")
        
        connection_layout.addWidget(self.auto_detect_btn)
        connection_layout.addWidget(self.connect_btn)
        connection_group.setLayout(connection_layout)
        control_layout.addWidget(connection_group)
        
        # 激光器参数组 - 添加功率控制
        laser_params = QGroupBox("激光器参数")
        laser_layout = QVBoxLayout()
        
        self.start_wl = QDoubleSpinBox()
        self.start_wl.setRange(1500, 1600)
        self.start_wl.setValue(1520)
        self.start_wl.setSuffix(" nm")
        
        self.stop_wl = QDoubleSpinBox()
        self.stop_wl.setRange(1500, 1600)
        self.stop_wl.setValue(1580)
        self.stop_wl.setSuffix(" nm")
        
        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.0001, 10)  # 最小步进0.1pm
        self.step_size.setValue(0.1)
        self.step_size.setSuffix(" nm")
        self.step_size.setDecimals(4)  # 支持4位小数
        
        self.dwell_time = QDoubleSpinBox()
        self.dwell_time.setRange(1, 60000)  # 1ms到60秒
        self.dwell_time.setValue(100)  # 默认100ms
        self.dwell_time.setSuffix(" ms")  # 使用毫秒单位
        
        # 添加激光器功率设置控件
        self.power_control = QDoubleSpinBox()
        self.power_control.setRange(-20.0, 13.0)  # 设置默认范围
        self.power_control.setValue(0.0)
        self.power_control.setSuffix(" dBm")
        self.power_control.setDecimals(2)
        
        # 自动功率控制模式
        self.apc_mode = QCheckBox("自动功率控制")
        self.apc_mode.setChecked(True)
        
        # 激光器输出使能
        self.output_enable = QCheckBox("激光输出使能")
        self.output_enable.setChecked(False)
        
        laser_layout.addWidget(QLabel("起始波长:"))
        laser_layout.addWidget(self.start_wl)
        laser_layout.addWidget(QLabel("终止波长:"))
        laser_layout.addWidget(self.stop_wl)
        laser_layout.addWidget(QLabel("步长:"))
        laser_layout.addWidget(self.step_size)
        laser_layout.addWidget(QLabel("停留时间:"))
        laser_layout.addWidget(self.dwell_time)
        
        # 添加功率控制部分
        laser_layout.addWidget(QLabel("输出功率:"))
        laser_layout.addWidget(self.power_control)
        laser_layout.addWidget(self.apc_mode)
        laser_layout.addWidget(self.output_enable)
        
        laser_params.setLayout(laser_layout)
        control_layout.addWidget(laser_params)
        
        # 频谱仪参数组
        spec_params = QGroupBox("频谱仪参数")
        spec_layout = QVBoxLayout()
        
        self.start_freq = QDoubleSpinBox()
        self.start_freq.setRange(1, 26500000)
        self.start_freq.setValue(1000)
        self.start_freq.setSuffix(" kHz")
        self.start_freq.setDecimals(3)
        self.start_freq.setSingleStep(1)
        
        self.stop_freq = QDoubleSpinBox()
        self.stop_freq.setRange(1, 26500000)
        self.stop_freq.setValue(10000)
        self.stop_freq.setSuffix(" kHz")
        self.stop_freq.setDecimals(3)
        self.stop_freq.setSingleStep(1)
        
        self.rbw = QDoubleSpinBox()
        self.rbw.setRange(0.001, 8000)
        self.rbw.setValue(100)
        self.rbw.setSuffix(" kHz")
        self.rbw.setDecimals(3)
        self.rbw.setSingleStep(1)
        
        # 添加采样点数显示标签
        self.points_label = QLabel("采样点数: --")
        self.points_label.setAlignment(Qt.AlignCenter)
        self.points_label.setStyleSheet("font-weight: bold;")
        
        # 添加采样点数选择下拉菜单
        self.points_combo = QComboBox()
        self.points_combo.addItem("自动计算", -1)  # -1表示自动计算
        self.points_combo.addItem("101", 101)
        self.points_combo.addItem("201", 201)
        self.points_combo.addItem("401", 401)
        self.points_combo.addItem("601", 601)
        self.points_combo.addItem("801", 801)
        self.points_combo.addItem("1001", 1001)
        self.points_combo.addItem("1601", 1601)
        self.points_combo.addItem("3201", 3201)
        self.points_combo.currentIndexChanged.connect(self.on_points_selection_changed)
        
        # 添加频谱仪型号显示
        self.analyzer_info_label = QLabel("频谱仪型号: 未连接")
        self.analyzer_info_label.setAlignment(Qt.AlignCenter)
        self.analyzer_info_label.setStyleSheet("font-weight: bold; color: blue;")
        
        self.auto_scale_btn = QPushButton("自动调整幅度")
        self.auto_tune_btn = QPushButton("自动调谐")
        
        spec_layout.addWidget(self.analyzer_info_label)
        spec_layout.addWidget(QLabel("起始频率 (kHz):"))
        spec_layout.addWidget(self.start_freq)
        spec_layout.addWidget(QLabel("终止频率 (kHz):"))
        spec_layout.addWidget(self.stop_freq)
        spec_layout.addWidget(QLabel("分辨率带宽 (kHz):"))
        spec_layout.addWidget(self.rbw)
        spec_layout.addWidget(QLabel("采样点数选择:"))
        spec_layout.addWidget(self.points_combo)
        spec_layout.addWidget(self.points_label)
        spec_layout.addWidget(self.auto_scale_btn)
        spec_layout.addWidget(self.auto_tune_btn)
        spec_params.setLayout(spec_layout)
        control_layout.addWidget(spec_params)
        
        # 数据保存设置组
        save_group = QGroupBox("数据保存设置")
        save_layout = QVBoxLayout()
        
        self.save_path = QLineEdit()
        self.save_path.setReadOnly(True)
        self.save_path.setPlaceholderText("选择数据保存目录")
        
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(QLabel("保存路径:"))
        save_path_layout.addWidget(self.save_path)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.select_save_path)
        save_path_layout.addWidget(self.browse_btn)
        save_layout.addLayout(save_path_layout)
        
        self.file_prefix = QLineEdit()
        self.file_prefix.setPlaceholderText("输入文件名前缀")
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("文件前缀:"))
        prefix_layout.addWidget(self.file_prefix)
        save_layout.addLayout(prefix_layout)
        
        self.file_format = QComboBox()
        self.file_format.addItems(["CSV文件 (*.csv)", "Excel文件 (*.xlsx)", "文本文件 (*.txt)", "H5DF文件 (*.h5)"])
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("文件格式:"))
        format_layout.addWidget(self.file_format)
        save_layout.addLayout(format_layout)
        
        self.auto_save = QComboBox()
        self.auto_save.addItems(["手动保存", "自动保存"])
        auto_save_layout = QHBoxLayout()
        auto_save_layout.addWidget(QLabel("保存方式:"))
        auto_save_layout.addWidget(self.auto_save)
        save_layout.addLayout(auto_save_layout)
        
        save_group.setLayout(save_layout)
        control_layout.addWidget(save_group)
        
        # 控制按钮组
        control_buttons = QGroupBox("扫描控制")
        buttons_layout = QVBoxLayout()
        self.start_btn = QPushButton("开始扫描")
        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.setEnabled(False)
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setCheckable(True) # 使按钮可切换
        self.save_btn = QPushButton("保存数据")
        self.save_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.pause_btn) # 添加暂停按钮到这一栏
        buttons_layout.addWidget(self.save_btn)
        control_buttons.setLayout(buttons_layout)
        control_layout.addWidget(control_buttons)
        
        # 进度条
        self.progress_bar = QProgressBar()
        control_layout.addWidget(self.progress_bar)
        control_layout.addStretch()
        
        # 添加左侧控制面板到主分隔器
        main_splitter.addWidget(control_scroll)
        
        # 右侧显示区域（也使用滚动区域优化显示）
        display_scroll = QScrollArea()
        display_scroll.setWidgetResizable(True)
        display_panel = QWidget()
        display_scroll.setWidget(display_panel)
        display_layout = QVBoxLayout(display_panel)
        
        # 图表设置 - 简化显示并使用对数坐标
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # 白色背景
        self.plot_widget.showGrid(x=True, y=True)  # 显示网格
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置坐标轴标签
        self.plot_widget.setLabel('left', '功率', 'dBm')
        self.plot_widget.setLabel('bottom', '频率', 'Hz')
        
        # 设置Y轴为对数坐标
        # 注意：dBm本身已经是对数单位，这里只是设置线性显示
        # 但使用对数刻度可以更好地显示功率变化
        self.plot_widget.setLogMode(x=False, y=True)  # Y轴使用对数坐标
        
        # 使用蓝色线条绘制频谱
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2))
        
        # 频率信息标签
        self.freq_label = QLabel("频率范围: 0 - 0 Hz")
        self.freq_label.setAlignment(Qt.AlignCenter)
        
        display_layout.addWidget(self.freq_label)
        display_layout.addWidget(self.plot_widget, stretch=3)
        
        # 报警状态和波长显示
        status_layout = QHBoxLayout()
        self.alarm_label = QLabel("状态: 正常")
        self.alarm_label.setAlignment(Qt.AlignCenter)
        self.alarm_label.setStyleSheet("background-color: green; color: white;")
        
        self.wavelength_label = QLabel("当前波长: -- nm")
        self.wavelength_label.setAlignment(Qt.AlignCenter)
        
        # 添加时间显示标签
        self.scan_time_label = QLabel("单次扫描: -- ms")
        self.scan_time_label.setAlignment(Qt.AlignCenter)
        self.eta_label = QLabel("预计完成: --:--:--")
        self.eta_label.setAlignment(Qt.AlignCenter)

        # 添加保存图像按钮
        self.save_image_btn = QPushButton("保存图像")
        self.save_image_btn.clicked.connect(self.save_plot_image)  # 连接到保存图像函数
        
        status_layout.addWidget(self.alarm_label)
        status_layout.addWidget(self.wavelength_label)
        status_layout.addWidget(self.scan_time_label)
        
        # 创建按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_image_btn)
        
        display_layout.addLayout(status_layout)
        display_layout.addLayout(btn_layout)
        
        main_splitter.addWidget(display_scroll)
        
        # 设置默认拆分比例 (1:3)
        main_splitter.setSizes([300, 900])
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 数据存储
        self.frequencies = []
        self.powers = []
        
        # 根据频谱仪型号更新界面
        self.analyzer_model.currentTextChanged.connect(self.update_analyzer_limits)
        # 初始调用一次设置默认值
        self.update_analyzer_limits(self.analyzer_model.currentText())

    def update_analyzer_limits(self, model: str):
        """根据频谱仪型号更新频率限制"""
        # 先保存当前下拉菜单选择
        current_selection = self.points_combo.currentData()
        
        # 清空下拉菜单
        self.points_combo.clear()
        self.points_combo.addItem("自动计算", -1)  # -1表示自动计算
        
        # 添加通用选项
        common_points = [101, 201, 401, 601, 801, 1001, 1601, 3201]
        for points in common_points:
            self.points_combo.addItem(str(points), points)
        
        if model == "N9010B":
            self.start_freq.setRange(1, 26500000)  # 1kHz-26.5GHz
            self.stop_freq.setRange(1, 26500000)
            self.points_label.setText("采样点数: -- (最大40001)")
            
            # 添加额外的高点数选项
            extra_points = [6401, 10001, 20001, 30001, 40001]
            for points in extra_points:
                self.points_combo.addItem(str(points), points)
                
        elif model == "CEYEAR4037":
            self.start_freq.setRange(1, 7500000)  # 1kHz-7.5GHz
            self.stop_freq.setRange(1, 7500000)
            self.points_label.setText("采样点数: -- (最大10001)")
            
            # 添加额外的选项
            extra_points = [6401, 8001, 10001]
            for points in extra_points:
                self.points_combo.addItem(str(points), points)
        
        # 恢复之前的选择（如果存在）
        for i in range(self.points_combo.count()):
            if self.points_combo.itemData(i) == current_selection:
                self.points_combo.setCurrentIndex(i)
                break
        
        # 确保当前值不超过新范围
        if self.stop_freq.value() > self.stop_freq.maximum():
            self.stop_freq.setValue(self.stop_freq.maximum())
            
    def on_points_selection_changed(self):
        """采样点数选择变更处理"""
        # 获取当前选择的采样点数
        points = self.points_combo.currentData()
        
        if points == -1:
            # 自动计算模式，更新标签显示为等待计算
            model = self.analyzer_model.currentText()
            max_points = 40001 if model == "N9010B" else 10001
            self.points_label.setText(f"采样点数: -- (最大{max_points})\n(等待计算)")
        else:
            # 手动选择模式，更新标签显示为选择的点数
            self.points_label.setText(f"采样点数: {points} (手动设置)")
            
        # 如果有连接的频谱仪，应用新的采样点设置
        try:
            from main import controller
            if hasattr(controller, 'analyzer') and controller.analyzer:
                controller.analyzer.set_sweep_points(points if points > 0 else 0)
                self.status_bar.showMessage(f"已设置采样点数: {points if points > 0 else '自动计算'}", 2000)
        except:
            pass

    def select_save_path(self):
        """选择数据保存路径"""
        path = QFileDialog.getExistingDirectory(
            self, "选择保存目录", 
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if path:
            self.save_path.setText(path)
            
    def get_save_filename(self) -> str:
        """生成保存文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.file_prefix.text() or "scan"
        save_dir = self.save_path.text() or os.getcwd()
        
        format_str = self.file_format.currentText()
        ext = format_str[format_str.find("*")+1:format_str.find(")")]
        
        return os.path.join(save_dir, f"{prefix}_{timestamp}{ext}")
        
    def update_plot(self, frequencies, powers):
        """更新图表 - 增强版本"""
        self.frequencies = frequencies
        self.powers = powers
        
        # 基本数据检查
        if not frequencies or not powers:
            return
            
        # 转换数据为numpy数组便于处理
        freqs = np.array(frequencies)
        pows = np.array(powers)
        
        # 处理异常值
        valid_mask = (pows > -100) & (pows < 50)  # 过滤明显不合理的数据
        if not np.any(valid_mask):
            return
            
        # 使用有效数据
        valid_freqs = freqs[valid_mask]
        valid_pows = pows[valid_mask]
        
        # 计算显示范围
        min_freq = np.min(valid_freqs)
        max_freq = np.max(valid_freqs)
        min_pow = np.min(valid_pows)
        max_pow = np.max(valid_pows)
        
        # 设置合理的Y轴范围
        if max_pow - min_pow < 10:  # 小动态范围
            y_range = (min_pow - 5, max_pow + 5)
        else:
            y_range = (min_pow - (max_pow - min_pow)*0.1,
                      max_pow + (max_pow - min_pow)*0.1)
        
        # 更新图表
        self.plot_curve.setData(valid_freqs, valid_pows)
        self.freq_label.setText(f"频率范围: {min_freq/1e6:.3f} - {max_freq/1e6:.3f} MHz")
        
        # 设置坐标轴范围
        self.plot_widget.setXRange(min_freq, max_freq)
        self.plot_widget.setYRange(*y_range)
        
        # 恢复原有代码，禁用对数模式以确保正确显示
        self.plot_widget.setLogMode(x=False, y=False)
            
    def update_wavelength(self, wavelength: float):
        """更新当前波长显示"""
        self.wavelength_label.setText(f"当前波长: {wavelength:.3f} nm")
    
    def update_power_display(self, power: float):
        """更新功率显示"""
        # 这里只更新UI显示，不发送实际命令到激光器
        # 使用状态栏显示功率信息，因为没有专门的功率标签
        self.status_bar.showMessage(f"功率设置: {power:.2f} dBm", 2000)
        
    def update_sweep_time(self, sweep_time: float):
        """更新单次扫描时间(ms)和预计完成时间"""
        self.single_sweep_time = sweep_time  # sweep_time 已经是ms单位
        self.scan_time_label.setText(f"单次扫描: {self.single_sweep_time:.1f} ms")

    def update_progress(self, percent: int, wavelength: float):
        """更新扫描进度"""
        self.progress_bar.setValue(percent)
        self.wavelength_label.setText(f"当前波长: {wavelength:.3f} nm")
        self.status_bar.showMessage(f"扫描进度: {percent}%")
        
        # 计算预计完成时间
        if hasattr(self, 'scan_start_time') and hasattr(self, 'wavelength_list'):
            elapsed = time.time() - self.scan_start_time
            remaining = len(self.wavelength_list) * self.single_sweep_time / 1000 - elapsed
            eta = time.strftime("%H:%M:%S", time.localtime(time.time() + remaining))
            self.eta_label.setText(f"预计完成: {eta}")
            
    def save_plot_image(self):
        """保存当前图表为图片"""
        path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)"
        )
        if path:
            exporter = exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(path)
            self.status_bar.showMessage(f"图片已保存到: {path}", 3000)
            
    def toggle_pause(self, checked: bool):
        """切换暂停/继续状态"""
        if checked:
            self.pause_btn.setText("继续")
        else:
            self.pause_btn.setText("暂停")
        
    def on_device_found(self, device_type, address):
        """设备找到时的处理"""
        if device_type == "Laser":
            self.laser_gpib.setText(address)
            self.status_bar.showMessage(f"找到激光器: {address}", 3000)
        elif device_type == "Analyzer":
            self.spec_gpib.setText(address)
            self.status_bar.showMessage(f"找到频谱仪: {address}", 3000)
        elif device_type == "SearchStart":
            # 开始搜索设备时禁用按钮
            self.auto_detect_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.alarm_label.setText(f"状态: 正在搜索设备")
            self.alarm_label.setStyleSheet("background-color: blue; color: white;")
        elif device_type == "SearchComplete":
            # 搜索完成后恢复按钮状态
            self.auto_detect_btn.setEnabled(True)
            self.connect_btn.setEnabled(True)
            if address == "success":
                self.alarm_label.setText("状态: 设备已连接")
                self.alarm_label.setStyleSheet("background-color: green; color: white;")
            else:
                self.alarm_label.setText("状态: 搜索完成")
                self.alarm_label.setStyleSheet("background-color: orange; color: white;")
        elif device_type == "LaserPower":
            # 处理激光器功率信息
            try:
                power = float(address)
                self.update_power_display(power)
                self.power_control.setValue(power)
            except ValueError:
                pass
        elif device_type == "LaserPowerRange":
            # 处理激光器功率范围信息
            try:
                min_power, max_power = map(float, address.split(','))
                self.update_power_range(min_power, max_power)
            except (ValueError, IndexError):
                pass
        elif device_type == "LaserOutputStatus":
            # 处理激光器输出状态
            self.update_output_status(address == "1")
        elif device_type == "LaserAPCMode":
            # 处理激光器APC模式状态
            self.update_apc_status(address == "1")
            
    def on_analyzer_model_detected(self, model: str):
        """频谱仪型号检测到时的处理"""
        # 更新下拉框选择
        index = self.analyzer_model.findText(model)
        if index >= 0:
            self.analyzer_model.setCurrentIndex(index)
        
        # 更新显示标签
        self.analyzer_info_label.setText(f"频谱仪型号: {model}")
            
    def is_auto_save(self) -> bool:
        """检查是否启用自动保存"""
        return self.auto_save.currentText() == "自动保存"
        
    def update_sweep_points(self, points: int, message: str):
        """更新采样点数显示"""
        model = self.analyzer_model.currentText()
        max_points = 40001 if model == "N9010B" else 10001
        
        self.points_label.setText(f"采样点数: {points} (最大{max_points})\n{message}")
        
        if points >= max_points:  # 达到最大点数时显示警告颜色
            self.points_label.setStyleSheet("font-weight: bold; color: red;")
        else:
            self.points_label.setStyleSheet("font-weight: bold; color: black;")
        
    def update_power_range(self, min_power: float, max_power: float):
        """更新功率调节范围"""
        self.power_control.setRange(min_power, max_power)
        
    def update_apc_status(self, is_apc: bool):
        """更新自动功率控制状态"""
        self.apc_mode.setChecked(is_apc)
        
    def update_output_status(self, is_enabled: bool):
        """更新激光输出状态"""
        self.output_enable.setChecked(is_enabled)
        
    def adjustForScreenSize(self):
        """根据屏幕尺寸调整UI组件"""
        window_width = self.width()
        
        # 如果窗口宽度小于900px，调整某些布局和字体大小
        if window_width < 900:
            # 减小字体大小
            for label in self.findChildren(QLabel):
                font = label.font()
                font.setPointSize(8)  # 较小的字体
                label.setFont(font)
                
            # 减小按钮大小
            for btn in self.findChildren(QPushButton):
                btn.setMinimumHeight(20)
                
            # 设置图表的最小高度
            self.plot_widget.setMinimumHeight(250)
        else:
            # 恢复默认字体大小
            for label in self.findChildren(QLabel):
                font = label.font()
                font.setPointSize(9)  # 默认字体大小
                label.setFont(font)
                
            # 恢复按钮大小
            for btn in self.findChildren(QPushButton):
                btn.setMinimumHeight(25)
                
            # 恢复图表默认高度
            self.plot_widget.setMinimumHeight(350)