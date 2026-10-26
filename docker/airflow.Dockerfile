FROM apache/airflow:2.10.5-python3.12
# Airflow pins SQLAlchemy 1.4 and its own pandas and numpy. The framework runs on
# those versions, so only the two packages Airflow does not ship are added.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    great-expectations==1.24.1 scipy
