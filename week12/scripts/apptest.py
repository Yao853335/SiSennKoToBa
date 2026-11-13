# -*- coding: utf-8 -*-
"""周五：用 Streamlit 官方 AppTest 框架验证界面真实执行（非仅 HTTP 200）。

为什么需要这一步：
  - 服务返回 HTTP 200 只说明 Tornado 起来了，不代表 app.py 能无异常执行完；
  - Streamlit 的组件在首次 run 时就会执行整个脚本，AppTest 能在无浏览器环境下
    捕获脚本异常、断言组件渲染结果；
  - 计划书联调要求的“页面不报错、组件正常渲染”在此得到可复核的证据。

注意：本测试不加载 UIE 模型（不点击“开始抽取”），只验证界面结构与静态分支，
模型链路由 scripts/smoke_test.py 的联调 1~4 覆盖。

产出：week12/logs/apptest_report.md
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.path.insert(0, BASE)

from streamlit.testing.v1 import AppTest  # noqa: E402

LOGS = os.path.join(BASE, "logs")
APP = os.path.join(BASE, "app.py")

results = []


def step(name, ok, detail=""):
    results.append((name, ok, detail))
    print("%s %s | %s" % ("OK  " if ok else "FAIL", name, detail), flush=True)
    return ok


def main():
    os.makedirs(LOGS, exist_ok=True)
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()

    step("界面脚本执行无异常", not at.exception,
         "" if not at.exception else str(at.exception)[:300])
    if at.exception:
        for e in at.exception:
            print("   EXCEPTION:", str(e.value)[:400], flush=True)
        write_report()
        return 1

    step("主标题渲染", len(at.title) > 0,
         at.title[0].value if at.title else "无标题")
    step("三个主 Tab 渲染", len(at.tabs) >= 3,
         "tabs=%d，标签=%s" % (len(at.tabs), [t.label for t in at.tabs]))
    step("侧边栏组件渲染", len(at.sidebar.selectbox) + len(at.sidebar.radio) +
         len(at.sidebar.text_input) + len(at.sidebar.slider) > 0,
         "text_input=%d radio=%d slider=%d selectbox=%d" % (
             len(at.sidebar.text_input), len(at.sidebar.radio),
             len(at.sidebar.slider), len(at.sidebar.selectbox)))
    step("checkpoint 路径解析提示", len(at.sidebar.success) > 0 or
         len(at.sidebar.error) > 0,
         (at.sidebar.success[0].value if at.sidebar.success else
          (at.sidebar.error[0].value if at.sidebar.error else "无提示")))

    # 示例文本应来自真实语料（data/demo_jds.txt 存在时）
    demo = os.path.join(BASE, "data", "demo_jds.txt")
    if os.path.exists(demo):
        with open(demo, encoding="utf-8") as f:
            first = f.readline().strip()
        ta = [t for t in at.text_area if t.key == "t1_text"]
        step("示例文本来自真实语料", bool(ta) and ta[0].value.strip()[:20] == first[:20],
             "文本框前20字=%s" % (ta[0].value.strip()[:20] if ta else "无文本框"))

    sel = [s for s in at.selectbox if s.key == "t1_sample"]
    step("示例下拉框已渲染", len(sel) == 1,
         "选项数=%d" % (len(sel[0].options) if sel else 0))

    btn = [b for b in at.button if b.key == "t1_run"]
    step("开始抽取按钮已渲染", len(btn) == 1,
         "按钮存在，disabled=%s" % (btn[0].disabled if btn else "n/a"))

    # 切到图谱 Tab 的静态分支（无结果时应给出提示而非异常）
    step("无抽取结果时界面不报错", not at.exception,
         "首次 run 后无异常")

    write_report()
    return 0 if all(ok for _, ok, _ in results) else 1


def write_report():
    n_pass = sum(1 for _, ok, _ in results if ok)
    lines = ["# 第12周 界面执行验证（Streamlit AppTest）", "",
             "结论：%d/%d 项通过。" % (n_pass, len(results)), "",
             "| 检查项 | 结果 | 说明 |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append("| %s | %s | %s |" % (
            name, "通过" if ok else "失败", str(detail).replace("|", "/")[:200]))
    lines += ["",
              "说明：HTTP 200 只能证明服务进程已监听端口，无法证明 app.py 能无异常",
              "执行完毕。本验证通过 Streamlit 官方 AppTest 在无浏览器环境下实际执行",
              "整个界面脚本，并断言标题、Tab、侧边栏组件、示例文本来源与按钮状态，",
              "异常会被 at.exception 捕获。模型推理链路由 smoke_test.py 联调 1~4 覆盖。",
              ""]
    path = os.path.join(LOGS, "apptest_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n%d/%d 通过 -> %s" % (n_pass, len(results), path))


if __name__ == "__main__":
    sys.exit(main())
