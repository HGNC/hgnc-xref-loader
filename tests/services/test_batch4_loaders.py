"""Tests for batch 4 special loaders: mirna_raw, alphafold, cytoband, lovd, ucsc2hgnc, imgt."""

from __future__ import annotations

from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.mirna_raw_parser import MirnaRawParser
from hgnc_xref_loader.loaders.alphafold_parser import AlphafoldParser
from hgnc_xref_loader.services.mirna_raw_load_service import MirnaRawLoadService
from hgnc_xref_loader.services.alphafold_load_service import AlphafoldLoadService
from hgnc_xref_loader.services.cytoband_load_service import CytobandLoadService
from hgnc_xref_loader.services.lovd_load_service import LovdLoadService
from hgnc_xref_loader.services.ucsc2hgnc_load_service import Ucsc2HgncLoadService
from hgnc_xref_loader.services.imgt_load_service import ImgtLoadService


def _make_mirna_gff3() -> bytes:
    return (
        b"##gff-version 3\n"
        b"chr1\tmiRBase\tgene\t100\t200\t.\t+\t.\tID=MI0000001;Alias=MI0000001;Name=hsa-mir-6859-1\n"
        b"chr1\tmiRBase\tprimary_transcript\t100\t200\t.\t+\t.\tID=MI0000001;Name=hsa-mir-6859-1\n"
        b"chr2\tmiRBase\tprimary_transcript\t300\t400\t.\t-\t.\tID=MI0000002;Name=hsa-let-7a-1\n"
    )


def _make_alphafold_csv() -> bytes:
    header_lines = ["##comment"] * 9 + ["swissprot_acc,col2,col3,alphafold_acc,version"]
    csv_data = [
        "P0DTC2,N/A,N/A,AF-P0DTC2-F1,2",
        "A0A0K8P6T7,N/A,N/A,AF-A0A0K8P6T7-F1,2",
    ]
    return "\n".join(header_lines + csv_data).encode("utf-8")


def _make_lovd_data() -> bytes:
    return b"LOVD_DB1\thttps://example.com/lovd1\tBRCA1,BRCA2\nLOVD_DB2\thttps://example.com/lovd2\tTP53\n"


def _make_imgt_data() -> bytes:
    return (
        b"Homo sapiens\tTRAV1-1\tF\tTRAV1-1\t01\t14\tX\tA1BG\t5\t1\tOTTHUMG0001\tGC01P001\tP04114\textra\n"
    )


class TestMirnaRawParser:
    def test_parse_filters_primary_transcript(self) -> None:
        records = MirnaRawParser().parse(_make_mirna_gff3())
        assert len(records) == 2
        assert all(r.mirn_feature == "primary_transcript" for r in records)

    def test_parse_staging_dict(self) -> None:
        records = MirnaRawParser().parse(_make_mirna_gff3())
        d = records[0].to_staging_dict()
        assert len(d) == 9
        assert d["mirn_score"] == ""  # '.' becomes empty


class TestMirnaRawLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_mirna_gff3()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "mirna_raw_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = MirnaRawLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True
        assert result.rows_loaded == 2


class TestAlphafoldParser:
    def test_parse_skips_header(self) -> None:
        records = AlphafoldParser().parse(_make_alphafold_csv())
        assert len(records) == 2

    def test_parse_record_fields(self) -> None:
        records = AlphafoldParser().parse(_make_alphafold_csv())
        assert records[0].swissprot_acc == "P0DTC2"
        assert records[0].alphafold_acc == "AF-P0DTC2-F1"
        assert records[0].version == 2


class TestAlphafoldLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_alphafold_csv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "alphafold_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = AlphafoldLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestCytobandLoadService:
    def test_run_success(self) -> None:
        mock_repo = MagicMock()
        mock_repo.fetch_cytobands.return_value = [
            {"cb_source": "ucsc", "cb_chr": "chr1", "cb_start": "0",
             "cb_end": "10000", "cb_band": "p36.33", "cb_stain": "gneg"},
        ]
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "cytoband_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = CytobandLoadService(mock_repo, mock_staging, mock_version).run()
        assert result.success is True


class TestLovdLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_lovd_data()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "lovd_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = LovdLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestUcsc2HgncLoadService:
    def test_run_success(self) -> None:
        mock_repo = MagicMock()
        mock_repo.fetch_mappings.return_value = [
            {"ucsc_app_sym": "A1BG", "ucsc_hgnc_id": "5", "ucsc_id": "uc001"},
            {"ucsc_app_sym": "A1BG", "ucsc_hgnc_id": "5", "ucsc_id": "uc002"},
        ]
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ucsc2hgnc_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = Ucsc2HgncLoadService(mock_repo, mock_staging, mock_version).run()
        assert result.success is True

    def test_deduplicate_marks_first_as_m(self) -> None:
        records = [
            {"ucsc_app_sym": "A1BG", "ucsc_hgnc_id": "5", "ucsc_id": "uc001"},
            {"ucsc_app_sym": "A1BG", "ucsc_hgnc_id": "5", "ucsc_id": "uc002"},
        ]
        result = Ucsc2HgncLoadService._deduplicate(records)
        assert result[0]["ucsc_mapby"] == "M"
        assert result[1]["ucsc_mapby"] == "-"


class TestImgtLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_imgt_data()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "imgt_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = ImgtLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True

    def test_parse_imgt_record(self) -> None:
        records = ImgtLoadService._parse_imgt(_make_imgt_data())
        assert len(records) == 1
        assert records[0]["im_species"] == "Homo sapiens"
        assert records[0]["im_hgnc_id"] == "5"
