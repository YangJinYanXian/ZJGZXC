# 用官方原版镜像作为基础
FROM vllm/vllm-openai:v0.8.4

# 把本地的 glm4.py 复制到容器对应位置，覆盖原来的
COPY glm4.py /usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/glm4.py

# 设置环境变量
ENV VLLM_USE_V1=0
