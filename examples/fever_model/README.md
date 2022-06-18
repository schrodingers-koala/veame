Example: Fever Model
====================

This example shows a model using VEAME's samples of state machine.

Model
-----

An overview of the model is as follows.

- Vaccine or placebo (up to two doses)
- Constant infection rate
- Symptom varying probablistically
  - 4 levels of symptom
- PCR tests applied to patients with fever
- Adverse effects of vaccine
  - Fever
  - Worsening of chronic disease
- Error of PCR tests (false-positive, false-negative)

See [report](./report/model_report.md) of the model for further details.
