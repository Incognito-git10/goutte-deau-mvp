export PYTHONPATH := src

.PHONY: collecte entrainement rapport tests tout api ui docs

collecte:
	python -m goutte.collecte --csv data/export_infoclimat.csv

entrainement:
	python -m goutte.entrainement

rapport:
	python -m goutte.rapport

tests:
	pytest -q

tout: collecte entrainement rapport tests

api:
	uvicorn api.main:app --reload --port 8000

ui:
	streamlit run app/streamlit_app.py

docs:
	python docs/planning_budget.py
	dot -Tpng -Gdpi=150 docs/architecture.dot -o docs/architecture.png
	dot -Tpng -Gdpi=150 docs/composants.dot -o docs/composants.png
	dot -Tpng -Gdpi=150 docs/modele_donnees.dot -o docs/modele_donnees.png
