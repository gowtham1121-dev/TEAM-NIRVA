\# Model Versioning, Feedback and Rollback Policy



\## 1. Purpose

Ensure that updates to the Autonomous Visual Quality Inspector are validated before use and that the previously approved model can be restored if an update performs poorly.



\## 2. Model Version Identification

Each candidate model should have:

\- A unique version identifier

\- Creation date

\- Model architecture and configuration

\- Training dataset version

\- Preprocessing configuration

\- Validation results

\- Approval status



Example version names: `patchcore-v1`, `patchcore-v2`.



These are naming examples, not evidence that those model versions currently exist.



\## 3. Inspector Feedback

An inspector should be able to record:

\- Original inspection result

\- Corrected result

\- Reason for correction

\- Reviewer identifier, if applicable

\- Correction timestamp



Feedback must be stored separately from the original model prediction.



\## 4. Model Update Workflow

1\. Collect and review inspection feedback.

2\. Verify image labels before including images in a training dataset.

3\. Prepare a candidate model using an approved dataset.

4\. Evaluate the candidate using a fixed validation set.

5\. Compare its performance with the currently approved model.

6\. Approve the candidate only if it meets defined acceptance criteria.

7\. Preserve the previous approved model before deployment.

8\. Record the newly approved model version.



\## 5. Rollback Conditions

Consider rollback when:

\- Validation performance drops below the approved limit.

\- False positives or false negatives increase unacceptably.

\- Predictions become unstable on known test cases.

\- The model fails to load or inference errors occur.

\- A deployment causes unacceptable response times.



The exact numerical limits must be established from measured baseline results.



\## 6. Rollback Procedure

1\. Stop promotion of the candidate model.

2\. Restore the previous approved model artifact and its matching configuration.

3\. Verify that the restored model loads successfully.

4\. Run known test images and compare outputs against recorded baseline results.

5\. Confirm that the inspection pipeline works correctly.

6\. Record the rollback reason, timestamp, and affected versions.



\## 7. Audit and Safety

\- Never overwrite the only copy of the approved model.

\- Keep model artifacts and configurations version-matched.

\- Record which model version produced each inspection result.

\- Do not automatically retrain or promote a model based solely on inspector feedback.

\- Preserve original inspection records for auditability.



\## 8. Current Implementation Status

This document defines the intended workflow. Automated feedback capture, model registry, candidate validation, model promotion, and rollback have not yet been implemented or verified.

