# 4-Axis Orthogonal Intersection Architecture ($D_1 \cap D_2 \cap D_3 \cap D_4$) for Prime Coordinate Navigation

A deterministic, memory-bounded geometric framework for navigating prime number coordinates at arbitrary-precision scales (validated up to $10^{41,024,320}$, the scale of the largest known Mersenne prime $M_{136279841} = 2^{136279841}-1$) without relying on analytic Zeta evaluations or heavy cross-lattice heaps.

## Core Architecture

1. **4-Axis Orthogonal Projection ($D_1, D_2, D_3, D_4$):**
   Decomposes the local integer boundary into four independent orthogonal harmonic axes:
   - $D_1$: Forward Real Axis ($X_1$)
   - $D_2$: Forward Imaginary Axis ($Y_1$)
   - $D_3$: Compensating Real Axis ($X_2$)
   - $D_4$: Compensating Imaginary Axis ($Y_2$)

2. **64-Bit Micro-Offset Space Convergence:**
   Instead of replicating multi-megabyte BigInt objects in RAM, each axis projects modular resonance masks onto a compact 64-bit relative offset domain. Multi-dimensional set intersection ($S(D_1) \cap S(D_2) \cap S(D_3) \cap S(D_4)$) eliminates ~90% of composite coordinates in milliseconds with minimal memory footprint.

3. **Shared Base-Phase Batching:**
   Computes modular phases once per 64-bit product block at the window boundary and distributes them across all four orthogonal dimensions, cutting arbitrary-precision division overhead by 75%.

4. **Incremental Anchor Stepping & Checkpointing:**
   Supports sequential forward scanning from arbitrary anchor values (`anchor -> next candidate`), persistent JSON state recovery (`prime_search_checkpoint.json`), and full-precision candidate logging (`found_primes_results.txt`).

## Benchmark Highlights (Scale: $2^{136279841}-1$, ~41.02 Million Digits)

- **Boundary Window:** `100,000` units (`50,000` odd positions)
- **Independent Axis Survival:** $|D_1| = 22,691$, $|D_2| = 28,013$, $|D_3| = 30,515$, $|D_4| = 32,967$
- **4D Intersection Convergence:** Reduced to `5,152` candidate offsets
- **Memory Footprint:** `< 50 MB` RAM (zero BigInt list duplication)
- **First Converged Offset:** `+22` units from anchor

> **Note on Verification:** At scales exceeding $10^{100,000}$ bits, output coordinates represent **4D orthogonal lattice candidates** filtered against base harmonic frequencies. Full deterministic or probable-prime certification (e.g., PRP / Gerbicz proof via PRST or Prime95) should be run separately for formal prime record submission.

## Quick Start

```bash
python prime_4d-d1d2d3d4.py
Enter a starting anchor expression (e.g., , ) or path to a file containing a large integer.10^502^136279841-1

Press  or  after each step to advance continuously using the newly converged coordinate as the next anchor.Entery

Type  on restart to continue from .resumeprime_search_checkpoint.json
