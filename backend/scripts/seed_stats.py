import asyncio
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from exception import InternalServerError
from models import EntityCreate
from scripts.seed import _entity_exists
from scripts.seed_stats_utils import (
    StatsConfig,
    StatsDataset,
    build_hub_entity,
    hub_update_payload,
    load_stats_config,
    read_stats_tsv,
    region_edge_payload,
    row_entity_id,
    skip_entity_id,
    table_from_kept_rows,
)
from scripts.seed_utils import SEED_DIR
from services import IngestionService, ReadService
from utils import http_client, logger


async def collect_kept_rows(
    read: ReadService, columns: list[str], rows: list[list]
) -> list[list]:
    """Keep TSV rows whose entity_id exists in OpenGIN.

    Empty / 'None' ids are skipped without a search. A missing region skips
    both the table row and the AS_CATEGORY edge.
    """
    kept: list[list] = []
    for row in rows:
        entity_id = row_entity_id(columns, row)
        if skip_entity_id(entity_id):
            logger.info("Skipping empty/None entity_id")
            continue
        if not await _entity_exists(read, entity_id):
            logger.info(f"Skipping missing region {entity_id}")
            continue
        kept.append(row)
    return kept


async def put_as_category_edges(
    ingestion: IngestionService,
    region_ids: list[str],
    hub_id: str,
    relation: str,
    region_locks: dict[str, asyncio.Lock] | None = None,
) -> None:
    """PUT one outgoing AS_CATEGORY edge per kept region (relationship-only)."""
    locks = region_locks if region_locks is not None else defaultdict(asyncio.Lock)
    for region_id in region_ids:
        payload = region_edge_payload(region_id, hub_id, relation)
        async with locks[region_id]:
            await ingestion.update_entity(region_id, payload)
        logger.info(f"{region_id} {relation} {hub_id}: updated")


async def upsert_hub(
    read: ReadService, ingestion: IngestionService, hub: EntityCreate
) -> str:
    """Create the hub with kind; update with id + attributes only.

    Category hubs are often missing from search, so a duplicate-id create
    falls back to the same attribute-only PUT.
    """
    if await _entity_exists(read, hub.id, hub.kind):
        await ingestion.update_entity(hub.id, hub_update_payload(hub))
        return "updated"
    try:
        await ingestion.create_entity(hub)
        return "created"
    except InternalServerError as exc:
        if "already exists" not in str(exc.detail).lower():
            raise
        await ingestion.update_entity(hub.id, hub_update_payload(hub))
        return "updated"


async def seed_dataset(
    read: ReadService,
    ingestion: IngestionService,
    config: StatsConfig,
    dataset: StatsDataset,
    seed_dir: Path = SEED_DIR,
    region_locks: dict[str, asyncio.Lock] | None = None,
) -> None:
    """Search TSV ids, upsert the hub with kept rows, then PUT region edges."""
    logger.info(f"Seeding {dataset.id} ({dataset.name})")
    columns, rows = read_stats_tsv(seed_dir / dataset.file)
    kept_rows = await collect_kept_rows(read, columns, rows)
    table = table_from_kept_rows(columns, kept_rows, dataset.date)
    hub = build_hub_entity(dataset, config.kind, table["columns"], table["rows"])
    status = await upsert_hub(read, ingestion, hub)
    logger.info(
        f"{hub.kind.minor} {hub.id} ({hub.name.value}): "
        f"{status} / {len(kept_rows)} rows"
    )
    region_ids = list(
        dict.fromkeys(row_entity_id(columns, row) for row in kept_rows)
    )
    await put_as_category_edges(
        ingestion, region_ids, dataset.id, config.relation, region_locks
    )


def _datasets_by_hub(datasets: list[StatsDataset]) -> list[list[StatsDataset]]:
    """Group yaml entries that write the same hub so years of one table stay serial."""
    grouped: dict[str, list[StatsDataset]] = {}
    for dataset in datasets:
        grouped.setdefault(dataset.id, []).append(dataset)
    return list(grouped.values())


async def seed_stats(seed_dir: Path = SEED_DIR) -> None:
    config = load_stats_config(seed_dir / "stats.yaml")
    read = ReadService()
    ingestion = IngestionService()
    region_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    hub_groups = _datasets_by_hub(config.datasets)

    await http_client.start()
    try:
        logger.info(
            f"Seeding {len(config.datasets)} dataset(s) "
            f"across {len(hub_groups)} table(s) in parallel"
        )

        async def seed_hub_group(datasets: list[StatsDataset]) -> None:
            for dataset in datasets:
                await seed_dataset(
                    read, ingestion, config, dataset, seed_dir, region_locks
                )

        await asyncio.gather(*(seed_hub_group(group) for group in hub_groups))
    finally:
        await http_client.close()


if __name__ == "__main__":
    asyncio.run(seed_stats())
