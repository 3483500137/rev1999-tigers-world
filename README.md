# 老虎的金黄 · 自由漫游

依据 [VioletWilde/1999-demo](https://github.com/VioletWilde/1999-demo) 第四章“老虎的金黄”沙盘，在 Blender 5.1 中重建的可探索三维场景，使用 Three.js 在浏览器中运行。

**在线体验：https://3483500137.github.io/rev1999-tigers-world/**

## 体验

- 总览：鼠标拖动旋转、滚轮缩放、右键平移。
- 进入林地：WASD 移动、鼠标环视、Shift 加速；包含建筑墙体碰撞和地图边界。
- 自由飞行：WASD 移动、E 上升、Q 下降。
- Esc 释放鼠标；R 回到初始视角；H 隐藏或恢复界面。
- 手机使用左侧方向按钮移动、右侧场景拖动环视。
- 原版沙盘：复用全部 11 张原始贴图、UV 和第四章 23 幕场景数据，可与重建空间对照。
- 城堡、东侧居所与林间道路有快捷跳转；小地图显示当前相机位置。

## 场景与复建范围

三维区域约 320 × 160 米。中央建筑已按 a03 原始贴图修正为西侧一个可见房间、东侧三个不同的切面房间：西侧和东侧下层是带靠背、侧框的座具形状，中层为横向桌面组合，上层为长条深色陈设，不再使用重复床铺代替。物件用途不作未经来源确认的命名。各组对象的 glTF extras 记录来源贴图、像素参考范围和形状 ID。

本轮还修正了塔楼竖向凹槽、礼堂下方窗列、分叉挑出屋顶、分段半圆看台与悬挂圆环，北侧通用球状岩石已替换为复用 a01 山体贴图的连续山面。针叶林颜色取自原始贴图，背面连廊与楼梯保留可移动通路。网页启用柔和阴影与室内补光，树木实例化、静态建筑按材质合并以减少绘制开销。

参考仓库提供的是沙盘图层与 UV，并非游戏完整 3D 模型。以上是已核对和修正的局部，不能视为整张场景完整还原：外围建筑、道路和植被的精确布局、全局比例、全部室内细件、山体几何与光照仍有差异，也未补齐参考图中的所有设施。可见原图才是验收基准；三维模式目前不是已验证的逐像素或逐面复制，测试通过也不代表视觉完全一致。无法获取的隐藏面、背面通道采用适配设计，原版沙盘模式保留来源贴图与原始布局用于对照。

## 本地开发

```sh
npm ci
npm run dev
npm test
npm run build
```

## Blender 源文件

- `blender/tigers-world.blend`：可编辑项目，包含三维重建和原版沙盘两个场景，图片已打包进文件。
- `blender/build_world.py`：可重复建模脚本。打开 Blender 后，在 Python Console 中执行：

```python
p = '/absolute/path/to/repo/blender/build_world.py'
exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), {'__file__': p})
```

先打开现有 `blender/tigers-world.blend` 再运行脚本。它直接替换该文件中的三维重建和原版沙盘场景，覆盖原路径，同时输出 `public/models/tigers-world.glb` 与导航数据 `public/data/world.json`；不会另建 `.blend` 文件，也不会清除无关场景。导航数据包含分层墙体碰撞、房间地板与楼梯斜坡。

## GitHub Pages

发布分支为 `gh-pages`，内容来自 `npm run build` 生成的静态 `dist`。Vite 使用相对路径，因此支持项目子目录。无需后端、模型 API、账号或服务端凭据。

更新后运行 `node scripts/publish-pages.mjs` 可构建并提交新的 `gh-pages` 发布分支。该脚本仅更新已配置的 `origin`，不会创建新仓库。

需要 Node.js、Git 及已登录的 GitHub CLI。若 Git 连接不可用，可以先运行 `npm run build`，再执行 `node scripts/publish-api.mjs dist gh-pages`，通过 GitHub API 发布；此备用脚本的目标固定为本项目仓库。

## 来源与许可

来源固定在提交 [`1d83ddc454c9c7c193e4c458412db42bfc5d8031`](https://github.com/VioletWilde/1999-demo/tree/1d83ddc454c9c7c193e4c458412db42bfc5d8031)，仅提取第四章相关资源。`public/data/sources.json` 记录每张贴图的路径、大小和 SHA-256。

本项目新编写的网页程序和 Blender 建模脚本以 MIT 许可开源。游戏贴图、角色、文本及从游戏素材衍生的模型不属于 MIT 许可范围，其权利归原权利人；参考数据的整理归属保留给 VioletWilde。项目为非官方场景研究演示。详细范围见 `LICENSE` 和 `ASSET_NOTICE.md`。
