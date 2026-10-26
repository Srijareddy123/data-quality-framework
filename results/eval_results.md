Command: `python -m dqf.evaluate --trials 200 --seed 7`

200 trials per row, 500 rows per load. The false-positive rate is the share of clean loads that the same checks flagged.

| Defect | Level | Detection rate (95% CI) | False-positive rate (95% CI) |
|---|---|---|---|
| nulls | 2% of one column | 137/200 = 68.5% (61.8% to 74.5%) | 0/200 = 0.0% (0.0% to 1.9%) |
| nulls | 10% of one column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| nulls | 30% of one column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| schema_change | drop_column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| schema_change | rename_column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| schema_change | add_column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| schema_change | retype_column | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| value_drift | one column +5% | 9/200 = 4.5% (2.4% to 8.3%) | 0/200 = 0.0% (0.0% to 1.9%) |
| value_drift | one column +20% | 182/200 = 91.0% (86.2% to 94.2%) | 3/200 = 1.5% (0.5% to 4.3%) |
| value_drift | one column +50% | 200/200 = 100.0% (98.1% to 100.0%) | 1/200 = 0.5% (0.1% to 2.8%) |
| row_loss | 80% of rows kept | 0/200 = 0.0% (0.0% to 1.9%) | 0/200 = 0.0% (0.0% to 1.9%) |
| row_loss | 50% of rows kept | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |
| row_loss | 10% of rows kept | 200/200 = 100.0% (98.1% to 100.0%) | 0/200 = 0.0% (0.0% to 1.9%) |

Clean loads flagged by any check: 10/2600 = 0.4%.
