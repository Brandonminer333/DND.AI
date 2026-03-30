"""Unit tests for `airflow/dags/context_dag.py`."""

from pathlib import Path


def test_recording_dag_loads_and_task_ids():
    from airflow.models import DagBag

    dag_folder = Path(__file__).resolve().parents[2] / "airflow" / "dags"
    dag_bag = DagBag(dag_folder=str(dag_folder), include_examples=False)
    assert not dag_bag.import_errors, dag_bag.import_errors

    # Use `dag_bag.dags` — `get_dag()` can re-import ORM models and trip SQLAlchemy
    # duplicate-table errors when Airflow is exercised twice in one pytest process.
    dag = dag_bag.dags.get("recording_dag")
    assert dag is not None
    task_ids = {t.task_id for t in dag.tasks}
    assert "wait_for_audio" in task_ids
    assert "transcribe_audio" in task_ids
    assert "summarize_transcript" in task_ids
