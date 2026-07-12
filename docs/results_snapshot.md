# Results Snapshot

Generated from a 50,000-row sample of the UCI Online Retail dataset.

## Dataset Preparation

| Metric | Value |
| --- | ---: |
| Source rows read | 50,000 |
| Normalized transaction rows | 32,114 |
| Dropped rows | 17,886 |
| Customers | 1,039 |
| Orders | 1,979 |
| Order items | 32,114 |

Main drop reason: missing `CustomerID`, with 17,881 occurrences before overlapping filters.

## Quality Gate

| Metric | Value |
| --- | ---: |
| Total checks | 25 |
| Passed checks | 25 |
| Failed checks | 0 |

## Top Countries By Revenue

| Country | Segment | Customers | Total orders | Paid | Canceled | Gross revenue |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| United Kingdom | domestic | 950 | 1,813 | 1,492 | 321 | 594,869.96 |
| Germany | export | 24 | 50 | 34 | 16 | 19,217.27 |
| France | export | 19 | 34 | 28 | 6 | 12,985.60 |
| EIRE | export | 3 | 20 | 15 | 5 | 8,813.88 |
| Netherlands | export | 2 | 3 | 3 | 0 | 8,784.48 |
| Australia | export | 4 | 6 | 5 | 1 | 8,187.23 |
| Japan | export | 3 | 4 | 3 | 1 | 7,705.07 |
| Sweden | export | 2 | 5 | 3 | 2 | 4,381.86 |

## Top Products By Revenue

| Product ID | Description | Units sold | Units canceled | Gross revenue |
| --- | --- | ---: | ---: | ---: |
| 22423 | REGENCY CAKESTAND 3 TIER | 1,807 | 98 | 20,432.85 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | 4,577 | 530 | 12,159.75 |
| 79321 | CHILLI LIGHTS | 2,402 | 73 | 10,071.34 |
| 82484 | WOOD BLACK BOARD ANT WHITE FINISH | 1,396 | 2 | 7,046.28 |
| 21623 | VINTAGE UNION JACK MEMOBOARD | 1,063 | 0 | 6,978.29 |
| 21137 | BLACK RECORD COVER FRAME | 2,015 | 0 | 6,852.09 |
| 85099B | JUMBO BAG RED RETROSPOT | 3,426 | 126 | 5,930.70 |
| 22189 | CREAM HEART CARD HOLDER | 2,306 | 0 | 5,741.98 |

## Generated Files

- `reports/dataset_preparation_report.json`
- `reports/quality_report.json`
- `reports/run_summary.json`
- `reports/airflow_validation.json`
- `data/processed/marts/daily_revenue.csv`
- `data/processed/marts/customer_revenue.csv`
- `data/processed/marts/product_revenue.csv`
- `data/processed/marts/country_revenue.csv`
