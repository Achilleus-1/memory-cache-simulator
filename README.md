# Memory and Cache Simulator

Trace-driven Python simulator for virtual memory, set-associative caches, replacement policies, and CPI/cost analysis.

## Original coursework

- Computer Architecture

Originally completed at the University of Texas at San Antonio and imported to GitHub later. This repository retains the coursework implementation with documented maintenance fixes and demonstration assets.

**Languages and technologies:** Python, argparse, standard library.

## Implementation

- Team implementation of cache geometry and implementation-memory/cost calculations.
- Per-process page tables sharing a physical-page pool.
- Instruction/data accesses through a set-associative cache with round-robin or random replacement.
- Hit/miss, page-fault, CPI, and unused-cache-space reporting.

## Concepts

- Address decomposition, cache associativity, shared page allocation, block-spanning accesses, and simulation bookkeeping.

## Repository layout

| Directory | Contents |
|---|---|
| `simulator.py` | Final integrated simulator |
| `milestones/cache-calculations` | Earlier source milestone |
| `milestones/virtual-memory` | Earlier source milestone |

## Running the source

Requires Python 3. Run python simulator.py --help to inspect the arguments. A typical invocation is: python simulator.py -s 64 -b 16 -a 4 -r rr -p 128 -u 20 -n -1 -f YOUR_TRACE_FILE. The program redirects its report to Team_12_Sim_n_M#3.txt. Original trace inputs were not present in the archive.

## Scope and limitations

- This was a team project; the repository describes the shared implementation without claiming sole authorship.
- The original trace format and coursework assumptions are retained.

Only source code, build configuration, and required text inputs are included. Written submissions, assignment instructions, PDFs, videos, generated outputs, binary builds, and private configuration are omitted. Anonymized contributor labels and supplied-code comments retain the distinction between submitted work and scaffolding. No license for course-provided material is inferred.

## Development and reuse

See [DEVELOPMENT.md](DEVELOPMENT.md) for reproducible checks and known archival dependencies, [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance, and [SECURITY.md](SECURITY.md) for private reports.

Reuse terms and provenance are documented in [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE). The maintenance license does not grant rights to original course or team material.
