import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("instarecon")


def log_sub_step(agent_id: str, step: str, duration: float, status: str = "ok"):
    logger.info(f"[{agent_id}] step={step} duration={duration:.2f}s status={status}")

