"""Tests for refseq_catalog parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.refseq_catalog_parser import (
    RefseqCatalogParser,
)
from hgnc_xref_loader.services.refseq_catalog_load_service import (
    RefseqCatalogLoadService,
)


def _make_refseq_catalog_tsv() -> bytes:
    lines = (
        "9606\tHomo sapiens\tNM_001308203.2\tRS202401\tREVIEWED\t4567\n"
        "10090\tMus musculus\tNM_001110785.1\tRS202401\tPROVISIONAL\t2345\n"
        "3702\tArabidopsis thaliana\tNM_001034412.1\tRS202401\tPROVISIONAL\t1234\n"
    )
    return gzip.compress(lines.encode("utf-8"))


class TestRefseqCatalogParser:
    """Test the refseq_catalog TSV parser."""

    def test_parse_filters_by_tax_id(self) -> None:
        parser = RefseqCatalogParser()
        records = parser.parse(_make_refseq_catalog_tsv())
        assert len(records) == 2
        tax_ids = {r.rfc_tax_id for r in records}
        assert tax_ids == {"9606", "10090"}

    def test_parse_record_fields(self) -> None:
        parser = RefseqCatalogParser()
        records = parser.parse(_make_refseq_catalog_tsv())
        human = [r for r in records if r.rfc_tax_id == "9606"][0]
        assert human.rfc_species == "Homo sapiens"
        assert human.rfc_refseq_id == "NM_001308203.2"
        assert human.rfc_status == "REVIEWED"

    def test_parse_staging_dict(self) -> None:
        parser = RefseqCatalogParser()
        records = parser.parse(_make_refseq_catalog_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 6


class TestRefseqCatalogLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.side_effect = [
            b"...RefSeq-release220.catalog.gz...",
            _make_refseq_catalog_tsv(),
        ]

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "refseq_catalog_update"
        mock_staging.bulk_copy_into_staging.return_value = 2

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = RefseqCatalogLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 2
