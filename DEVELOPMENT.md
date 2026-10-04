# Development

Python 3.12 and the standard library are sufficient. Run `python
tools/check_repository.py` for parsing, privacy checks, and cache regression tests.

Run `python simulator.py -s 64 -b 16 -a 4 -r rr -p 128 -u 20 -n -1
-f examples/tiny.trace` on one line. The trace is a new tiny synthetic demonstration,
not an original workload. The program writes a Team_*_Sim_*.txt report in the
working directory; generated reports are ignored by Git. Milestone versions are
retained as historical coursework, not additional current entry points.
