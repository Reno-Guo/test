FROM streamlit/streamlit:latest

# 更新软件源，启用 non-free 存储库
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security bullseye-security main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y unrar

# 安装 Python 依赖（可选，Streamlit Cloud 会自动处理 requirements.txt）
COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

# 复制项目文件
COPY . /app
