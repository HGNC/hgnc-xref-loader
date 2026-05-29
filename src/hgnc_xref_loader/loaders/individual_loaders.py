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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


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
        return []


@register_source(XrefSource.CYTOBAND)
class CytobandLoader(BaseXrefLoader):
    """Load cytoband cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


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
        return []


@register_source(XrefSource.UCSC2HGNC)
class Ucsc2HgncLoader(BaseXrefLoader):
    """Load UCSC-to-HGNC cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


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
        return []
