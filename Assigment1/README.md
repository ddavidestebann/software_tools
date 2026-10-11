# MapleFreight: Delivery Delay Prediction & Slack Alerts

### AML 3303, Assessment 1 · David Aponte Monroy (C0967956)

An end-to-end system that predicts which in-transit shipments will be delivered late and posts an alert to the `#dispatch-alerts` Slack channel while dispatch still has time to re-route or warn the customer.

## Problem

MapleFreight finds delays only after the delivery window has passed. By then it has paid service credits, booked expedited re-deliveries and received complaints that reach the account manager before dispatch knows anything is wrong. On-time performance has dropped from 94% to 88% this year.

**Objectives**

1. Analyse shipment, route and carrier data to find the main drivers of late delivery.
2. Build a model that classifies whether a shipment will be delivered late.
3. Notify dispatch in Slack about high-risk shipments automatically.
4. Give actionable recommendations to improve on-time performance.

## Dataset

`maplefreight_delivery_delay_dataset.csv` (included in this repository) has 6,035 shipments and 23 columns. The target is `delivered_late` (1 = missed the promised window), and about 21% of shipments are late.

Cleaning applied in the notebook:

| Issue                                                                           | Fix                                                                                     |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 32 exact duplicates and 3 repeated`shipment_id`s                              | Removed, leaving 6,000 rows                                                             |
| Inconsistent spelling in text columns (`service_level` had 6 distinct values) | Text columns stripped and lower-cased, leaving 3 service levels                         |
| 40`weight_kg` values entered in grams (170,900 to 2,999,300)                  | Divided by 1,000, which puts them inside the normal range (30 to 5,044 kg)              |
| Missing values in fuel cost, driver experience, weather and traffic (2 to 4%)   | Median or`"Unknown"` imputation inside the sklearn pipeline, plus missing-value flags |
| `actual_transit_hours` is only known after delivery (leakage)                 | Dropped from the features                                                               |

Missing values affect 686 rows (11%), so they are imputed and not dropped. The late rate is the same with and without missing values (20.6%).

## Repository contents

| File                                                      | Purpose                                               |
| --------------------------------------------------------- | ----------------------------------------------------- |
| `MapleFreight_Delivery_Delay_Prediction_C0967956.ipynb` | Full notebook, run top to bottom with outputs         |
| `maplefreight_delivery_delay_dataset.csv`               | Raw dataset                                           |
| `screenshots/slack_alert.png`                           | The Slack alert as it appeared in`#dispatch-alerts` |
| `requirements.txt`                                      | Python dependencies                                   |
| `.env.example`                                          | Template for the Slack webhook variable               |
| `.gitignore`                                            | Keeps`.env` (the real webhook) out of git           |

## How to run

Requires Python 3.12 or newer.

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env            # macOS/Linux: cp .env.example .env
# edit .env and paste your Slack Incoming Webhook URL into WEBHOOK_URL

jupyter notebook MapleFreight_Delivery_Delay_Prediction_C0967956.ipynb   # Kernel > Restart & Run All
```

Slack setup: create a workspace and a `#dispatch-alerts` channel, create a Slack app, turn on **Incoming Webhooks**, add a webhook for that channel and paste its URL into `.env`. If `WEBHOOK_URL` is not set, the notebook still runs and skips the post. The webhook URL is never printed.

## Notebook structure

1. Context, problem statement and objectives
2. Data understanding (quality audit: duplicates, nulls, outliers, leakage)
3. Data preprocessing (cleaning)
4. Exploratory data analysis
5. Feature engineering
6. Data preparation (train/test split and preprocessing pipeline)
7. Data modelling (Logistic Regression baseline, Random Forest, Hist Gradient Boosting)
8. Model evaluation and threshold selection
9. Model explainability
10. Slack alert integration
11. Recommendations

## Approach

Data audit → cleaning → EDA → feature engineering → stratified 80/20 split (4,800 train / 1,200 test) → sklearn `Pipeline` (imputation, scaling, one-hot) → 5-fold CV comparison of three models → threshold chosen on out-of-fold predictions → one-time test evaluation → permutation importance and coefficients → Slack alert.

Class imbalance is handled with `class_weight="balanced"`. Models are compared on PR-AUC, precision, recall and F1, not accuracy: always predicting "on time" would score 79% accuracy and catch no delays.

## Key findings

**Drivers of late delivery (EDA and model explainability)**

- **Weather:** storm 46% and snow 34% late vs. 14% for clear weather. It is the most important feature of the model.
- **Carrier:** contract owner-operators 36% late vs. 13% for the MapleFreight fleet.
- **Route complexity:** 12% late with no stops vs. 29% with 5. Longer distance and transit time also raise the risk.
- **Conditions at dispatch:** heavy traffic (32% vs. 12%), route congestion (27% vs. 16%), a pickup more than 30 minutes late (27% vs. 15%) and recent carrier lateness.
- **Driver experience:** under 3 years 26% vs. over 10 years 14%. Economy service is late 27% of the time vs. 15% for Express.
- **Little or no signal:** customer tier (Gold accounts are late as often as Bronze) and destination city.
- **Risks add up:** a pickup 30 to 60 minutes late on a trip longer than 12 hours is late 38% of the time.

**Model comparison (5-fold cross-validation on the training set, default 0.5 threshold)**

| Model                                 | Accuracy | Precision | Recall          | F1              | PR-AUC          | ROC-AUC         |
| ------------------------------------- | -------- | --------- | --------------- | --------------- | --------------- | --------------- |
| **Logistic Regression (final)** | 0.740    | 0.423     | **0.723** | **0.533** | **0.558** | **0.808** |
| Random Forest                         | 0.786    | 0.484     | 0.551           | 0.515           | 0.527           | 0.792           |
| Hist Gradient Boosting                | 0.790    | 0.493     | 0.456           | 0.473           | 0.506           | 0.780           |

The two tree models get a higher accuracy, but they find fewer late shipments. Logistic regression has the best PR-AUC, ROC-AUC and recall, so it is the final model. The risk factors act mostly additively, so a linear model captures them well and is easy to explain.

**Final model on the held-out test set (threshold 0.47)**

| Precision | Recall | F1    |
| --------- | ------ | ----- |
| 0.431     | 0.769  | 0.552 |

Confusion matrix: **190 of 247 late shipments caught**, 57 missed, 251 false alarms and 702 correct "on time" predictions.

**What drives the model (permutation importance on the test set, drop in PR-AUC)**

`weather_severity` (0.118), `distance_km` (0.111), `num_stops` (0.096), `traffic_index` (0.077), `carrier` (0.072), `pickup_delay_minutes` (0.056) and `route_congestion_score` (0.050). Risk goes up with contract owner-operators, more stops, weather severity, distance, traffic and Economy service, and goes down with the MapleFreight fleet, Express service and driver experience. `actual_transit_hours` is not among the features.

## Alert threshold and why

**Threshold = 0.47.** This is the highest risk score that still catches at least **75% of late shipments**. It was chosen on out-of-fold predictions from the training set, so the test set played no part in the choice. The test set was used once, at the end.

| Recall target | Threshold       |
| ------------- | --------------- |
| 72%           | 0.504           |
| **75%** | **0.467** |
| 80%           | 0.412           |

- A missed delay costs a service credit, an expedited re-delivery and a complaint. A false alarm costs a dispatcher a few minutes, so recall is the priority.
- At 0.47, about 2 in 5 alerts are real late shipments (precision 0.43), twice the 21% base rate.
- A higher threshold gives fewer alerts and higher precision, but recall drops below 72%. A lower one catches more delays, but precision falls and the number of flagged shipments grows, which creates alert fatigue.
- The threshold flags about 37% of shipments (441 of 1,200 in the test set), so the Slack message gives the count and only the top 5 by risk. The 75% recall target is a business assumption and should be reviewed with dispatch.

## Slack alert

The message starts with how many shipments are at risk, then lists the top 5 with shipment ID, destination, carrier and risk score. It is short enough to read on a phone. The screenshot is in `screenshots/slack_alert.png`.

## Recommendations

1. **Weather playbook:** when the forecast is snow or storm, give the customer a longer delivery estimate or warn them up front, and assign those loads to the most experienced drivers.
2. **Realistic promises on complex routes:** add time per stop and per extra 100 km to the scheduled transit hours, and revisit Economy promise times.
3. **Pickup punctuality:** treat a pickup more than 30 minutes late as a trigger to re-score the shipment and contact the customer.
4. **Driver and fleet:** pair new drivers with mentors on long or bad-weather routes, and plan the replacement of the oldest vehicles.

## AI usage

AI assistant used: **Claude Code (Anthropic), with Claude Opus 5.5 and Claude Sonnet 5.5**. I used it as a tutor and code reviewer, and I ran every cell myself. After an initial reference solution generated by the assistant, I rebuilt the notebook cell by cell in my own file. For each section the assistant explained the purpose of the step and asked me comprehension questions. It then reviewed my saved notebook and pointed out errors that I fixed. It also supplied code and wording that I adapted: the threshold search, the Slack message cell, the explainability cells and the English text of some findings.

**Cases where the AI output was wrong:**

1. **Spelling normalisation broke valid names.** In the first reference draft the assistant applied `.str.title()` to every categorical column. This changed `Toronto ON` to `Toronto On` and `MapleFreight Fleet` to `Maplefreight Fleet`, which showed up as wrong names in the Slack message preview. The fix was a consistent case across text columns, with a lookup that restores the original spelling for the message.
2. **A wrong threshold value.** The assistant said the 0.01-step threshold loop would return 0.47, but it returns 0.46 because the grid skips the exact value of 0.467. I used a 0.001 step.
3. **A wrong domain hypothesis.** The assistant assumed a late pickup would hurt short trips more and engineered `pickup_delay_ratio` for that reason. The pickup-delay × transit-time heatmap showed the opposite (long trips with late pickups are the worst, at 38% late), and the ratio is weaker than the raw delay.
4. **Parallel cross-validation crashed on Windows.** `n_jobs=-1` raised `BrokenProcessPool` inside Jupyter, so cross-validation runs in a single process (`N_JOBS = 1`).
