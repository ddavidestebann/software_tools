# MapleFreight Late-Shipment Prediction: Project Workflow

End-to-end system that predicts which in-transit shipments will arrive late and alerts dispatch in Slack early enough to re-route or warn the customer.

## 1. Context

- MapleFreight finds delays only after the delivery window has passed.
- Consequences: paid-out service credits, expedited re-deliveries, and complaints reaching the account manager before dispatch knows anything is wrong.
- Role: Data Scientist. Deliverable: a prediction pipeline plus a live alerting channel.

## 2. Problem Statement

- Detect, while a shipment is still in transit, whether it will miss its delivery window.
- Shift the company from reactive (post-delay) to proactive (pre-delay) operations.
- Framing: binary classification (`late` = actual arrival > promised window end), scored on in-transit shipments at regular intervals.

## 3. Objective

- Business: cut service credits, expedited re-deliveries, and escalated complaints.
- Technical: a model with high recall on late shipments at a precision dispatch can tolerate (avoid alert fatigue), producing a calibrated risk score.
- Operational: a Slack alert with enough lead time to act, including shipment ID, customer, route, risk score, and top reasons.

## 4. Data Understanding

- Inventory sources: shipments (origin, destination, carrier, service level, weight/volume), promised vs. actual timestamps, tracking events/scans, route/lane info, weather, holidays, customer/account data.
- Check grain (one row per shipment vs. per event), keys, date ranges, data volume, and class balance (% late).
- Identify the label and the **prediction time**: what is known at each point in transit.
- Flag leakage risks: fields recorded after delivery, final status codes, actual transit time.

## 5. Exploratory Data Analysis (EDA)

- Late rate overall and by carrier, lane, service level, origin/destination, day of week, month, and season.
- Distributions of transit time, distance, weight; outliers and impossible values.
- Missing-value patterns and duplicates.
- Late rate vs. progress in transit (where on the route do delays appear?).
- Correlations and early signals (e.g., late first-leg departure, scan gaps, weather events).
- Time trends and drift (is the late rate changing?).

## 6. Data Preprocessing

- Parse timestamps and standardize time zones.
- Remove duplicates; fix invalid records (negative durations, delivery before pickup).
- Handle missing values (impute by group median/mode, add missing-indicator flags where informative).
- Treat outliers (cap/winsorize or keep if genuine).
- Encode and clean categoricals (normalize carrier/lane names, group rare categories).
- Build the label from promised vs. actual delivery times.

## 7. Feature Engineering

- **Time:** hour, day of week, month, holiday/weekend flags, time until promised delivery, time elapsed since pickup.
- **Route:** distance, lane, origin-destination pair, number of legs/stops, cross-border flag.
- **Progress:** % of route completed, hours since last scan, delay at last checkpoint vs. plan, departure delay.
- **Historical (as of prediction time only):** rolling late rate by carrier, lane, and customer.
- **External:** weather severity along route, traffic or congestion, holiday volume.
- **Shipment:** weight, volume, service level, customer tier.
- All features computed using only information available at prediction time (no leakage).

## 8. Data Preparation

- Time-based train / validation / test split (train on the past, test on the future) to mirror production.
- Fit encoders, scalers, and imputers on training data only; wrap them in a single sklearn `Pipeline` / `ColumnTransformer`.
- Handle class imbalance: class weights, or resampling on the training set only.
- Freeze the feature list and schema for reuse in serving.

## 9. Data Modelling

- Baselines: majority class and logistic regression.
- Candidates: Random Forest, XGBoost / LightGBM, optionally CatBoost for categorical-heavy data.
- Hyperparameter tuning with time-series cross-validation (Optuna or randomized search).
- Probability calibration (Platt or isotonic) so scores are meaningful risk levels.
- Select the final model on validation metrics, not test.

## 10. Model Evaluation

- Metrics: PR-AUC, ROC-AUC, recall, precision, F1/F2, confusion matrix, Brier score.
- Choose the alert threshold by business cost (cost of a missed delay vs. a false alarm) and dispatch capacity.
- Evaluate **lead time**: how many hours before the window closes the model flags a late shipment.
- Slice analysis by carrier, lane, and customer tier to check consistent performance.
- Final one-time score on the held-out test set versus the baseline.

## 11. Model Explainability

- Global: feature importance and SHAP summary plots.
- Local: per-shipment SHAP values, converted to a plain-language "top 3 reasons" (e.g., "left origin 6 h late", "storm on lane").
- Use the reasons in the alert so dispatch can trust the score and choose the right action.
- Sanity-check drivers against domain knowledge to catch leakage.

## 12. Slack Alert Integration

- Scheduled scoring job (e.g., every 30-60 min) scores all in-transit shipments with the saved pipeline.
- Trigger an alert when risk score ≥ threshold and the shipment has not been alerted already (deduplicate; re-alert only if risk rises materially).
- Post via a Slack Incoming Webhook or the Slack Web API (`chat.postMessage`) using Block Kit:
  - Shipment ID, customer, route, promised ETA, risk score, top reasons, suggested action (re-route / notify customer), link to the tracking page.
- Store secrets (Slack token, DB credentials) in environment variables / a secrets manager.
- Add logging, retries, and error alerts; track alert outcomes (acknowledged, delay averted, false alarm) for feedback.
- Monitoring: data drift, score distribution, precision/recall on realized outcomes; retrain on a schedule.

## 13. Recommendations

- Deploy as a pilot on high-impact lanes or key accounts first, then expand.
- Review the threshold monthly with dispatch to balance missed delays against alert fatigue.
- Feed alert outcomes back into training data (closed-loop learning).
- Improve data capture: more frequent scan events, live weather and traffic feeds, carrier ETA updates.
- Define action playbooks tied to risk bands (e.g., high risk → re-route; medium → proactive customer notice).
- Track business KPIs: service credits paid, expedited re-deliveries, complaint escalations, on-time %.

Pipeline at a Glance

### `Raw data → Clean → Features → Time-split → Train/Tune → Calibrate → Evaluate → Explain (SHAP) → Score in-transit shipments → Threshold → Slack alert → Feedback & monitorin`

# Problem, dataset, how to run, key findings, your chosen threshold and why, and the AI usage section

Problem: At MapleFreight. Delays are currently found only after the delivery window has passed, which means paid-out service credits, expedited re-deliveries and complaints that reach the account manager before dispatch knows anything is wrong.

Goal: Build an end-to-end system that predicts which in-transit shipments will arrive late and alerts dispatch in Slack while there is still time to re-route or warn the customer.

## Objectives

1. Analyze shipment, route and carrier data to identify the main drivers of late delivery.
2. Build a predictive model that classifies whether a shipment will be delivered late.
3. Integrate Slack alerts so dispatch is notified about high-risk shipments automatically.
4. Provide actionable recommendations that improve on-time performance.
