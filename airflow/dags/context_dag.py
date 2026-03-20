# airflow/dags/context_dag.py

# fmt: off
# isort: off

from datetime import datetime, timedelta

from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator

from context.transcribe import transcribe_audio
from context.summarize import summarize_transcript

# fmt: on
# isort: on

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 1, 1),
}

with DAG(
    'recording_dag',
    default_args=default_args,
    description='Transcribe and summarize audio files as they arrive',
    schedule_interval=timedelta(minutes=1),  # Poll frequently for new files
    catchup=False,
    tags=['context'],
    max_active_runs=1,
    max_active_tasks=2
) as dag:

    audio_sensor = FileSensor(
        task_id="wait_for_audio",
        # Relative to fs_conn_id root, or absolute
        filepath="data/audio/*.wav",
        fs_conn_id="fs_default",       # Define this connection in Airflow UI
        # Releases worker slot while waiting (async-like)
        mode="reschedule",
        poke_interval=30,              # Check every 30s
        timeout=60 * 60,               # Give up after 1 hour
    )

    transcript_sensor = FileSensor(
        task_id="wait_for_transcript",
        filepath="data/transcript/*.txt",
        fs_conn_id="fs_default",
        mode="reschedule",
        poke_interval=30,
        timeout=60 * 60,
    )

    task_transcribe = PythonOperator(
        task_id='transcribe_audio',
        python_callable=transcribe_audio,
        execution_timeout=timedelta(minutes=10)
    )

    task_summarize = PythonOperator(
        task_id='summarize_transcript',
        python_callable=summarize_transcript,
    )

    audio_sensor >> task_transcribe
    transcript_sensor >> task_summarize
