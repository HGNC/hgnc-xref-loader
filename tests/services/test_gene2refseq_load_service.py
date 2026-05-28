"""Tests for gene2refseq parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.gene2refseq_parser import Gene2RefseqParser
from hgnc_xref_loader.services.gene2refseq_load_service import (
    Gene2RefseqLoadService,
)


def _make_g2r_tsv() -> bytes:
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
        "9606\t1\tREVIEWED\tNR_024540.1\t11111\tNP_001128622.1\t22222"
        "\tNG_012798.1\t33333\t5001\t115789\t+\tGRCh38.p13\t-\t-\tA1BG\n"
        "10116\t3\tPROVISIONAL\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\tA2m\n"
        "3702\t4\tPROVISIONAL\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\tAAT1\n"
    )
    return gzip.compress((header + lines).encode("utf-8"))


class TestGene2RefseqParser:
    """Test the gene2refseq TSV parser."""

    def test_parse_filters_by_tax_id(self) -> None:
        parser = Gene2RefseqParser()
        records = parser.parse(_make_g2r_tsv())
        assert len(records) == 2
        tax_ids = {r.g2r_tax_id for r in records}
        assert tax_ids == {"9606", "10116"}

    def test_parse_staging_dict_has_16_cols(self) -> None:
        parser = Gene2RefseqParser()
        records = parser.parse(_make_g2r_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 16


class TestGene2RefseqLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_g2r_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gene2refseq_update"
        mock_staging.bulk_copy_into_staging.return_value = 2

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = Gene2RefseqLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 2
