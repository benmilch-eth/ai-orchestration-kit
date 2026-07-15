"""ai-orchestration-kit — a substrate-based handoff bus with a safe, auditable autonomous executor."""
from .store import LocalStore
from .watcher import run_watch
from .executor import Executor
from .classifier import llm_classifier
from .audit import Audit
__all__ = ["LocalStore", "run_watch", "Executor", "llm_classifier", "Audit"]
__version__ = "0.1.0"
