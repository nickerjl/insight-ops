"""Dramatiq task modules.

Importing this package registers all actors with the configured broker.
The worker entrypoint is::

    dramatiq app.tasks
"""

from app.tasks import broker  # noqa: F401  (configure broker first)
from app.tasks.aggregate_errors import aggregate_error_event  # noqa: F401
from app.tasks.demo_tasks import demo_task  # noqa: F401
from app.tasks.investigate import run_investigation_task  # noqa: F401
