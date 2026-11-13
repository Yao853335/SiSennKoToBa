# -*- coding: utf-8 -*-
"""第 12 周联调问题定位：跨线程复用 Taskflow 复现实验。

现象：Streamlit 服务中，会话 1 点击「开始抽取」正常；会话 2（新会话线程）
复用 @st.cache_resource 缓存的同一 Taskflow 时，paddlenlp 内部
input_ids.numpy() 抛 AttributeError: 'paddle.base.libpaddle.Tensor'
object has no attribute 'numpy'。

假设：Taskflow 的推理 DataLoader 与创建线程绑定，跨线程调用即触发。
验证：主线程创建+推理 -> 正常；新线程推理同一对象 -> 是否复现。
"""
import os
import sys
import threading
import traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import core  # noqa: E402

TEXT = ("招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，"
        "熟悉Spring Boot和MySQL，具备扎实的后端开发能力，英语读写良好。")


def try_predict(ie, tag):
    try:
        r = ie(TEXT)
        n = sum(len(v) for d in r for v in d.values())
        print("[%s] OK 实体数=%d" % (tag, n))
        return True
    except Exception as exc:
        print("[%s] FAIL %s: %s" % (tag, type(exc).__name__, exc))
        traceback.print_exc(limit=3)
        return False


def main():
    ie = core.create_entity_taskflow(task_path=core.resolve_ckpt("./checkpoint/uie_jd_v2"),
                                     device="cpu", schema=core.ENTITY_SCHEMA_V2,
                                     position_prob=0.5)
    ok_main = try_predict(ie, "创建线程-第1次")
    ok_main2 = try_predict(ie, "创建线程-第2次")

    result = {}

    def worker():
        result["t"] = try_predict(ie, "新线程-复用")

    t = threading.Thread(target=worker)
    t.start()
    t.join(180)

    print("结论：主线程 %s/%s；新线程 %s" % (
        ok_main, ok_main2, result.get("t", "超时/未执行")))


if __name__ == "__main__":
    main()
