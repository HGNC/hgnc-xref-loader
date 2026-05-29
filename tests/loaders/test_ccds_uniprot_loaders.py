"""Tests for CCDS and UniProt loader fetch_and_parse implementations."""

from __future__ import annotations

from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.ccds_loader import CcdsXrefLoader
from hgnc_xref_loader.loaders.uniprot_loader import UniprotXrefLoader


def _ccds_bytes() -> bytes:
    header = "chr\tacc\tver\tsymbol\tncbi_gene_id\tccds_id\tstatus\tstrand\tfrom\tto\tlocations\tmatch_type\n"
    row = "chr1\tNC_000001.11\t1\tA1BG\t1\tCCDS1.1\tPublic\t+\t100\t200\t[100-200]\tIdentical\n"
    return (header + row).encode("utf-8")


def _uniprot_bytes() -> bytes:
    pre = "\n".join(["# comment"] * 19)
    header = (
        "Entry\tStatus\tEntry Name\tProtein names\t"
        "Gene Names (primary)\tCross-reference (HGNC)\t"
        "EC number\tCross-reference (GeneID)"
    )
    row = "P12345\treviewed\tABC_HUMAN\tProtein alpha (Fragment)\tABC\tHGNC:12345\tEC:1.1.1.1\t1234"
    return f"{pre}\n{header}\n{row}\n".encode("utf-8")


class TestCcdsXrefLoaderFetchAndParse:
    """Tests for CCDS fetch_and_parse behavior."""

    def test_fetch_uses_ccds_url(self) -> None:
        fetch_client = MagicMock()
        fetch_client.fetch.return_value = _ccds_bytes()

        loader = CcdsXrefLoader(fetch_client=fetch_client)
        loader.fetch_and_parse()

        fetch_client.fetch.assert_called_once_with(
            "https://ftp.ncbi.nlm.nih.gov/pub/CCDS/current_human/CCDS.current.txt"
        )

    def test_fetch_and_parse_returns_staging_dicts(self) -> None:
        fetch_client = MagicMock()
        fetch_client.fetch.return_value = _ccds_bytes()

        loader = CcdsXrefLoader(fetch_client=fetch_client)
        rows = loader.fetch_and_parse()

        assert len(rows) == 1
        assert rows[0]["ccds_id"] == "CCDS1.1"
        assert rows[0]["ccds_eg_id"] == "1"


class TestUniprotXrefLoaderFetchAndParse:
    """Tests for UniProt fetch_and_parse behavior."""

    def test_fetch_uses_uniprot_stream_url(self) -> None:
        fetch_client = MagicMock()
        fetch_client.fetch.return_value = _uniprot_bytes()

        loader = UniprotXrefLoader(fetch_client=fetch_client)
        loader.fetch_and_parse()

        fetch_client.fetch.assert_called_once()
        called_url = fetch_client.fetch.call_args.args[0]
        assert called_url.startswith("https://rest.uniprot.org/uniprotkb/stream")
        assert "organism_id:9606" in called_url

    def test_fetch_and_parse_returns_main_uniprot_rows(self) -> None:
        fetch_client = MagicMock()
        fetch_client.fetch.return_value = _uniprot_bytes()

        loader = UniprotXrefLoader(fetch_client=fetch_client)
        rows = loader.fetch_and_parse()

        assert len(rows) == 1
        assert rows[0]["unip_acc"] == "P12345"
        assert rows[0]["unip_status"] == "reviewed"
        assert rows[0]["unip_prot_name"] == "Protein alpha"
