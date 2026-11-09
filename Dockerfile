# Optional: run without installing Python.   docker build -t strentor-assistant . && docker run -p 8501:8501 strentor-assistant
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Pre-download the embedding model at build time so the container works offline afterwards.
RUN python scripts/warmup.py
ENV TEAM_PASSWORD=evaluator
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
