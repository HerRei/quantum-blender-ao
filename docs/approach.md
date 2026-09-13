# Approach

## The idea

The project uses ambient visibility as a small rendering problem that is easy to explain.
At a point on the floor, look in `N` fixed directions over the upper hemisphere:

```text
f(i) = 1 if Blender's ray i reaches open space
f(i) = 0 if it hits geometry

visibility = average of f(i)
```

A value near one means open sky; a value near zero means the point is enclosed. Blender
uses that value to colour the tile, so the estimator visibly affects the image.

## The comparison

- **Exact** reads every entry of the table. It is the reference result.
- **Monte Carlo** samples entries at random and averages them.
- **Simulated QAE** puts the direction index into a uniform superposition, marks the open
  directions with a truth-table oracle, applies Grover powers, takes finite shots, and
  uses maximum-likelihood amplitude estimation.

Monte Carlo receives the same logical lookup-query budget that QAE actually uses. The
saved JSON records the estimates, queries, shots, qubits, circuit depth, gate count, and
timings.

## What the demo teaches

It makes three things concrete:

1. A quantum circuit can feed a real visual pipeline rather than merely print a number.
2. Approximate methods can produce visibly different images from the exact reference.
3. Logical query complexity is not the same as practical cost: the default QAE circuits
   can be deep even for a tiny 16-direction table.

## What it does not claim

Blender performs every ray/geometry intersection first, on a classical computer. The
oracle is then built from that finished binary table. This is therefore quantum-assisted
visibility estimation, not quantum ray tracing or an end-to-end rendering speed-up.

Likewise, simulator time is not QPU time. A real-hardware extension should test only a
few representative probes and report device noise, transpilation, queue time, and QPU
usage separately.

## How to read the results

Start with one probe and four directions, then the binary table. Compare the three
estimators, look at the three renders, and finish with the error and circuit-resource
numbers from `generated/results.json`. The honest conclusion can be negative: this project
explores where a quantum estimator could fit into graphics, not a claim that current
hardware has already won.
