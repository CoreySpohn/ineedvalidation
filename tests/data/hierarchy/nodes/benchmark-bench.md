---
id: benchmark-bench
level: benchmark
title: Bench loop closure
couples_to:
- subsystem-mixer
cases:
- bench-loop
libraries:
- widgetlib
srqs:
- loop residual
referent: bench loop data
referent_status: in-hand
evidence:
- code-verification
- validation
validation_level: 2
domain_overlap:
  covers:
  - loop-bandwidth
  - actuator-count
  misses:
  - residual-amplitude
---
# Bench loop closure

One effect at a time against a measurement in hand.
