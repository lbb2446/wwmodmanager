# Mod Manager

一款简洁高效的 MOD 管理工具，帮助你轻松管理游戏 MOD。

## 截图

![Screenshot](screenshot.png)

## 功能特性

### 角色管理
- 自动同步角色列表（来源于库洛第三方接口）
- 显示角色头像和 MOD 数量
- 按角色分类管理 MOD

### MOD 管理
- **启用/禁用**：一键切换 MOD 状态
- **互斥启用**：启用一个 MOD 时自动禁用同角色下其他 MOD
- **批量操作**：支持全部启用/全部禁用
- **喜爱功能**：标记喜欢的 MOD，爱心按钮切换状态
- **简介预览**：鼠标悬停查看 MOD 简介（自动读取 txt 文件）

### 预览功能
- 自动识别 MOD 预览图
- 支持 png/jpg/jpeg/gif 等多种图片格式

### 文件操作
- 打开 MOD 文件夹
- 打开应用所在文件夹

### 自定义配置
- 可自定义应用标题和名称
- 可自定义应用图标

## 使用方法

1. 运行 `ModManager.exe`
2. 点击「同步角色」获取角色列表
3. 选择角色查看其 MOD 列表
4. 点击按钮启用/禁用 MOD

## MOD 目录结构

```
mods/
├── 角色1/
│   ├── MOD_A/           # 已启用
│   ├── DISABLED_MOD_B/  # 已禁用
│   └── MOD_C/
│       └── readme.txt   # MOD 简介（可选）
├── 角色2/
│   └── ...
```

## 配置文件

`config.json` 支持以下配置：

```json
{
    "app_title": "Mod Manager",
    "app_name": "ModManager",
    "icon_path": "icon.ico"
}
```

## 开发

### 环境要求
- Python 3.x
- Flask
- Requests
- Waitress

### 运行开发模式
```bash
python app.py
```

### 打包
```bash
build.bat
```

## 技术栈

- **后端**: Flask + Waitress
- **前端**: HTML + CSS + JavaScript
- **打包**: PyInstaller

## License

MIT
