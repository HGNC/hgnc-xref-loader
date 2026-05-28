"""Tests for the CCDS load service.

Validates the orchestration of FTP fetch, TSV parsing, staging load,
and promotion for the CCDS xref loader.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.fetch.ftp_client import FtpFetchError
from hgnc_xref_loader.loaders.ccds_parser import CcdsRecord
from hgnc_xref_loader.repositories.xref_staging_repository import (
    RowCountMismatchError,
)


SAMPLE_TSV = b"#chromosome\taccession\tversion\tsymbol\tncbi_gene_id\tccds_id\tstatus\tstrand\tfrom\tto\tlocations\tmatch_type\nchr1\tNC_000001.11\t1\tA1BG\t1\tCCDS1.1\tPublic\t-\t11873\t11873\t;\tNA\n"


class TestCcdsLoadServiceImports:
    """Verify the service can be imported."""

    def test_import_ccds_load_service(self) -> None:
        from hgnc_xref_loader.services.ccds_load_service import CcdsLoadService

        assert CcdsLoadService is not None


class TestCcdsLoadServiceRun:
    """Verify the full load lifecycle."""

    def _make_service(
        self,
        ftp_data: bytes = SAMPLE_TSV,
        staging_repo: MagicMock | None = None,
    ) -> "CcdsLoadService":
        from hgnc_xref_loader.services.ccds_load_service import CcdsLoadService

        mock_ftp = MagicMock()
        mock_ftp.fetch.return_value = ftp_data

        repo = staging_repo or MagicMock()
        repo.prepare_staging_table.return_value = "ccds_update"
        repo.bulk_copy_into_staging.return_value = 1
        return CcdsLoadService(
            ftp_client=mock_ftp,
            staging_repo=repo,
        )

    def test_run_calls_ftp_fetch(self) -> None:
        svc = self._make_service()
        svc.run()
        svc._ftp_client.fetch.assert_called_once()

    def test_run_prepares_staging_table(self) -> None:
        svc = self._make_service()
        svc.run()
        svc._staging_repo.prepare_staging_table.assert_called_once_with("ccds")

    def test_run_bulk_copies_parsed_records(self) -> None:
        svc = self._make_service()
        svc.run()
        call_args = svc._staging_repo.bulk_copy_into_staging.call_args
        staging_table = call_args[0][0]
        records = call_args[0][1]
        assert staging_table == "ccds_update"
        assert len(records) == 1
        assert records[0]["ccds_id"] == "CCDS1.1"

    def test_run_validates_row_count(self) -> None:
        svc = self._make_service()
        svc.run()
        svc._staging_repo.validate_staging_row_count.assert_called_once_with(
            "ccds_update", 1
        )

    def test_run_promotes_staging(self) -> None:
        svc = self._make_service()
        svc.run()
        svc._staging_repo.promote_staging_to_production.assert_called_once_with(
            "ccds_update", "ccds"
        )

    def test_run_returns_record_count(self) -> None:
        svc = self._make_service()
        count = svc.run()
        assert count == 1

    def test_run_returns_zero_for_empty_data(self) -> None:
        empty_tsv = b"#header\n"
        svc = self._make_service(ftp_data=empty_tsv)
        count = svc.run()
        assert count == 0

    def test_run_does_not_promote_on_empty_data(self) -> None:
        empty_tsv = b"#header\n"
        svc = self._make_service(ftp_data=empty_tsv)
        svc.run()
        svc._staging_repo.promote_staging_to_production.assert_not_called()

    def test_run_raises_on_ftp_failure(self) -> None:
        svc = self._make_service()
        svc._ftp_client.fetch.side_effect = FtpFetchError("host", "failed")
        with pytest.raises(FtpFetchError):
            svc.run()

    def test_run_raises_on_row_count_mismatch(self) -> None:
        svc = self._make_service()
        svc._staging_repo.validate_staging_row_count.side_effect = RowCountMismatchError(
            "ccds_update", expected=1, actual=0
        )
        with pytest.raises(RowCountMismatchError):
            svc.run()

    def test_run_does_not_promote_on_validation_failure(self) -> None:
        svc = self._make_service()
        svc._staging_repo.validate_staging_row_count.side_effect = RowCountMismatchError(
            "ccds_update", expected=1, actual=0
        )
        with pytest.raises(RowCountMismatchError):
            svc.run()
        svc._staging_repo.promote_staging_to_production.assert_not_called()

    def test_run_parses_multiple_rows(self) -> None:
        multi_tsv = (
            b"#chromosome\taccession\tversion\tsymbol\tncbi_gene_id\tccds_id\tstatus\tstrand\tfrom\tto\tlocations\tmatch_type\n"
            b"chr1\tNC_000001.11\t1\tA1BG\t1\tCCDS1.1\tPublic\t-\t11873\t11873\t;\tNA\n"
            b"chr1\tNC_000001.11\t1\tA1CF\t29974\tCCDS2.2\tPublic\t+\t11873\t12000\t;\tNA\n"
        )
        svc = self._make_service(ftp_data=multi_tsv)
        svc._staging_repo.bulk_copy_into_staging.return_value = 2
        count = svc.run()
        assert count == 2
