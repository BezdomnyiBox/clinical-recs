import time
from datetime import datetime

from sqlalchemy import inspect, select

from app.db import SessionLocal, engine
from app.models import Document, Job
from app.pipeline.graph import graph


def claim_job():
    with SessionLocal() as s:
        job = s.scalars(
            select(Job)
            .where(Job.status == "queued")
            .order_by(Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if not job:
            return None
        job.status, job.started_at = "running", datetime.now()
        s.commit()
        return job.id, job.document_id


def run(job_id: int, doc_id: int):
    err = None
    try:
        graph.invoke({"document_id": doc_id, "job_id": job_id})
    except Exception as e:  # сбой не маскируется под «утверждения не найдены»
        err = f"{type(e).__name__}: {e}"
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        job.finished_at = datetime.now()
        job.status, job.error = ("error", err) if err else ("done", None)
        if err:
            doc = s.get(Document, doc_id)
            doc.status, doc.status_detail = "failed", err
        s.commit()


def main():
    while not inspect(engine).has_table("jobs"):  # таблицы создаёт API при старте
        time.sleep(2)
    # TODO: вернуть в очередь задачи, зависшие в "running" после падения воркера
    while True:
        item = claim_job()
        run(*item) if item else time.sleep(2)


if __name__ == "__main__":
    main()
