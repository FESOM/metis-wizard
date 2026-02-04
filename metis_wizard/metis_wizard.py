"""
The ``metis-wizard`` package provides an easy-to-use interface for ``metis``, the FESOM mesh partitioner.

A ``partition`` is a collection of subdomains that cover the entire domain of the mesh, which can be divided up among multiple cores. FESOM
scales to approximately 300 cores. See the notes in the ``fesom`` documentation <https://readthedocs.org/fesom/> for more information. 
"""

import importlib.resources as pkg_resources
import shutil
import subprocess

import f90nml
import questionary
import rich_click as click
from click_loguru import ClickLoguru
from loguru import logger

__version__ = "2.1.0"
__author__ = "FESOM Team"
__license__ = "MIT"
__maintainer__ = "FESOM Team"
__email__ = "paul.gierz@awi.de"

click_loguru = ClickLoguru(
    "metis-wizard",
    __version__,
    retention=2,
    timer_log_level="info",
)


class FesomMesh:
    def __init__(self, path):
        self.path = path


class MetisNamelist(f90nml.Namelist):
    """
    Namelist for the FESOM Mesh Partitioning Tools ``metis``.
    """

    def set_mesh(self, mesh_path):
        """
        Sets up the mesh file path for the ``metis`` (``fesom_ini``) namelist.

        Parameters
        ----------
        mesh_path : str
            Path to the mesh file.
        """
        self["paths"]["meshpath"] = mesh_path

    def set_partitioning(self, n_part=288):
        """
        Sets up the number of levels and partitions to use for the ``metis`` (``fesom_ini``) namelist.

        Parameters
        ----------
        n_part : int
            Number of partitions (cores) to use.
        """
        self["machine"]["n_levels"] = 1
        self["machine"]["n_part"] = n_part


class MetisPartitionerError(Exception):
    """General METIS Partitioner Error"""


class MetisPartitioner:
    """
    A class used to partition a FESOM mesh using METIS.

    Attributes
    ----------
    bin : str
        a string representing the binary file for the partitioner, can be set during initialization

    Methods
    -------
    __init__(self, bin=None):
        Initializes the MetisPartitioner. If bin is not provided, it tries to find 'fesom_ini' in the PATH.
    partition_mesh(self, mesh, n_part=288):
        Partitions the provided FESOM mesh using METIS.
    """

    _BIN = "fesom_ini"

    def __init__(self, bin: str = None) -> None:
        """
        Initializes the MetisPartitioner. If bin is not provided, it tries to find 'fesom_ini' in the PATH.

        Parameters:
        -----------
        bin (str, optional): The path to the METIS binary. Defaults to None.
        """
        self.bin = bin or self._BIN
        try:
            assert shutil.which(self.bin)
        except AssertionError:
            raise MetisPartitionerError(f"{self.bin} not found on PATH.")

    def partition_mesh(
        self, mesh: FesomMesh, n_part: int = 288, alpha=None, beta=None, gamma=None, use_cavity=False, namelist_path=None
    ) -> None:
        """
        Partitions the mesh using METIS.

        Parameters:
        -----------
        mesh (FesomMesh): The FESOM mesh object.
        n_part (int, optional): The number of partitions. Defaults to 288.
        """
        # Create the namelist:
        nml = prepare_namelist(mesh, n_part, alpha, beta, gamma, use_cavity, namelist_path)
        # Write the namelist:
        nml.write("namelist.config", force=True)
        logger.info(f"Namelist written for {self.bin}.")
        # Run the partitioner:
        logger.info(f"Partitioning mesh with {self.bin}...")
        subprocess.run(self.bin, shell=True, check=True)
        logger.success(f"Mesh partitioned with {self.bin} for {n_part}.")


def read_namelist_config():
    with pkg_resources.open_text("metis_wizard", "namelist.config") as file:
        data = file.read()
    return data


def prepare_namelist(
    mesh: FesomMesh, n_part: int = 288, alpha=None, beta=None, gamma=None, use_cavity=False, namelist_path=None
):
    """
    This function prepares the METIS namelist file for partitioning.

    Parameters:
    -----------
    n_part (int, optional): The number of partitions. Defaults to 288.
    namelist_path (str, optional): Path to custom namelist template. Defaults to bundled template.

    Returns:
    --------
    MetisNamelist object: The METIS namelist object.
    """
    if namelist_path is not None:
        nml = MetisNamelist(f90nml.read(namelist_path))
    else:
        f = read_namelist_config()
        nml = MetisNamelist(f90nml.reads(f))
    nml.set_mesh(mesh.path)
    nml.set_partitioning(n_part)
    if alpha is not None:
        nml["geometry"]["alphaeuler"] = alpha
    if beta is not None:
        nml["geometry"]["betaeuler"] = beta
    if gamma is not None:
        nml["geometry"]["gammaeuler"] = gamma
    if use_cavity:
        nml["ale_def"]["use_partial_cell"] = True
        nml["run_config"]["use_cavity"] = True
        nml["run_config"]["use_cavity_partial_cell"] = True
    return nml


@click_loguru.logging_options
@click.command()
@click_loguru.init_logger()
@click.version_option(version=__version__)
@click.argument("mesh_path", type=click.Path(exists=True))
@click.argument("n_part", nargs=-1)
@click.option("--interactive", is_flag=True, help="Interactive mode.")
@click.option(
    "--rotated", nargs=3, type=float, help="Rotated mesh. Give alpha, beta, gamma."
)
@click.option(
    "--use-cavity",
    is_flag=True,
    help="Enable cavity support. Sets use_cavity, use_cavity_partial_cell, and use_partial_cell.",
)
@click.option(
    "--fesom-ini",
    type=click.Path(exists=True),
    help="Path to fesom_ini binary. Defaults to searching PATH.",
)
@click.option(
    "--namelist",
    type=click.Path(exists=True),
    help="Path to custom namelist template. Defaults to bundled template.",
)
def main(
    verbose,
    quiet,
    logfile,
    profile_mem,
    mesh_path,
    n_part,
    interactive=False,
    rotated=None,
    use_cavity=False,
    fesom_ini=None,
    namelist=None,
):
    if rotated is not None:
        logger.info("Rotated mesh dected. Rotating mesh...")
        alpha, beta, gamma = rotated
        logger.info(f"Rotating mesh by alpha={alpha}, beta={beta}, gamma={gamma}")
    else:
        alpha, beta, gamma = None, None, None
    if use_cavity:
        logger.info("Cavity support enabled. Setting use_cavity, use_cavity_partial_cell, and use_partial_cell.")
    if not n_part and interactive:
        logger.info("Interactive mode enabled for selecting partitions:")
        logger.info("Highlighted (filled in) partitions will be generated...")
        n_part = questionary.checkbox(
            "Select the number of partitions",
            choices=[
                questionary.Choice(n, checked=True) for n in [72, 144, 288, 432, 864]
            ],
        ).ask()
        while questionary.confirm(
            "Would you like to add a custom number of partitions?", default=False
        ).ask():
            n_part += questionary.text("Enter the number of partitions").ask()
            logger.info("Selected partitions:")
            [logger.info(n) for n in n_part]
    if interactive and not questionary.confirm("Proceed with partitioning?").ask():
        logger.info("Exiting...")
        return
    n_part = n_part or [288]
    n_part = [int(n) for n in n_part]
    logger.info("Beginning Mesh Partitioning with METIS")
    logger.info(f"Mesh Path: {mesh_path}")
    logger.info(f"Number of Partition Schemes: {len(n_part)}")
    partitoner = MetisPartitioner(bin=fesom_ini)
    mesh = FesomMesh(mesh_path)
    for n in n_part:
        logger.info(f"Partition Scheme: {n}")
        partitoner.partition_mesh(mesh, n, alpha, beta, gamma, use_cavity, namelist)


if __name__ == "__main__":
    main()
