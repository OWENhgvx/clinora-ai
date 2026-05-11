# Clinora 本地启动

## 后端（FastAPI）

在仓库根目录执行：

```bash
cd clinora-backend
python3 -m venv .venv

source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

如需首次灌入向量库文献（耗时长，且依赖 `.env` 等配置），可另行执行：`python ingest.py`。

## 前端（Vite）

**需要 Node.js 20 及以上**（过旧会导致 `vite` / 依赖报错）。在仓库根目录执行：

```bash
cd clinora-frontend
npm install
npm run dev
```

终端提示的本地地址通常是 `http://localhost:5173/`。开发环境默认会把 API 发到 `http://localhost:8000`，请先启动后端。

若后端端口或地址不同，可临时指定：

```bash
VITE_BACKEND_URL=http://127.0.0.1:8000 npm run dev
```
