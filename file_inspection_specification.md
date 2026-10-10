\# Autonomous Visual Quality Inspector for Small Manufacturers



\## 1. Project Objective

Build a visual inspection system that helps small manufacturers identify potentially defective products using images.



\## 2. Supported Input

\- Product image uploaded by an inspector.

\- Supported image formats: JPG, JPEG, PNG.

\- Images must be readable and contain the product to be inspected.



\## 3. Inspection Outcomes

\- \*\*PASS:\*\* The product meets the configured acceptance criteria.

\- \*\*REVIEW:\*\* The result is uncertain and requires human inspection.

\- \*\*FAIL:\*\* The product appears to violate the configured quality criteria.



These outcomes must be based on validated inspection rules. Thresholds must not be invented before model validation.



\## 4. Human Review

\- Inspectors can review uncertain or flagged products.

\- Reviewers can record whether a prediction was correct.

\- Corrections should be stored with the inspection record.

\- Human corrections must not automatically change the trained model.



\## 5. Inspection Records

Each inspection should eventually record:

\- Unique inspection ID

\- Image filename

\- Inspection timestamp

\- Prediction and anomaly score, when available

\- Final decision

\- Reviewer correction, when applicable

\- Model version, when available



\## 6. Model Version Safety

\- Preserve the currently approved model.

\- Validate a candidate model before promotion.

\- Record the model version used for each inspection.

\- Keep a recoverable previous version before replacing an approved model.



\## 7. Data and Safety

\- Preserve original images and ground-truth annotations.

\- Keep training, validation, and test data separate.

\- Do not treat unverified predictions as confirmed defects.

\- Restrict access to inspection records and uploaded images as appropriate.



\## 8. Evaluation Requirements

Before claiming successful inspection performance, measure:

\- Image-level AUROC

\- Pixel-level AUROC when valid defect masks are available

\- Inference time

\- False positives and false negatives

\- Performance under lighting and alignment changes



\## 9. Current Limitations

\- Model integration is pending.

\- Decision thresholds are not yet calibrated.

\- Human-review and rollback workflows are not yet verified.

\- Final performance claims require measured experimental results.

