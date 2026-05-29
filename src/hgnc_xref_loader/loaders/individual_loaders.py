"""Individual xref source adapters replacing scaffold stubs.

Each adapter is a thin ``BaseXrefLoader`` subclass registered with the
loader registry. Loaders fetch data from external URLs via
``XrefFetchClient``, parse it with the corresponding parser, and return
staging dicts ready for persistence.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import DefaultXrefFetchClient, XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source, XrefSource
from hgnc_xref_loader.repositories.xref_staging_repository import (
    XrefStagingRepository,
)


def _ensure_client(client: XrefFetchClient | None) -> XrefFetchClient:
    """Return the provided client or create a default one.

    Args:
        client: An optional fetch client.

    Returns:
        A usable XrefFetchClient instance.
    """
    return client or DefaultXrefFetchClient()


def _to_text(value: object) -> str | None:
    """Convert a raw field value to a non-empty string.

    Args:
        value: Raw field value from a parsed row.

    Returns:
        Stripped non-empty string, or None if blank/placeholder.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-" or text == "0":
        return None
    return text


def _first_present(row: dict[str, object], keys: tuple[str, ...]) -> str | None:
    """Return the first present non-empty value from preferred keys.

    Args:
        row: Parsed row dictionary.
        keys: Preferred key names in lookup order.

    Returns:
        First non-empty value, or None.
    """
    for key in keys:
        value = _to_text(row.get(key))
        if value is not None:
            return value
    return None


def _normalize_rows(
    raw: list[dict],
    source: str,
    hgnc_keys: tuple[str, ...],
    external_keys: tuple[str, ...],
    symbol_keys: tuple[str, ...] = (),
    status_keys: tuple[str, ...] = (),
) -> list[XrefRecord]:
    """Normalize parsed dict rows into ``XrefRecord`` instances.

    Args:
        raw: Parsed source rows.
        source: Source label for ``XrefRecord.source``.
        hgnc_keys: Candidate keys for hgnc_id.
        external_keys: Candidate keys for external_id.
        symbol_keys: Optional candidate keys for symbol.
        status_keys: Optional candidate keys for status.

    Returns:
        Normalized xref records.
    """
    records: list[XrefRecord] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        typed_row = row

        hgnc_id = _first_present(typed_row, hgnc_keys)
        external_id = _first_present(typed_row, external_keys)
        symbol = _first_present(typed_row, symbol_keys)
        status = _first_present(typed_row, status_keys)

        if hgnc_id is None and external_id is None:
            continue
        if hgnc_id is None:
            hgnc_id = external_id
        if external_id is None:
            external_id = hgnc_id

        if hgnc_id is None or external_id is None:
            continue

        try:
            records.append(
                XrefRecord(
                    hgnc_id=hgnc_id,
                    external_id=external_id,
                    source=source,
                    symbol=symbol,
                    status=status,
                )
            )
        except Exception:
            continue
    return records


@register_source(XrefSource.GENE_INFO)
class GeneInfoLoader(BaseXrefLoader):
    """Load NCBI gene_info cross-reference data.

    Fetches ``gene_info.gz`` from NCBI FTP and parses it using
    ``GeneInfoParser``.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.gene_info_parser import GeneInfoParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = GeneInfoParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="gene_info",
            hgnc_keys=("gi_hgnc_id", "gi_eg_id"),
            external_keys=("gi_eg_id",),
            symbol_keys=("gi_sym",),
            status_keys=("gi_nome_status",),
        )


@register_source(XrefSource.GENE_HISTORY)
class GeneHistoryLoader(BaseXrefLoader):
    """Load NCBI gene_history cross-reference data.

    Fetches ``gene_history.gz`` from NCBI FTP and parses it using
    ``GeneHistoryParser``.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_history.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.gene_history_parser import GeneHistoryParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = GeneHistoryParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="gene_history",
            hgnc_keys=("gh_eg_id", "gh_discontinued_eg_id"),
            external_keys=("gh_discontinued_eg_id", "gh_discontinued_sym"),
            symbol_keys=("gh_discontinued_sym",),
            status_keys=("gh_discontinued_date",),
        )


@register_source(XrefSource.GENE2ACCESSION)
class Gene2AccessionLoader(BaseXrefLoader):
    """Load NCBI gene2accession cross-reference data.

    Fetches ``gene2accession.gz`` from NCBI FTP and parses it using
    ``Gene2AccessionParser``.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2accession/gene2accession.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.gene2accession_parser import Gene2AccessionParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = Gene2AccessionParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="gene2accession",
            hgnc_keys=("g2a_eg_id",),
            external_keys=("g2a_rna_nt_acc_ver", "g2a_gen_nt_acc_ver", "g2a_prot_acc_ver"),
            symbol_keys=("g2a_symbol",),
            status_keys=("g2a_status",),
        )


@register_source(XrefSource.GENE2REFSEQ)
class Gene2RefseqLoader(BaseXrefLoader):
    """Load NCBI gene2refseq cross-reference data.

    Fetches ``gene2refseq.gz`` from NCBI FTP and parses it using
    ``Gene2RefseqParser``.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2refseq/gene2refseq.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.gene2refseq_parser import Gene2RefseqParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = Gene2RefseqParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="gene2refseq",
            hgnc_keys=("g2r_eg_id",),
            external_keys=("g2r_rna_nt_acc_ver", "g2r_gen_nt_acc_ver", "g2r_prot_acc_ver"),
            symbol_keys=("g2r_symbol",),
            status_keys=("g2r_status",),
        )


@register_source(XrefSource.REFSEQ_CATALOG)
class RefseqCatalogLoader(BaseXrefLoader):
    """Load NCBI RefSeq catalog cross-reference data.

    Fetches the latest RefSeq release catalog from NCBI via HTTPS.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _BASE_URL = "https://ftp.ncbi.nlm.nih.gov/refseq/release/release-catalog/"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.refseq_catalog_parser import RefseqCatalogParser

        client = _ensure_client(self._fetch_client)
        url = self._resolve_catalog_url(client)
        data = client.fetch(url)
        records = RefseqCatalogParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def _resolve_catalog_url(self, client: XrefFetchClient) -> str:
        listing = client.fetch(self._BASE_URL)
        import re

        matches = re.findall(r"(RefSeq-release\d+\.catalog\.gz)", listing.decode("utf-8", errors="replace"))
        if not matches:
            return self._BASE_URL + "RefSeq-release1.catalog.gz"
        return self._BASE_URL + sorted(matches)[-1]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="refseq_catalog",
            hgnc_keys=("rfc_refseq_id",),
            external_keys=("rfc_release", "rfc_refseq_id"),
            symbol_keys=("rfc_species",),
            status_keys=("rfc_status",),
        )


@register_source(XrefSource.RNA_CENTRAL)
class RnaCentralLoader(BaseXrefLoader):
    """Load RNAcentral cross-reference data.

    Fetches ``id_mapping.tsv.gz`` from EBI FTP.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/id_mapping.tsv.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.rna_central_parser import RnaCentralParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = RnaCentralParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="rna_central",
            hgnc_keys=("hgnc_id", "id", "rna_central_acc"),
            external_keys=("rna_central_acc", "id"),
            symbol_keys=("symbol",),
            status_keys=("biotype",),
        )


@register_source(XrefSource.NCBI2NAMELIST)
class Ncbi2NamelistLoader(BaseXrefLoader):
    """Load NCBI to_name cross-reference data.

    Reads the to_name file from NCBI. Requires credentials for the
    private FTP server; in production these come from environment
    variables.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.ncbi2namelist_parser import Ncbi2NamelistParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = Ncbi2NamelistParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ncbi2namelist",
            hgnc_keys=("ntn_eg_id",),
            external_keys=("ntn_sym", "ntn_eg_id"),
            symbol_keys=("ntn_sym",),
        )


@register_source(XrefSource.CCDS_SEQ)
class CcdsSeqLoader(BaseXrefLoader):
    """Load CCDS sequence cross-reference data.

    Fetches CCDS FASTA sequence data from NCBI FTP.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/pub/CCDS/current_human/CCDS.current.txt"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.ccds_seq_parser import CcdsSeqParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = CcdsSeqParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ccds_seq",
            hgnc_keys=("ccdseq_ccds_id",),
            external_keys=("ccdseq_build", "ccdseq_seq"),
        )


@register_source(XrefSource.GENCC)
class GenCCLoader(BaseXrefLoader):
    """Load GenCC cross-reference data.

    Fetches submissions CSV from thegencc.org.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://search.thegencc.org/download/action/submissions-export-csv"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.gencc_parser import GenCCParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = GenCCParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="gencc",
            hgnc_keys=("hgnc_id", "uuid"),
            external_keys=("disease_id", "omim_id", "uuid"),
            symbol_keys=("symbol",),
        )


@register_source(XrefSource.IUPHAR)
class IupharLoader(BaseXrefLoader):
    """Load IUPHAR/GtoP cross-reference data.

    Fetches HGNC mapping CSV from Guide to Pharmacology.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://www.guidetopharmacology.org/DATA/GtP_to_HGNC_mapping.csv"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.iuphar_parser import IupharParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = IupharParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="iuphar",
            hgnc_keys=("iu_hgnc_id", "iu_id"),
            external_keys=("iu_id", "iu_receptor_id"),
            symbol_keys=("iu_app_sym",),
            status_keys=("iu_receptor_name",),
        )


@register_source(XrefSource.MANE)
class ManeLoader(BaseXrefLoader):
    """Load NCBI MANE cross-reference data.

    Fetches MANE summary from NCBI FTP.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/current/MANE.GRCh38.summary.txt.gz"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.mane_parser import ManeParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = ManeParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="mane",
            hgnc_keys=("hgnc_id", "ncbi_gene_id"),
            external_keys=("ensembl_gene", "refseq_nuc_acc", "id"),
            symbol_keys=("symbol",),
            status_keys=("mane_status",),
        )


@register_source(XrefSource.OMIM2GENE)
class Omim2GeneLoader(BaseXrefLoader):
    """Load OMIM mim2gene cross-reference data.

    Fetches mim2gene.txt from OMIM.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://www.omim.org/static/omim/data/mim2gene.txt"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.omim2gene_parser import Omim2GeneParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = Omim2GeneParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="omim2gene",
            hgnc_keys=("m2g_eg_id", "m2g_mim_number"),
            external_keys=("m2g_mim_number", "m2g_ensg"),
            symbol_keys=("m2g_app_sym",),
            status_keys=("m2g_type",),
        )


@register_source(XrefSource.RGD_ORTHOLOGS)
class RgdOrthologsLoader(BaseXrefLoader):
    """Load RGD orthologs cross-reference data.

    Fetches RGD orthologs file from RGD.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://download.rgd.mcw.edu/pub/data_release/orthologs/RGD_ORTHOLOGS.txt"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.rgd_orthologs_parser import RgdOrthologsParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = RgdOrthologsParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="rgd_orthologs",
            hgnc_keys=("rgdo_human_ortholog_hgnc_id", "rgdo_human_ortholog_entrez"),
            external_keys=("rgdo_rat_gene_rgd_id", "rgdo_rat_gene_entrez_gene_id"),
            symbol_keys=("rgdo_human_ortholog_symbol",),
            status_keys=("rgdo_human_ortholog_source",),
        )


@register_source(XrefSource.AGR)
class AgrLoader(BaseXrefLoader):
    """Load Alliance genome cross-reference data.

    Fetches gene descriptions TSV from Alliance Genome.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "http://reports.alliancegenome.org/gene-descriptions/HUMAN_gene_desc_latest.tsv"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.agr_parser import AgrParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = AgrParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="agr",
            hgnc_keys=("hgnc_id",),
            external_keys=("hgnc_id", "description"),
            symbol_keys=("symbol",),
        )


@register_source(XrefSource.MGI)
class MgiLoader(BaseXrefLoader):
    """Load MGI homology cross-reference data.

    Fetches HGNC Alliance homology report from MGI.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "http://www.informatics.jax.org/downloads/reports/HGNC_AllianceHomology.rpt"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.mgi_parser import MgiParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = MgiParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="mgi",
            hgnc_keys=("ncbi_gene_id", "mgi_id", "ensembl_id"),
            external_keys=("mgi_id", "ensembl_id"),
            symbol_keys=("symbol",),
            status_keys=("type",),
        )


@register_source(XrefSource.ENSEMBL2HGNC_COMPLETE)
class Ensembl2HgncCompleteLoader(BaseXrefLoader):
    """Load complete Ensembl-to-HGNC cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        import contextlib

        from ensembl_orm.session import get_session

        from hgnc_xref_loader.repositories.ensembl2hgnc_complete_repository import (
            Ensembl2HgncCompleteRepository,
        )

        def session_factory() -> contextlib.AbstractContextManager:
            return contextlib.nullcontext(get_session())

        repository = Ensembl2HgncCompleteRepository(
            ensembl_session_factory=session_factory
        )
        return repository.fetch_all_mappings()

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ensembl2hgnc_complete",
            hgnc_keys=("e2ha_hgnc_id",),
            external_keys=("e2ha_ensembl_gene_id",),
            symbol_keys=("e2ha_app_sym",),
            status_keys=("e2ha_mapped",),
        )


@register_source(XrefSource.ENSEMBL_GENE)
class EnsemblGeneLoader(BaseXrefLoader):
    """Load Ensembl gene cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        import contextlib

        from ensembl_orm.session import get_session

        from hgnc_xref_loader.repositories.ensembl_gene_repository import (
            EnsemblGeneRepository,
        )

        def session_factory() -> contextlib.AbstractContextManager:
            return contextlib.nullcontext(get_session())

        repository = EnsemblGeneRepository(ensembl_session_factory=session_factory)
        return repository.fetch_genes()

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ensembl_gene",
            hgnc_keys=("hgnc_id", "gene_id"),
            external_keys=("gene_id",),
            symbol_keys=("name",),
            status_keys=("name_source",),
        )


@register_source(XrefSource.ENSEMBL_SEQ)
class EnsemblSeqLoader(BaseXrefLoader):
    """Load Ensembl sequence cross-reference data."""

    _CDNA_URL = (
        "https://ftp.ensembl.org/pub/current_fasta/homo_sapiens/cdna/"
        "Homo_sapiens.GRCh38.cdna.all.fa.gz"
    )
    _NCRNA_URL = (
        "https://ftp.ensembl.org/pub/current_fasta/homo_sapiens/ncrna/"
        "Homo_sapiens.GRCh38.ncrna.fa.gz"
    )

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.ensembl_seq_parser import EnsemblSeqParser

        client = _ensure_client(self._fetch_client)
        parser = EnsemblSeqParser()

        cdna_data = client.fetch(self._CDNA_URL)
        ncrna_data = client.fetch(self._NCRNA_URL)

        cdna_records = parser.parse_cdna(cdna_data)
        ncrna_records = parser.parse_ncrna(ncrna_data)
        return [record.to_staging_dict() for record in (cdna_records + ncrna_records)]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ensembl_seq",
            hgnc_keys=("eseq_ensembl_gene_id", "eseq_ensembl_transcript_id"),
            external_keys=("eseq_ensembl_transcript_id", "eseq_ensembl_gene_id"),
            status_keys=("eseq_source",),
        )


@register_source(XrefSource.MIRNA_RAW)
class MirnaRawLoader(BaseXrefLoader):
    """Load miRBase miRNA cross-reference data.

    Fetches human miRNA GFF3 from miRBase.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "https://www.mirbase.org/download/hsa.gff3"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.mirna_raw_parser import MirnaRawParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = MirnaRawParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="mirna_raw",
            hgnc_keys=("mirn_attributes", "mirn_seqname"),
            external_keys=("mirn_seqname", "mirn_attributes"),
            status_keys=("mirn_feature",),
        )


@register_source(XrefSource.ALPHAFOLD)
class AlphafoldLoader(BaseXrefLoader):
    """Load Alphafold cross-reference data.

    Fetches accession ID mapping from EBI FTP.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
    """

    _URL = "http://ftp.ebi.ac.uk/pub/databases/alphafold/accession_ids.csv"

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.alphafold_parser import AlphafoldParser

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        records = AlphafoldParser().parse(data)
        return [r.to_staging_dict() for r in records]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="alphafold",
            hgnc_keys=("swissprot_acc",),
            external_keys=("alphafold_acc", "swissprot_acc"),
            status_keys=("version",),
        )


@register_source(XrefSource.CYTOBAND)
class CytobandLoader(BaseXrefLoader):
    """Load cytoband cross-reference data."""

    _URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/cytoBand.txt.gz"

    def fetch_and_parse(self) -> list[dict]:
        import gzip

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)

        try:
            text = gzip.decompress(data).decode("utf-8")
        except Exception:
            text = data.decode("utf-8")

        rows: list[dict[str, str | int]] = []
        for line in text.splitlines():
            cols = line.split("\t")
            if len(cols) < 5:
                continue
            chromosome = cols[0].replace("chr", "").strip()
            rows.append(
                {
                    "cb_source": "UCSC",
                    "cb_chr": chromosome,
                    "cb_start": int(cols[1]),
                    "cb_end": int(cols[2]),
                    "cb_band": cols[3].strip(),
                    "cb_stain": cols[4].strip(),
                }
            )
        return rows

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="cytoband",
            hgnc_keys=("cb_chr",),
            external_keys=("cb_band",),
            status_keys=("cb_source",),
        )


@register_source(XrefSource.LOVD)
class LovdLoader(BaseXrefLoader):
    """Load LOVD cross-reference data."""

    _URL = "http://www.lovd.nl/2.0/index_list.php?export=txt"

    def fetch_and_parse(self) -> list[dict]:
        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        text = data.decode("utf-8")

        records: list[dict[str, str]] = []
        lines = text.splitlines()
        if lines:
            lines = lines[1:]

        for line in lines:
            cols = line.replace('"', "").split("\t")
            if len(cols) < 9:
                continue
            db_name = cols[6].strip()
            db_url = cols[7].strip()
            genes = cols[8].strip()
            if not genes:
                continue
            for symbol in [s.strip() for s in genes.split(",") if s.strip()]:
                name = (
                    f"{db_name} ({symbol})"
                    if symbol in {"NF1_germline", "NF1_somatic"}
                    else db_name
                )
                records.append(
                    {
                        "lovd_db_name": name,
                        "lovd_db_url": db_url,
                        "lovd_db_genes": symbol,
                    }
                )
        return records

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="lovd",
            hgnc_keys=("lovd_db_genes",),
            external_keys=("lovd_db_url", "lovd_db_name"),
            symbol_keys=("lovd_db_genes",),
        )


@register_source(XrefSource.UCSC2HGNC)
class Ucsc2HgncLoader(BaseXrefLoader):
    """Load UCSC-to-HGNC cross-reference data."""

    _URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/hgncXref.txt.gz"

    def fetch_and_parse(self) -> list[dict]:
        import gzip

        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)

        try:
            text = gzip.decompress(data).decode("utf-8")
        except Exception:
            text = data.decode("utf-8")

        rows: list[dict[str, str]] = []
        for line in text.splitlines():
            cols = [c.strip() for c in line.split("\t")]
            if len(cols) < 2:
                continue

            symbol = cols[0]
            hgnc_id = cols[1]
            transcript = cols[2] if len(cols) > 2 else ""

            if not symbol or not hgnc_id:
                continue

            rows.append(
                {
                    "ucsc_hgnc_app_sym": symbol,
                    "ucsc_hgnc_id": hgnc_id,
                    "ucsc_hgnc_ucsc_id": transcript,
                    "ucsc_mapby": "-",
                }
            )
        return rows

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="ucsc2hgnc",
            hgnc_keys=("ucsc_hgnc_id",),
            external_keys=("ucsc_hgnc_ucsc_id", "ucsc_hgnc_app_sym"),
            symbol_keys=("ucsc_hgnc_app_sym",),
            status_keys=("ucsc_mapby",),
        )


@register_source(XrefSource.IMGT)
class ImgtLoader(BaseXrefLoader):
    """Load IMGT/GENE-DB cross-reference data."""

    _URL = "https://www.imgt.org/genedb/GENElect?query=4.5+&species=Homo+sapiens"
    _COLUMNS = [
        "im_species",
        "im_gene_id",
        "im_gene_function",
        "im_gene_name",
        "im_alleles",
        "im_chrom",
        "im_ref_acc",
        "im_hgnc_app_sym",
        "im_hgnc_id",
        "im_eg_id",
        "im_vega",
        "im_geneatlas",
        "im_genecards",
        "im_uniprot",
    ]

    def fetch_and_parse(self) -> list[dict]:
        client = _ensure_client(self._fetch_client)
        data = client.fetch(self._URL)
        text = data.decode("utf-8")

        in_pre = "<pre>" in text and "</pre>" in text
        if in_pre:
            text = text.split("<pre>", 1)[1].split("</pre>", 1)[0]

        rows = [line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]
        if rows:
            rows = rows[1:]

        records: list[dict[str, str]] = []
        for row in rows:
            cols = row.split(";")
            if len(cols) < len(self._COLUMNS):
                continue
            record: dict[str, str] = {}
            for index, column_name in enumerate(self._COLUMNS):
                value = cols[index].strip()
                record[column_name] = "" if value == "-" else value
            records.append(record)
        return records

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return _normalize_rows(
            raw,
            source="imgt",
            hgnc_keys=("im_hgnc_id", "im_eg_id", "im_gene_id"),
            external_keys=("im_gene_id", "im_uniprot"),
            symbol_keys=("im_hgnc_app_sym", "im_gene_name"),
            status_keys=("im_gene_function",),
        )
