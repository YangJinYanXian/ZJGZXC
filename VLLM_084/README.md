### 【依赖】

```
vllm==0.8.4
transformers==4.51.3
```

【💡GLM-4-0414 注意事项💡】

#### 1. 启动报错

`2025-04-15` 已知 `vllm==0.8.4` 启动该模型会遇到 `F.linear(x, layer.weight, bias)` 中

`linear(): argument  'input' (position 1) must be Tensor not tuple` 的问题。[[16618\]](https://github.com/vllm-project/vllm/pull/16618)

直到fix被merge以前，请先手动将附件的 [glm4.py](https://www.modelscope.cn/models/tclf90/glm-z1-32b-0414-gptq-int8/file/view/master/glm4.py?status=1) 替换掉`vllm`项目中对应的文件

```
 ...lib路径.../vllm/model_executor/models/glm4.py
```

#### 2. 需使用V0推理模式

启动vllm之前，先设置环境变量

```
export VLLM_USE_V1=0
```

------

我来详细告诉你怎么**一步步创建 Dockerfile，构建一个新vllm镜像**，特别简单，跟写一个小文本文件一样！

### 第一步：进入你的工作目录

假设你刚才已经建了个目录，比如：

```bash
mkdir vllm-dockerfile-glm4
cd vllm-dockerfile-glm4
```

如果你还没建，现在建也行。

------

### 第二步：新建 Dockerfile 文件

在 `vllm-dockerfile-glm4` 目录里执行：

```bash
touch Dockerfile
```

这条命令就是**创建一个空的 Dockerfile**。

（或者你也可以用自己喜欢的编辑器，比如 `vim Dockerfile`、`nano Dockerfile`、或者 VSCode）

------

### 第三步：编辑 Dockerfile

然后把下面这段内容**写进**刚才的 `Dockerfile` 里：

```Dockerfile
# 用官方原版镜像作为基础
FROM vllm/vllm-openai:v0.8.4

# 把本地的 glm4.py 复制到容器对应位置，覆盖原来的
COPY glm4.py /path/to/here/glm4.py

# 设置环境变量
ENV VLLM_USE_V1=0
```

✅ 简单解释：

- `FROM` 是指定基础镜像（就是 vllm/vllm-openai:v0.8.4）
- `COPY` 是把你准备好的 `glm4.py` 复制进去
- `ENV` 是给容器内部设置环境变量

------

### 第四步：确认一下

你的目录结构应该是：

```bash
vllm-dockerfile-glm4/
├── Dockerfile
└── glm4.py
```

（就是和 `Dockerfile` 同目录下有个 `glm4.py`）

------

### 第五步：构建镜像

在 `vllm-dockerfile-glm4` 目录里运行：

```bash
docker build -t vllm-dockerfile-glm4:v0.8.4 .
```

docker build -f .v/Dockerfile -t myapp-dev .

注意最后的点 `.`，表示当前目录。

✅ 这就会打包出一个新的镜像叫 `vllm-dockerfile-glm4:v0.8.4`，里面已经替换好你的文件了！

你问得非常好！🌟

**这个命令里的最后那个点（`.`）其实是非常重要的，它的意思是：**

> **构建上下文（build context）是当前目录。**

#### 🔥 什么是 "构建上下文"？

构建镜像的时候，Docker 需要读取：

- 你的 Dockerfile
- 还有 Dockerfile 里面用到的其他文件（比如 COPY、ADD 的文件）

这些**必须**都在所谓的**构建上下文目录**里面。
 而这个点（`.`）就是告诉 Docker：

🧠 **“以当前目录为根目录，打包里面所有需要的文件。”**

#### 👀 具体来说，在这个命令里：

```bash
docker build -f ./docker/dev/Dockerfile -t myapp-dev .
```

拆开理解就是：

| 部分                         | 意思                                                         |
| ---------------------------- | ------------------------------------------------------------ |
| `-f ./docker/dev/Dockerfile` | 使用 `./docker/dev/Dockerfile` 这个文件作为 Dockerfile。     |
| `-t myapp-dev`               | 把生成的镜像叫做 `myapp-dev`。                               |
| `.`                          | 把当前目录（`.`）作为**构建上下文**，Docker可以访问这个目录里的所有文件。 |

#### ⚡️ 如果没有写点（`.`）会怎样？

- Docker根本不知道去哪找文件。
- 会报错，比如找不到 Dockerfile 里面 `COPY` 或 `ADD` 指令需要的源文件。

所以，这个点非常重要！！

#### 🧩 小扩展

其实，点（`.`）可以换成其他目录，比如：

```bash
docker build -f ./docker/dev/Dockerfile -t myapp-dev ./docker
```

这时候，构建上下文就是 `./docker` 目录了，不是当前目录。

但是一般来说，绝大多数时候大家都用点（`.`），最简单最方便。

------

### 第六步：用新镜像启动容器

```bash
docker run -d \
  --runtime nvidia \
  --gpus '"device=4,5,6,7"' \
  -v /models/ZhipuAI/GLM-Z1-32B-0414:/workspace/models \
  -v /log:/var/log/vllm \
  -p 8001:8000 \
  --ipc=host \
  --name vllm1 \
  vllm-dockerfile-glm4:v0.8.4 \
  --model /workspace/models \
  --max-num-batched-tokens 131072 \
  --tensor-parallel-size 4 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --api-key vllm \
  --served-model-name GLM-Z1-32B-0414
```

🐖（注意镜像名改成了 `vllm-dockerfile-glm4:v0.8.4`）

------

要不要我顺便也给你一版：如果以后想要改 `glm4.py`，**不用重新 build 镜像**的高级做法——**每次只改 glm4.py 文件，不用重新 build 镜像**，直接重启容器就能用新代码，那我们可以用 **docker-compose + 挂载 volume（卷）**的方法来搞，非常丝滑！

下面教你怎么做：

------

## 1. 准备目录结构

建议这样安排目录，比如：

```bash
vllm-dev/
├── docker-compose.yml
└── glm4.py   # 你本地要替换的新版 glm4.py
```

✅ `glm4.py` 就是你想要热更新的文件。

------

## 2. 写 docker-compose.yml 文件

新建一个文件叫 `docker-compose.yml`，内容写成这样：

```yaml
version: '3.8'

services:
  vllm:
    image: vllm/vllm-openai:v0.8.4
    container_name: vllm1
    runtime: nvidia
    environment:
      - VLLM_USE_V1=0
    ports:
      - "8001:8000"
    ipc: host
    volumes:
      - /models/ZhipuAI/GLM-Z1-32B-0414:/workspace/models
      - /log:/var/log/vllm
      - ./glm4.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/glm4.py
    command:
      --model /workspace/models
      --max-num-batched-tokens 131072
      --tensor-parallel-size 4
      --enable-auto-tool-choice
      --tool-call-parser hermes
      --api-key vllm
      --served-model-name GLM-Z1-32B-0414
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
              device_ids: ['4', '5', '6', '7']
```

✅ 核心改动：

- `volumes:` 里面用 `./glm4.py` **直接挂到** 容器的 `/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/glm4.py` 位置
- 这样每次只要你改了本地的 `glm4.py`，容器里实时生效！（重启一下容器即可）
- 还顺便把 `VLLM_USE_V1=0` 环境变量加上了。

------

## 3. 启动容器

在 `vllm-dev` 目录下，直接跑：

```bash
docker-compose up -d
```

✅ 就启动好了！

以后如果你改了本地的 `glm4.py`，只需要：

```bash
docker-compose restart
```

就能重新加载新的代码了！（**不用重新 build 镜像！**）

------

## 为什么这么做好？

| 项目       | 传统 build                     | 挂载热更新             |
| ---------- | ------------------------------ | ---------------------- |
| 开发体验   | 改一次文件就要重新 build，很慢 | 改完直接 restart，超快 |
| 适合场景   | 代码稳定、基本不改动           | 开发、调试、快速迭代   |
| 磁盘空间   | build 多次产生一堆镜像         | 占用少                 |
| 操作复杂度 | build + run 两步               | up + restart 超简单    |

------

# 🚀 进阶建议

如果你想要**修改多个文件一起挂载**，也可以挂整个目录，比如这样：

```yaml
volumes:
  - ./vllm-models/:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/
```

（注意对应目录结构）

------

