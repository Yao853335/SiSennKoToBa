# 第12周联调缺陷记录：跨会话复用缓存模型崩溃（已修复）

## 现象
- 会话 1 点击「开始抽取」正常（模型在本会话线程创建并推理）；
- 会话 1 结束后，会话 2（Streamlit 新会话线程）复用 `@st.cache_resource`
  缓存的同一 Taskflow 点击抽取，服务端抛：
  `AttributeError: 'paddle.base.libpaddle.Tensor' object has no attribute 'numpy'`
  （paddlenlp information_extraction.py:975 `copy_from_cpu(input_ids.numpy())`），
  界面无结果返回，表现为按钮点击后永久转圈。

## 定位过程
1. 纯 Python 跨线程复现脚本（scripts/repro_thread_issue.py）：主线程创建 +
   新线程复用，**不复现** → 排除"线程本身"单一因素；
2. 最小 Streamlit 复现页（scripts/mini_repro_app.py）+ 两会话探针
   （scripts/probe_mini_sessions.py）探针字段：线程名 /
   `paddle.in_dynamic_mode()` / 当前 place；
3. 探针结果（修复前 logs/mini_repro_probe.txt 旧版）：
   会话 1 线程 `dygraph=True` 推理 OK；会话 2 新线程 `dygraph=False` →
   DataLoader 产出静态图 Tensor（`libpaddle.Tensor`，无 `.numpy()`）→ 崩溃。

## 根因
paddle 的动态图/静态图开关是**线程级**状态。Taskflow 的 paddle-inference
predictor 在创建线程的动态图上下文下初始化；新会话线程默认 `dygraph=False`，
paddlenlp 推理链路上的 DataLoader 按静态图模式返回张量，与
`copy_from_cpu(input_ids.numpy())` 的动态图假设冲突。

## 修复
core.py 新增 `ensure_dygraph()`：推理前在当前线程检测
`paddle.in_dynamic_mode()`，为 False 时调用 `paddle.disable_static()`
（paddle 2.x 进入动态图模式的 API；2.6.2 无 `enable_dynamic_mode`）。
app.py 在抽取循环前调用一次；调用幂等，创建线程内无副作用。

## 验证
- 修复后两会话探针：会话 1 `PREDICT_OK entities=6`，会话 2
  `PREDICT_OK entities=6`（会话 2 线程态仍为 `dygraph=False`，
  由 ensure_dygraph 在推理前纠正）；
- 主系统回归（scripts/take_ui_screenshots_pass2.py）：会话 1 单条抽取建立缓存 →
  会话 2 复用缓存对 8 条 JD 抽取成功（47 实体、9 三元组），截图齐全。

## 结论与教训
- Streamlit + paddle 组合下，**任何跨会话共享的 paddle 推理对象都必须在使用
  线程内显式对齐图模式开关**，`@st.cache_resource` 只解决"加载一次"，
  不解决"线程态一致"；
- 联调必须覆盖"第二个用户/第二个会话"场景：单会话自测全绿并不代表系统可用，
  这正是计划书强调"核心风险在联调时的状态管理"的具体体现。
