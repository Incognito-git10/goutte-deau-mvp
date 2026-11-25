# Image légère pour l'API (python slim, pas de GPU)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pandas numpy scikit-learn joblib requests
COPY src/ src/
COPY api/ api/
COPY data/ data/
COPY models/ models/
ENV PYTHONPATH=src
RUN python -m goutte.collecte --csv data/export_infoclimat.csv
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
