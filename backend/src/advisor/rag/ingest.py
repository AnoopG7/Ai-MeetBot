from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from ..core.config import settings
from ..core.logging import configure_logging, get_logger
from .embedding import DenseEmbedding, SparseEmbedding
from .ingestion import load_directory, process_documents
from .store import VectorStore

logger = get_logger(__name__)


def ingest_directory(
    dir_path: Path,
    pattern: str = "*.md",
    recreate: bool = False,
) -> int:
    store = VectorStore()

    if recreate:
        with contextlib.suppress(Exception):
            store.delete_collection()

    dense_emb = DenseEmbedding()
    sparse_emb = SparseEmbedding()

    docs = load_directory(dir_path, pattern=pattern)

    if not docs:
        logger.warning("no documents found", directory=str(dir_path), pattern=pattern)
        return 0

    count = process_documents(
        docs=docs,
        store=store,
        dense_emb=dense_emb,
        sparse_emb=sparse_emb,
    )

    store.close()
    return count


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser(
        description="Ingest finance knowledge documents into Qdrant",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=str,
        default=str(settings.knowledge_dir),
        help="Path to knowledge base directory",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.md",
        help="File glob pattern (default: *.md)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the collection before ingesting",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Qdrant URL (default: from env QDRANT_URL)",
    )

    args = parser.parse_args()
    dir_path = Path(args.directory)

    if not dir_path.exists():
        logger.error("directory not found", path=str(dir_path))
        sys.exit(1)

    logger.info(
        "starting ingestion",
        directory=str(dir_path),
        pattern=args.pattern,
        recreate=args.recreate,
    )

    count = ingest_directory(
        dir_path=dir_path,
        pattern=args.pattern,
        recreate=args.recreate,
    )

    logger.info("ingestion finished", total_chunks=count)
    print(f"\nIngested {count} chunks into Qdrant collection '{settings.qdrant_collection}'")


if __name__ == "__main__":
    main()
