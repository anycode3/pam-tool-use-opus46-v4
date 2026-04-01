# PAM版图优化工具 - 设计规格文档

## 1. 项目概述

### 1.1 背景
在PAM（功率放大器模块）设计过程中，用户在已有版图做了EM仿真后，发现性能未达预期，需要调整版图中相关器件的值。本工具旨在自动化版图优化流程，提供从版图上传、解析、器件识别、器件修改到DRC检测的全流程支持。

### 1.2 使用场景
- 多用户轻量级Web工具（无需复杂权限管理，文件隔离即可）
- 支持GDS和DXF两种版图格式（同等优先级）

### 1.3 核心工作流
1. 上传版图文件（GDS/DXF）
2. 解析并可视化版图
3. 配置层映射（将解析层名映射到ME1/ME2/TFR/VA1/GND等标准层）
4. 触发器件识别（电感L、电容C、电阻R、焊盘PAD、地孔GND）
5. 选定器件，修改器件值
6. 预览修改（新旧版图差异对比）
7. DRC规则检测
8. 检测通过后应用修改，下载新版图

## 2. 技术架构

### 2.1 技术栈
- **前端**: React 18 + TypeScript + deck.gl + Ant Design 5 + Zustand + Vite
- **后端**: Python + FastAPI + gdstk(GDS解析) + ezdxf(DXF解析)
- **存储**: 本地文件系统

### 2.2 架构图
```
┌─────────────────────────────────────────────────┐
│                   Frontend (React)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ File     │ │ Layout   │ │ Device Panel     │ │
│  │ Upload   │ │ Viewer   │ │ (识别/修改/对比)  │ │
│  │ Panel    │ │ (deck.gl)│ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Layer    │ │ Layer    │ │ DRC Rules &      │ │
│  │ Control  │ │ Mapping  │ │ Results Panel    │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────┬──────────────────────────────┘
                   │  REST API (JSON)
┌──────────────────▼──────────────────────────────┐
│                Backend (FastAPI)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Parser   │ │ Device   │ │ Layout Modifier  │ │
│  │ (gdstk/  │ │ Recog-   │ │ (几何修改+       │ │
│  │  ezdxf)  │ │ nizer    │ │  版图重生成)     │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Layer    │ │ DRC      │ │ File Storage     │ │
│  │ Manager  │ │ Engine   │ │ (本地文件系统)    │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 2.3 数据存储结构
```
storage/
  projects/
    {project_id}/
      original.gds           # 原始上传文件
      layout_data.json        # 解析后的几何数据缓存
      layer_mapping.json      # 层映射配置
      devices.json            # 器件识别结果
      modified.gds            # 修改后的版图
      drc_rules.json          # DRC规则
      drc_results.json        # DRC检测结果
```

## 3. 分阶段实施计划

| 阶段 | 内容 | 核心交付 |
|------|------|---------|
| P1 | 基础框架 + 文件上传解析 + 版图可视化 | 上传GDS/DXF，解析后在deck.gl中显示，支持缩放/平移/选择 |
| P2 | 分层管理 + 层映射配置 | 分层过滤显示，层名到ME1/ME2/TFR/VA1/GND的映射 |
| P3 | 器件识别 | 识别电感L、电容C、电阻R、焊盘PAD、地孔GND，显示器件指标 |
| P4 | 器件修改 + 版图重生成 + 差异对比 | 修改器件值，自动/手动调整几何，新旧版图对比 |
| P5 | DRC规则定义 + 检测 | 界面定义+文件上传DRC规则，执行检测并展示结果 |

## 4. API接口设计

### 4.1 P1: 文件管理与版图数据

```
POST   /api/projects/upload          # 上传版图文件(GDS/DXF)，返回project_id
GET    /api/projects                  # 获取项目列表
GET    /api/projects/{id}             # 获取项目详情
DELETE /api/projects/{id}             # 删除项目

GET    /api/projects/{id}/layout      # 获取解析后的几何数据(JSON)
       Query params:
         layers: string[]            # 可选，过滤指定层
         bbox: [x1,y1,x2,y2]        # 可选，只返回视口范围内的数据
```

**layout 返回数据结构**:
```json
{
  "bounds": {"min_x": 0, "min_y": 0, "max_x": 1000, "max_y": 800},
  "layers": [
    {"layer": 1, "datatype": 0, "name": "1/0", "polygon_count": 150}
  ],
  "geometries": [
    {
      "id": "poly_001",
      "type": "polygon",
      "layer": 1,
      "datatype": 0,
      "points": [[0,0],[100,0],[100,50],[0,50]],
      "properties": {}
    }
  ]
}
```

### 4.2 P2: 层管理

```
GET    /api/projects/{id}/layers              # 获取所有层信息
PUT    /api/projects/{id}/layer-mapping       # 保存层映射配置
       Body: {"mappings": {"1/0": "ME1", "2/0": "ME2", ...}}
GET    /api/projects/{id}/layer-mapping       # 获取层映射配置
```

### 4.3 P3: 器件识别

```
POST   /api/projects/{id}/devices/recognize   # 触发器件识别
       Body: {"method": "geometry"|"hybrid"}
GET    /api/projects/{id}/devices             # 获取识别结果列表
GET    /api/projects/{id}/devices/{dev_id}    # 获取单个器件详情
```

**器件数据结构**:
```json
{
  "id": "dev_001",
  "type": "inductor",
  "value": 2.5,
  "unit": "nH",
  "turns": 3,
  "layers": ["ME1", "ME2"],
  "bbox": [100, 200, 300, 400],
  "polygon_ids": ["poly_001", "poly_002"],
  "ports": [
    {"id": "p1", "position": [100, 300], "layer": "ME1"},
    {"id": "p2", "position": [300, 300], "layer": "ME2"}
  ],
  "metrics": {
    "area": 20000,
    "width": 10,
    "length": 50
  }
}
```

### 4.4 P4: 器件修改

```
POST   /api/projects/{id}/devices/{dev_id}/modify
       Body: {
         "new_value": 5.0,
         "mode": "auto"|"manual",
         "manual_params": {"width": 20, "length": 100}
       }
       Response: 修改预览(新旧对比数据)

POST   /api/projects/{id}/apply-modifications
       Body: {"modifications": ["mod_001", ...]}
       Response: 新版图下载链接

GET    /api/projects/{id}/diff         # 获取新旧版图差异
GET    /api/projects/{id}/download     # 下载修改后的版图文件
```

### 4.5 P5: DRC检测

```
POST   /api/projects/{id}/drc/rules          # 上传/定义DRC规则
       Body: {
         "rules": [...],
         "rule_file": "base64..."
       }
GET    /api/projects/{id}/drc/rules          # 获取当前DRC规则
POST   /api/projects/{id}/drc/run            # 执行DRC检测
GET    /api/projects/{id}/drc/results        # 获取DRC检测结果
```

**DRC规则结构**:
```json
{
  "rules": [
    {
      "id": "rule_001",
      "type": "min_width",
      "layer": "ME1",
      "value": 5.0,
      "description": "ME1最小线宽"
    },
    {
      "id": "rule_002",
      "type": "min_spacing",
      "layer1": "ME1",
      "layer2": "ME2",
      "value": 3.0,
      "description": "ME1-ME2最小间距"
    }
  ]
}
```

## 5. 器件识别算法

### 5.1 识别策略

提供两种识别方式:

**方式1: 基于几何特征的规则识别（主推）**

按层归类多边形，根据几何特征和跨层关系匹配器件。

**方式2: 基于空间聚类的辅助识别**

使用DBSCAN空间聚类将相邻多边形分组，对每组应用器件规则匹配，作为方式1的补充。

### 5.2 识别顺序与排他性

**关键约束**: 电感和电容都存在于ME1和ME2层，必须保证排他性识别，避免重复。

**识别顺序**: 先电感后电容（电感螺旋形状辨识度更高）

```
Step 1: 先识别电感(螺旋形状) → 标记已归属多边形
Step 2: 在剩余未标记多边形中识别电容(矩形平板重叠)
Step 3: 识别电阻(TFR层，与上述无冲突)
Step 4: 识别焊盘PAD(ME1+ME2+VA1穿透，排除已标记)
Step 5: 识别地孔GND(GND+ME1+ME2+VA1穿透，排除已标记)
```

每个多边形一旦被归属到某器件，即标记为"已使用"，后续识别不再考虑。

### 5.3 器件匹配规则

| 器件类型 | 匹配条件 | 值计算 |
|---------|---------|--------|
| 电感 L | ME1和/或ME2层有螺旋形状的连通区域，路径角度累积>360° | 基于内径、外径、圈数、线宽 |
| 电容 C | ME1和ME2层在同区域有矩形大面积平行重叠 | C = ε × A / d |
| 电阻 R | 仅TFR层的矩形条状区域，长宽比较大 | R = ρ × L / (W × t) |
| 焊盘 PAD | ME1+ME2+VA1三层同位置有多边形 | - |
| 地孔 GND | GND+ME1+ME2+VA1四层同位置有多边形 | - |

### 5.4 器件值修改的几何变换

| 器件 | 修改方式 | 几何变换 |
|------|---------|---------|
| 电容 C | 改变值→改变面积 | 保持一边不变按比例缩放另一边，或等比例缩放 |
| 电阻 R | 改变值→改变长/宽 | 保持宽度不变调长度，或保持长度不变调宽度 |
| 电感 L | 改变值→改变圈数/间距/线宽 | 增减螺旋圈数，或调整内外径 |

修改约束:
- 端口位置尽量不变（保持连接关系）
- 修改区域不与相邻器件重叠
- 满足DRC规则

## 6. 前端组件设计

### 6.1 页面布局
```
┌────────────────────────────────────────────────────────┐
│  Header: 项目名称 | 文件信息 | 操作按钮                  │
├────────┬───────────────────────────────┬───────────────┤
│        │                               │               │
│ Left   │     Center                    │   Right       │
│ Panel  │     Layout Viewer (deck.gl)   │   Panel       │
│        │                               │               │
│ - 层   │     缩放/平移/选择            │  - 器件列表    │
│   列表 │                               │  - 器件详情    │
│ - 层   │                               │  - 修改面板    │
│   映射 │                               │  - DRC面板     │
│ - 过滤 │                               │               │
│        │                               │               │
├────────┴───────────────────────────────┴───────────────┤
│  Bottom: 状态栏 | 坐标 | 缩放比例                       │
└────────────────────────────────────────────────────────┘
```

### 6.2 核心组件

| 组件 | 功能 |
|------|------|
| `FileUpload` | 拖拽/点击上传GDS/DXF，显示上传进度 |
| `LayoutViewer` | deck.gl渲染版图，支持缩放/平移/多边形选择高亮 |
| `LayerPanel` | 显示层列表，切换层可见性，过滤显示 |
| `LayerMappingDialog` | 配置层名到ME1/ME2/TFR/VA1/GND的映射 |
| `DeviceList` | 器件列表，点击定位到版图位置 |
| `DeviceDetail` | 显示器件类型、值、圈数等指标 |
| `DeviceModifyPanel` | 修改器件值，选择自动/手动模式 |
| `DiffViewer` | 新旧版图对比显示，高亮差异区域 |
| `DrcRulesPanel` | 定义/上传DRC规则 |
| `DrcResultsPanel` | 显示DRC检测结果，点击定位到违规位置 |

## 7. 版图分层规则

| 层名 | 用途 | 说明 |
|------|------|------|
| ME1 | 金属层1 | 金属走线层 |
| ME2 | 金属层2 | 金属走线层 |
| TFR | 电阻层 | 薄膜电阻，与ME1同层 |
| VA1 | 过孔层 | ME1和ME2之间的连通 |
| GND | 地层 | 接地层 |
