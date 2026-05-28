"""Tests for ccds_seq parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.ccds_seq_parser import CcdsSeqParser
from hgnc_xref_loader.services.ccds_seq_load_service import CcdsSeqLoadService


def _make_fasta() -> bytes:
    fasta = (
        ">CCDS1|GRCh38|chr1\n"
        "ATCGATCG\n"
        "GCTAGCTA\n"
        ">CCDS2|GRCh38|chr2\n"
        "TTTTTTTT\n"
    )
    return gzip.compress(fasta.encode("utf-8"))


class TestCcdsSeqParser:
    """Test the ccds_seq FASTA parser."""

    def test_parse_basic(self) -> None:
        parser = CcdsSeqParser()
        records = parser.parse(_make_fasta())
        assert len(records) == 2

    def test_parse_record_fields(self) -> None:
        parser = CcdsSeqParser()
        records = parser.parse(_make_fasta())
        assert records[0].ccdseq_ccds_id == "CCDS1"
        assert records[0].ccdseq_build == "GRCh38"
        assert records[0].ccdseq_chrom == "chr1"
        assert records[0].ccdseq_seq == "ATCGATCGGCTAGCTA"

    def test_parse_second_record(self) -> None:
        parser = CcdsSeqParser()
        records = parser.parse(_make_fasta())
        assert records[1].ccdseq_ccds_id == "CCDS2"
        assert records[1].ccdseq_seq == "TTTTTTTT"

    def test_parse_staging_dict(self) -> None:
        parser = CcdsSeqParser()
        records = parser.parse(_make_fasta())
        d = records[0].to_staging_dict()
        assert d["ccdseq_ccds_id"] == "CCDS1"
        assert len(d) == 4


class TestCcdsSeqLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_ftp = MagicMock()
        mock_ftp.fetch.return_value = _make_fasta()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ccds_seq_update"
        mock_staging.bulk_copy_into_staging.return_value = 2

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = CcdsSeqLoadService(
            ftp_client=mock_ftp,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 2
