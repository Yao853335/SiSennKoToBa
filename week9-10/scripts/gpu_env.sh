# GPU 训练环境：加载 CUDA 11 运行库 + 项目模型缓存
# 用法: source /d/SiSennKoToBa/week9-10/scripts/gpu_env.sh
NVB=/d/anaconda/envs/uie_gpu/Lib/site-packages/nvidia
export PATH="$NVB/cublas/bin:$NVB/cuda_runtime/bin:$NVB/cudnn/bin:$NVB/cuda_nvrtc/bin:$PATH"
export PYTHONPATH=
export PYTHONNOUSERSITE=1
export PPNLP_HOME="D:\\SiSennKoToBa\\.cache\\paddlenlp"
export UIPY=/d/anaconda/envs/uie_gpu/python.exe
