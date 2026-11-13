# -*- coding: utf-8 -*-
"""最小复现页：两个先后会话复用同一缓存 Taskflow，探针输出线程态。

探针：线程名 / paddle.in_dynamic_mode() / 当前 expected place。
用于定位 pass2 会话 'libpaddle.Tensor has no attribute numpy' 的根因。
启动：streamlit run scripts/mini_repro_app.py --server.port 8504
"""
import os
import sys
import threading

import paddle
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import core  # noqa: E402

TEXT = ("招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，"
        "熟悉Spring Boot和MySQL，具备扎实的后端开发能力，英语读写良好。")


@st.cache_resource(show_spinner=False)
def get_model():
    return core.create_entity_taskflow(
        task_path=core.resolve_ckpt("./checkpoint/uie_jd_v2"),
        device="cpu", schema=core.ENTITY_SCHEMA_V2, position_prob=0.5)


st.title("mini repro")
st.write("thread=%s" % threading.current_thread().name)
st.write("dygraph=%s" % paddle.in_dynamic_mode())
try:
    st.write("place=%s" % paddle.framework._current_expected_place())
except Exception as exc:  # noqa: BLE001
    st.write("place_probe_fail=%s" % exc)

if st.button("run"):
    core.ensure_dygraph()
    ie = get_model()
    try:
        r = ie(TEXT)
        st.write("PREDICT_OK entities=%d" %
                 sum(len(v) for d in r for v in d.values()))
    except Exception as exc:  # noqa: BLE001
        st.write("PREDICT_FAIL %s: %s" % (type(exc).__name__, exc))
