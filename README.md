# 激光器控制程序

这个程序用于控制激光器和频谱分析仪，进行波长扫描和数据采集。

## 安装说明

本程序依赖于多个Python库，包括pandas等数据处理库。由于不同系统环境可能导致安装问题，特别是pandas库在某些环境下可能难以安装，我们提供了以下几种安装方法。

### 基本安装

```bash
# 使用pip安装
pip install -e .
```

使用上述命令将自动根据您的系统环境选择合适的pandas版本。

### 解决pandas安装问题

如果安装pandas时遇到问题，可以尝试以下方法：

1. **手动安装pandas**：

```bash
# 安装较老但稳定的pandas版本
pip install pandas==1.3.5
# 然后安装其他依赖
pip install -e .
```

2. **使用conda安装**：

```bash
# 使用conda创建环境并安装pandas
conda create -n laser_env python=3.8 pandas
conda activate laser_env
# 然后安装其他依赖
pip install -e .
```

3. **解决依赖问题**：

在某些系统上，可能需要先安装pandas的依赖库：

```bash
# 对于Ubuntu/Debian系统
sudo apt-get install python3-dev build-essential
# 然后安装pandas
pip install pandas
```

### 已知问题及解决方案

1. **numpy版本兼容性**：如果遇到numpy相关错误，尝试安装特定版本：
   ```bash
   pip install numpy==1.23.5
   pip install pandas==1.5.3
   ```

2. **编译错误**：在某些系统上可能需要安装C编译器：
   - Windows: 安装Visual C++ Build Tools
   - Linux: 安装gcc和必要的开发包
   - macOS: 安装Xcode Command Line Tools

## 使用说明

1. 连接设备
2. 设置扫描参数
3. 开始扫描
4. 保存数据

数据将以CSV, Excel或文本格式保存，可用于后续分析。

## 系统要求

- Python 3.6+
- 支持的操作系统: Windows, Linux, macOS