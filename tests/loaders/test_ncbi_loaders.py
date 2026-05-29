"""Tests for NCBI loader fetch_and_parse implementations.

Validates that GeneInfo, GeneHistory, Gene2Refseq, and Gene2Accession
loaders correctly construct URLs, fetch data, parse records, and return
staging dicts.
"""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.fetch.client import DefaultXrefFetchClient
from hgnc_xref_loader.loaders.individual_loaders import (
    Gene2AccessionLoader,
    Gene2RefseqLoader,
    GeneHistoryLoader,
    GeneInfoLoader,
)


def _gzip_lines(lines: list[str]) -> bytes:
    joined = "\n".join(lines).encode("utf-8")
    return gzip.compress(joined)


GENE_INFO_DATA = _gzip_lines([
    "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\tdescription\ttype_of_gene\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\tNomenclature_status\tOther_designations\tModification_date",
    "9606\t1\tA1BG\t-\tA1B|ABG|GAB\tHGNC:5|MIM:138670\t19\t19q13.4\talpha-1-B glycoprotein\tprotein-coding\tA1BG\talpha-1-B glycoprotein\tO\tHEL-S-163pA1BG\t20240101",
])

GENE_HISTORY_DATA = _gzip_lines([
    "#tax_id\tGeneID\tDiscontinued_GeneID\tDiscontinued_Symbol\tDiscontinued_Date",
    "9606\t1\t99999\tOLD_SYMBOL\t20240101",
])

GENE2REFSEQ_DATA = _gzip_lines([
    "#tax_id\tGeneID\tstatus\tRNA_nucleotide_accession.version\tRNA_nucleotide_gi\tProtein_accession.version\tProtein_gi\tGenomic_nucleotide_accession.version\tGenomic_nucleotide_gi\tstart_position_on_the_genomic_accession\tend_position_on_the_genomic_accession\torientation\tassembly\tpeptide_product_accession.version\tpeptide_product_gi\tAssembly_unit\tAssembly_name\tAssembly_version\tStatus\tGeneID\tSymbol\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\tNomenclature_status\tOther_designations\tFeature_type\tcDNA\tcoding_region\tgenomic\tpeptide\tconceptual",
    "9606\t1\t-\t-\t-\t-\t-\tNC_000019.11\t1051814\t1052445\t+\tGRCh38.p14\t-\t-\t-\tPrimary Assembly\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-",
])

GENE2ACCESSION_DATA = _gzip_lines([
    "#tax_id\tGeneID\tstatus\tRNA_nucleotide_accession.version\tRNA_nucleotide_gi\tProtein_accession.version\tProtein_gi\tGenomic_nucleotide_accession.version\tGenomic_nucleotide_gi\tstart_position_on_the_genomic_accession\tend_position_on_the_genomic_accession\torientation\tassembly\tpeptide_product_accession.version\tpeptide_product_gi\tpeptide_name\tAssembly_unit\tAssembly_name\tAssembly_version\tStatus\tGeneID\tSymbol\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\tNomenclature_status\tOther_designations\tFeature_type\tcDNA\tcoding_region\tgenomic\tpeptide\tconceptual",
    "9606\t1\t-\t-\t-\t-\t-\tNC_000019.11\t1051814\t1052445\t+\tGRCh38.p14\t-\t-\t-\t-\tPrimary Assembly\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-",
])


class TestGeneInfoLoader:
    """Tests for GeneInfo loader fetch_and_parse."""

    def test_fetch_uses_correct_url(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE_INFO_DATA
        loader = GeneInfoLoader(fetch_client=mock_client)
        loader.fetch_and_parse()

        mock_client.fetch.assert_called_once_with(
            "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz"
        )

    def test_fetch_and_parse_returns_staging_dicts(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE_INFO_DATA
        loader = GeneInfoLoader(fetch_client=mock_client)
        result = loader.fetch_and_parse()

        assert len(result) == 1
        assert result[0]["gi_tax_id"] == "9606"
        assert result[0]["gi_eg_id"] == "1"
        assert result[0]["gi_hgnc_id"] == 5

    def test_creates_default_client_when_none(self) -> None:
        with patch.object(DefaultXrefFetchClient, "fetch", return_value=GENE_INFO_DATA):
            loader = GeneInfoLoader()
            result = loader.fetch_and_parse()
            assert len(result) == 1


class TestGeneHistoryLoader:
    """Tests for GeneHistory loader fetch_and_parse."""

    def test_fetch_uses_correct_url(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE_HISTORY_DATA
        loader = GeneHistoryLoader(fetch_client=mock_client)
        loader.fetch_and_parse()

        mock_client.fetch.assert_called_once_with(
            "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_history.gz"
        )

    def test_fetch_and_parse_returns_staging_dicts(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE_HISTORY_DATA
        loader = GeneHistoryLoader(fetch_client=mock_client)
        result = loader.fetch_and_parse()

        assert len(result) >= 1

    def test_creates_default_client_when_none(self) -> None:
        with patch.object(DefaultXrefFetchClient, "fetch", return_value=GENE_HISTORY_DATA):
            loader = GeneHistoryLoader()
            result = loader.fetch_and_parse()
            assert len(result) >= 1


class TestGene2RefseqLoader:
    """Tests for Gene2Refseq loader fetch_and_parse."""

    def test_fetch_uses_correct_url(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE2REFSEQ_DATA
        loader = Gene2RefseqLoader(fetch_client=mock_client)
        loader.fetch_and_parse()

        mock_client.fetch.assert_called_once_with(
            "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2refseq/gene2refseq.gz"
        )

    def test_fetch_and_parse_returns_staging_dicts(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE2REFSEQ_DATA
        loader = Gene2RefseqLoader(fetch_client=mock_client)
        result = loader.fetch_and_parse()

        assert len(result) >= 1

    def test_creates_default_client_when_none(self) -> None:
        with patch.object(DefaultXrefFetchClient, "fetch", return_value=GENE2REFSEQ_DATA):
            loader = Gene2RefseqLoader()
            result = loader.fetch_and_parse()
            assert len(result) >= 1


class TestGene2AccessionLoader:
    """Tests for Gene2Accession loader fetch_and_parse."""

    def test_fetch_uses_correct_url(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE2ACCESSION_DATA
        loader = Gene2AccessionLoader(fetch_client=mock_client)
        loader.fetch_and_parse()

        mock_client.fetch.assert_called_once_with(
            "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2accession/gene2accession.gz"
        )

    def test_fetch_and_parse_returns_staging_dicts(self) -> None:
        mock_client = MagicMock()
        mock_client.fetch.return_value = GENE2ACCESSION_DATA
        loader = Gene2AccessionLoader(fetch_client=mock_client)
        result = loader.fetch_and_parse()

        assert len(result) >= 1

    def test_creates_default_client_when_none(self) -> None:
        with patch.object(DefaultXrefFetchClient, "fetch", return_value=GENE2ACCESSION_DATA):
            loader = Gene2AccessionLoader()
            result = loader.fetch_and_parse()
            assert len(result) >= 1
