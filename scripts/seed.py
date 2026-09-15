import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from exception import BadRequestError
from models import EntityCreate
from scripts.seed_utils import SeedItem, load_seed_payloads
from services import IngestionService
from utils import http_client, logger


async def _create_or_skip(ingestion: IngestionService, entity: EntityCreate) -> str:
    try:
        await ingestion.create_entity(entity)
        return "created"
    except BadRequestError as exc:
        logger.warning(f"Skipping {entity.id}: {exc.detail}")
        return "skipped"


async def _create_or_update(ingestion: IngestionService, entity: EntityCreate) -> str:
    try:
        await ingestion.create_entity(entity)
        return "created"
    except BadRequestError as exc:
        logger.warning(
            f"{entity.id} already exists, updating relationships: {exc.detail}"
        )
        await ingestion.update_entity(entity.id, entity)
        return "updated"


async def seed_item(ingestion: IngestionService, item: SeedItem) -> str:
    if item.update_on_conflict:
        return await _create_or_update(ingestion, item.entity)
    return await _create_or_skip(ingestion, item.entity)


async def seed() -> None:
    items = load_seed_payloads()
    ingestion = IngestionService()

    await http_client.start()
    try:
        for item in items:
            entity = item.entity
            status = await seed_item(ingestion, item)
            logger.info(
                f"{entity.kind.minor} {entity.id} ({entity.name.value}): {status}"
            )
    finally:
        await http_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
