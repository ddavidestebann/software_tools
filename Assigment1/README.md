# MapleFreight: Delivery Delay Prediction & Slack Alerts

AML 3303, Assessment 1 · David Aponte Monroy

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

| Issue                                                                         | Fix                                                                                     |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 32 exact duplicates and 3 repeated`shipment_id`s                            | Removed, leaving 6,000 rows                                                             |
| `service_level` spelled both `Standard` and `standard`                  | Mapped to the most frequent spelling                                                    |
| 40`weight_kg` values entered in grams (170,000 to 3,000,000)                | Divided by 1,000                                                                        |
| Missing values in fuel cost, driver experience, weather and traffic (2 to 4%) | Median or`"Unknown"` imputation inside the sklearn pipeline, plus missing-value flags |
| `actual_transit_hours` is only known after delivery (leakage)               | Dropped from the features                                                               |

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


**Workflow**

1. Contex
2. Problem statement
3. Objectives
4. Data understanding (data quality audit)
5. Data preprocessing (cleaning)
6. Exploratory data analysis (EDA)
7. Feature engineering
8. Data preparation (split + preprocessing pipeline)
9. Data modelling (baseline vs. candidates)
10. Model evaluation and threshold selection
11. Model explainability
12. Slack alert integration
13. Recommendations

## Approach

Data audit → cleaning → EDA → feature engineering → stratified 80/20 split → sklearn `Pipeline` (imputation, scaling, one-hot) → 5-fold CV comparison → threshold chosen on out-of-fold predictions → one-time test evaluation → permutation importance → Slack alert.

Class imbalance is handled with `class_weight="balanced"`. Models are compared on PR-AUC, precision, recall and F1, not accuracy.

## Key findings

**Drivers of late delivery (EDA and model explainability)**

- **Weather:** storm 46% and snow 34% late vs. 14% for clear weather. This is the most important model feature.
- **Carrier:** contract owner-operators 36% late vs. 13% for the MapleFreight fleet.
- **Route complexity:** 12% late with no stops vs. 29% with 5. Longer distance and transit time also raise the risk.
- **Conditions at dispatch:** heavy traffic (32% vs. 12%), route congestion, a pickup more than 30 minutes late (27% vs. 15%) and recent carrier lateness.
- **Driver experience:** under 3 years 26% vs. over 10 years 14%. Economy service is late 27% of the time vs. 15% for Express.
- **No signal:** customer tier (Gold accounts are late as often as Bronze) and destination.

**Models**

On the test set, each model uses its own threshold set for at least 75% recall:

| Model                                           | Precision       | Recall          | F1              | PR-AUC          | ROC-AUC         |
| ----------------------------------------------- | --------------- | --------------- | --------------- | --------------- | --------------- |
| Dummy (always "on time"), 79% accuracy          | 0.000           | 0.000           | 0.000           | 0.206           | 0.500           |
| **Logistic Regression (baseline, final)** | **0.431** | **0.769** | **0.552** | **0.600** | **0.831** |
| Random Forest                                   | 0.412           | 0.798           | 0.543           | 0.556           | 0.820           |
| Tuned Hist Gradient Boosting                    | 0.426           | 0.781           | 0.551           | 0.551           | 0.819           |

The baseline logistic regression stayed the best model. Tuned gradient boosting and random forest did not beat it on cross-validated PR-AUC (0.538 and 0.524 vs. 0.558). The risk factors act mostly additively, so a linear model captures them well and is easier to explain. Confusion matrix of the final model on the test set: **190 of 247 late shipments caught**, 57 missed, 251 false alarms and 702 correct "on time" predictions.

## Alert threshold and why

**Threshold = 0.47.** This is the highest risk score that still catches at least **75% of late shipments**. It was chosen on out-of-fold predictions from the training set, so the test set played no part in the choice.

- A missed delay costs a service credit, an expedited re-delivery and a complaint. A false alarm costs a dispatcher a few minutes, so recall is the priority.
- At 0.47, about 2 in 5 alerts are real late shipments (precision 0.43), twice the 21% base rate. The F1-optimal threshold (0.56) would lose 9 points of recall for only 6 points of precision.
- The threshold flags about 37% of shipments, so the Slack message gives the count and only the top 5 by risk. The recommended next step is two alert tiers (0.80 or more: act now; 0.47 to 0.80: digest), with the threshold reviewed monthly with dispatch.

## Recommendations

1. A bad-weather playbook: add buffer time or warn the customer when the forecast is snow or storm.
2. Send long and multi-stop loads to the company fleet first. Set on-time KPIs for owner-operators.
3. Add time per stop and per distance to promised transit times. Revisit Economy promises.
4. Treat a pickup more than 30 minutes late as a trigger to re-score and contact the customer.
5. Tiered alerts, Gold accounts first, a pilot on owner-operator and long-haul lanes, and a monthly threshold review.

## AI usage

AI assistant used: **Claude Code (Anthropic, Claude Opus 5.5)**. I used it to structure the notebook, write the cleaning, modelling and Slack code, and draft the explanations. I reviewed and ran every cell myself.

**Cases where the AI output was wrong:**

1. **Spelling normalisation broke valid names.** To fix `standard` vs. `Standard`, the assistant first applied `.str.title()` to every categorical column. This also changed `Toronto ON` to `Toronto On` and `MapleFreight Fleet` to `Maplefreight Fleet`, which showed up as wrong names in the Slack message preview. The fix maps each case variant to its most frequent original spelling.
2. **A wrong domain hypothesis.** The assistant assumed a late pickup would hurt short trips more and engineered `pickup_delay_ratio` for that reason. The pickup-delay × transit-time heatmap showed the opposite (long trips with late pickups are the worst, at 38% late), and the ratio turned out weaker than the raw delay (r = 0.03 vs. 0.13).
3. **Parallel cross-validation crashed on Windows.** `n_jobs=-1` raised `BrokenProcessPool` inside Jupyter, so cross-validation now runs in a single process.
