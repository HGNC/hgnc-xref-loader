"""Tests for gene2accession parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.gene2accession_parser import (
    Gene2AccessionParser,
)
from hgnc_xref_loader.services.gene2accession_load_service import (
    Gene2AccessionLoadService,
)


def _make_g2a_tsv() -> bytes:
    header = (
        "#tax_id\tGeneID\tStatus\tRNA_nucleotide_accession.version"
        "\tRNA_nucleotide_gi\tProtein_accession.version\tProtein_gi"
        "\tGenomic_nucleotide_accession.version\tGenomic_nucleotide_gi"
        "\tStart_position_on_the_genomic_accession"
        "\tEnd_position_on_the_genomic_accession"
        "\tOrientation\tAssembly\tMature_peptide_accession.version"
        "\tMature_peptide_gi\tSymbol\n"
    )
    lines = (
        "9606\t1\tREVIEWED\tNR_024540.1\t12345678\tNP_001128622.1"
        "\t87654321\tNG_012798.1\t11223344\t5001\t115789\t+\t"
        "GRCh38.p13\t-\t-\tA1BG\n"
        "10090\t2\tREVIEWED\t-\t-\tNP_033745.1\t99887766\t-\t-\t"
        "-\t-\t-\t-\t-\t-\tA2m\n"
        "3702\t3\tPROVISIONAL\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\tAAT1\n"
    )
    return gzip.compress((header + lines).encode("utf-8"))


class TestGene2AccessionParser:
    """Test the gene2accession TSV parser."""

    def test_parse_filters_by_tax_id(self) -> None:
        parser = Gene2AccessionParser()
        records = parser.parse(_make_g2a_tsv())
        assert len(records) == 2
        tax_ids = {r.g2a_tax_id for r in records}
        assert tax_ids == {"9606", "10090"}

    def test_parse_record_fields(self) -> None:
        parser = Gene2AccessionParser()
        records = parser.parse(_make_g2a_tsv())
        human = [r for r in records if r.g2a_tax_id == "9606"][0]
        assert human.g2a_eg_id == "1"
        assert human.g2a_status == "REVIEWED"
        assert human.g2a_symbol == "A1BG"

    def test_parse_staging_dict(self) -> None:
        parser = Gene2AccessionParser()
        records = parser.parse(_make_g2a_tsv())
        d = records[0].to_staging_dict()
        assert "g2a_tax_id" in d
        assert "g2a_symbol" in d
        assert len(d) == 16


class TestGene2AccessionLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_g2a_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gene2accession_update"
        mock_staging.bulk_copy_into_staging.return_value = 2

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = Gene2AccessionLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 2
        mock_staging.promote_staging_to_production.assert_called_once()

    def test_run_skips_when_version_unchanged(self) -> None:
        mock_version = MagicMock()
        mock_version.should_skip.return_value = True

        service = Gene2AccessionLoadService(
            http_client=MagicMock(),
            staging_repo=MagicMock(),
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.skipped is True
