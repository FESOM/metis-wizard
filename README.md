# `metis-wizard`: Partition your mesh into subdomains
> [Paul Gierz](mailto:paul.gierz@awi.de)
[![Docker](https://github.com/FESOM/metis-wizard/actions/workflows/docker.yml/badge.svg)](https://github.com/FESOM/metis-wizard/actions/workflows/docker.yml)

This is a simple tool to partition a mesh into subdomains. It is based on the [`metis`](https://github.com/FESOM/fesom2/tree/main/lib/metis-5.1.0)
library. The tool is in FORTRAN with a Python wrapper to call the `fesom_ini` program, which must be compiled first and be on your `$PATH`.

## Usage with Docker

```console
docker run -it --rm -v ghcr.io/fesom/metis-wizard <mesh> <nparts>
```

Or use select one or more number of partitions from common CPU counts:

```console
docker run -it --rm ghcr.io/fesom/metis-wizard --interactive <mesh>
```
