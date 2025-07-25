FROM streamlit/streamlit:latest

# 启用 multiverse 存储库并安装 unrar
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-add-repository multiverse && \
    apt-get update && \
    apt-get install -y unrar

# 复制项目文件
COPY . /app
WORKDIR /app
