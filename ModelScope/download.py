#模型下载
from modelscope import snapshot_download
model_dir = snapshot_download('tclf90/glm-z1-32b-0414-gptq-int8', cache_dir='/root/YangXian/models')