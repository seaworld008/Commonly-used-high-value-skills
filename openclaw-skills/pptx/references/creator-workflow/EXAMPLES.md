<!-- Copyright (c) 2026 seaworld008 -->
<!-- SPDX-License-Identifier: MIT -->

# 两条制作路线的合成示例

所有名称、数量和结论均为演示用合成材料，不对应真实组织或业绩。
示例命令从仓库根目录运行，临时文件全部放在已有 TMPDIR 中。

## 生成一份小数据与两种图表
以下代码生成 UTF-8 CSV，不需要联网：
```sh
python -c 'import os; from pathlib import Path; root=Path(os.environ["TMPDIR"]); (root/"synthetic-requests.csv").write_text("team,requests,completed\nTraining,14,11\nSupport,9,7\nPlanning,6,4\n", encoding="utf-8")'
python skills/office-white-collar/pptx/scripts/chartkit.py \
  --data "$TMPDIR/synthetic-requests.csv" --type bar --x team \
  --y requests,completed --out "$TMPDIR" --filename synthetic-requests.svg \
  --title "Synthetic pilot: requests and completions (count)"
python skills/office-white-collar/pptx/scripts/chartkit.py \
  --data "$TMPDIR/synthetic-requests.csv" --type barh --x team \
  --y requests --out "$TMPDIR" --filename synthetic-requests.png \
  --title "Synthetic pilot: requests by team (count)"
```
依赖缺失时命令应失败并给出错误；不要用占位图片替代成功结果。
SVG 包含类别、系列和标题文本，PNG 尺寸应为 1200 × 675。
两个图都应显示 Training 14、Support 9、Planning 6，不能按字母顺序意外重排。
这些图是静态资产；原生可编辑图表示例见[制作路线](ORCHESTRATION_PPTX.md)。

## API 示例
当需要从计算结果直接绘图时，可把脚本所在目录加入当前进程的模块搜索路径。
```python
import os
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, "skills/office-white-collar/pptx/scripts")
from chartkit import render_chart

frame = pd.DataFrame({"step": ["Opening", "Added", "Removed"], "change": [20, 5, -3]})
render_chart(frame, "waterfall", "step", ["change"],
             "Synthetic balance changes (count)", Path(os.environ["TMPDIR"]) / "synthetic-waterfall.svg")
```
三条变化累计后为 22；最后一条柱从 25 向下至 22。
如输入缺失值、无穷大或多列 waterfall，必须报错且保留原有目标文件。

## 由数据形成叙事
合成 brief：培训协调员要决定下一轮试点先支持哪个团队。
S01 提出决策；S02 展示请求与完成量；S03 解释样本规模和局限；S04 给出试点安排。
请求最多不能直接证明业务价值最大。行动建议应注明这是合成演示，
真实决策还需处理时长、收益、容量及时间窗口等证据。
页脚标记证据 E-SYN-01，台账保存 CSV、字段含义和生成方式。

## Marp Markdown 快速稿
把以下内容保存为 TMPDIR 中的 Markdown 文件。此处只提供源稿，
导出前按[制作路线](ORCHESTRATION_PPTX.md)检查实际安装的 Marp 版本与 --help。
```markdown
---
marp: true
size: 16:9
---
# 先验证培训团队的试点需求
合成演示：用于讨论页面顺序，不代表真实业务建议。

---
# 培训团队请求量为 14 项
支持团队 9 项，计划团队 6 项。
来源：E-SYN-01，合成数据；单位：请求数。

---
# 下一步需要容量与收益证据
现有数据只说明数量，无法判断投入回报。
先补充处理时长与可用人员，再决定扩展范围。
```
快速稿验证论证与节奏；正式原生 PPTX 仍按对象策略制作并验收。

## 验收预期
图表数值与 CSV 一致；标题没有把请求数说成收益。
柱形基线为零，标签可读，来源标识清楚。
PPTX 的标题可单独编辑，原生图表数据改动能更新绘图。
未运行桌面检查时，记录“待目标应用验收”，不能引用此示例宣称通过。
