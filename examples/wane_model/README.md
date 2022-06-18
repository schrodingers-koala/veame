Example: Wane Model
===================

Some kind of vaccine provide us life-long immunity. 
On the other hand, immunity by some kind of vaccine like influenza vaccines decreases over time.
This example shows a model with waning vaccine efficacy.

Model
-----

The model of this example is same as [Simple Model](../simple_model/README.md) excepting the followings.

- The vaccine effect reduces the infection rate of vaccined individuals to 0%.
- The infection rate of vaccined individuals increases over time after vaccination.
- Changes in the infection rate are implemented with ParameterUpdater.

See [report](./report/model_report.md) of model for further details.

Infection Rate
--------------

The infection rate is calculated as below.

infection_rate = infection_immune_adjust_c19 x infection_ratio_c19 x infection_base_rate_c19

Parameter description:
- infection_immune_adjust_c19: parameter of the vaccine effect.
- infection_ratio_c19: 0 before epidemic, 1 during epidemic.
- infection_base_rate_c19: base infection rate (for example, infection rate in a country).

ParameterUpdater
----------------

ParameterUpdater updates the value of infection_immune_adjust_c19.
In this example, infection_immune_adjust_c19 increases 0.05 per week up to 0.60.

```python
time_and_parameters = {
    7: {"infection_immune_adjust_c19": 0.05},
    14: {"infection_immune_adjust_c19": 0.10},
    21: {"infection_immune_adjust_c19": 0.15},
    28: {"infection_immune_adjust_c19": 0.20},
    35: {"infection_immune_adjust_c19": 0.25},
    42: {"infection_immune_adjust_c19": 0.30},
    49: {"infection_immune_adjust_c19": 0.35},
    56: {"infection_immune_adjust_c19": 0.40},
    63: {"infection_immune_adjust_c19": 0.45},
    70: {"infection_immune_adjust_c19": 0.50},
    77: {"infection_immune_adjust_c19": 0.55},
    84: {"infection_immune_adjust_c19": 0.60},
}
pu = ParameterUpdater(
    "vac_wane",
    time_and_parameters,
    state_for_activate=sm_vaceffstatus("vaceff"),
    state_for_deactivate=sm_vaceffstatus("no_vaceff"),
)
```
