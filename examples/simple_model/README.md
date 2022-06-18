Example: Simple Model
=====================

This example shows a model of two doses vaccination and simulation results.
A simplified model is used for understanding essential natures by excluding factors which complicate vaccine efficacy analyses.

Model
-----

An overview of the model is as follows.<a id="Model"></a>

- No dose or two doses vaccination.
- The first dose:
  - Efficacy is 30%:
    - The probability that the first dose for an individual takes effect and the individual get full immunity is 30%.
    - The probability that the first dose for an individual takes no effect is 70%.
  - If the first dose takes effect for an individual, it takes 7-14 days after the first dose for the individual to get full immunity.
- The second dose:
  - Efficacy is 30% for individuals without full immunity.
  - If an individual has full immunity, the second dose takes no effect for the individual.
  - If the second dose takes effect for an individual, it takes 3-7 days after the second dose for the individual to get full immunity.
  - Total efficacy with the first dose and the second dose is 51% (= 1.0 - 0.7 x 0.7).
- The infection rate is constant (0.0007 / person day)(*).
- Any individual with full immunity doesn't infect.
- Any person has fever 2-6 days after infection.
- Any infected person tests positive with 100% probability.

See [report](./report/model_report.md) of the model for further details.

(*) The infection rate is calculated as follows.

In a country with 1 million population which is almost equivalent to San Francisco, the infection rate is 0.0001 per day when 100 people test positive a day.
To assume vaccine efficacy is 85%, the infection rate in the case of no vaccination is
0.0001 / (1 - 0.85) = 0.0007.


Simulation
----------

An overview of the simulation is as follows.

- The simulation period is 4 months (from 9/1/2021 to 1/1/2022).
- The sample size (the number of persons) is 30000.
- The vaccination period is 2 months (from 9/1/2021 to 11/1/2021)
- The ratio of vaccination:
  - No dose: 10%
  - One dose: 0%
  - Two doses: 90% (equivalent to the ratio in Israel)

```console
$ python ./examples/simple_model/vaceff_simple_model.py --task sim --config config_september_2021_no_adv.py --count 30000
```

Analysis
--------

This example uses the analysis method in the [paper][1] by the Ministry of Health in Israel.
This paper used negative binomial regression model to calculate incidence rate ratio.
In this example, incidence rate is used for simplification.

- Vaccine efficacy (VE) is 1 - incidence rate of fully vaccinated people / incidence rate of unvaccinated people.
- Incidence rate is incidence per person day.
- Unvaccinated individuals are defined as those who doesn't receive the first dose of vaccine.
- Fully vaccinated individuals are defined as those for whom 7 days had passed since receiving the second dose of vaccine.

```console
$ python ./examples/simple_model/vaceff_simple_data_analyze_vac_during_pandemic.py --input simple_model_September_January_eff1_7_3_0_0_eff2_7_3_0_0_vacdist_1_0_9_30000.dat
```

Result
------

Result of the analysis shows that vaccine efficacy is 54%.
This value is nearly equal to the vaccine efficacy of the [model](#Model) (51%).
The analysis seems to be correct in this model which infection rate is constant.

|             | Analysis   |
| :---------: | :--------: |
| Simulation  | 0.54       |

By the way, what happens if the infection rate varies with time?
See the next [example](../simple_model_with_varying_infection_rate/README.md) for further evaluations of the analysis.

Future Work
-----------

Iterating simulation can provides the error distribution of vaccine efficacy and enables evaluations of error.
Calculating the error distribution will be supported in the future.


[1]: https://www.thelancet.com/article/S0140-6736(21)00947-8/fulltext
