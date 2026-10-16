# Data

`raw/` preserves the original downloaded attachments locally. The datasets are ignored by Git and are not included in the public repository. Place organizer-provided copies here:

| File | Records | Columns |
| --- | ---: | ---: |
| engagement_behavior.csv | 20,000 | 8 |
| monetization_potential.csv | 20,000 | 6 |
| risk_and_churn_metrics.csv | 20,000 | 7 |
| all_users_combined.xlsx | See `all_users` sheet | Combined data |

The workbook contains `Start here` and `all_users` sheets. The addendum describes it as the four datasets pre-joined on `user_id`.

`user_profiles.csv` is mentioned in the case and email but was not among the six attachments. Do not treat a reconstructed file as an original organizer attachment.

Preserve blanks and outliers in raw inputs. Record cleaning decisions and place generated files in `processed/`, which is ignored by Git.
