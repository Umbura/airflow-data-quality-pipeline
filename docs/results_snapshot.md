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
| Total checks | 14 |
| Passed checks | 14 |
| Failed checks | 0 |

## Top Countries By Revenue

| Country | Segment | Customers | Orders | Gross revenue |
| --- | --- | ---: | ---: | ---: |
| United Kingdom | domestic | 950 | 1,813 | 594,869.96 |
| Germany | export | 24 | 50 | 19,217.27 |
| France | export | 19 | 34 | 12,985.60 |
| EIRE | export | 3 | 20 | 8,813.88 |
| Netherlands | export | 2 | 3 | 8,784.48 |
| Australia | export | 4 | 6 | 8,187.23 |
| Japan | export | 3 | 4 | 7,705.07 |
| Sweden | export | 2 | 5 | 4,381.86 |

## Top Products By Revenue

| Product ID | Description | Units sold | Gross revenue |
| --- | --- | ---: | ---: |
| 22423 | REGENCY CAKESTAND 3 TIER | 1,905 | 20,432.85 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | 5,107 | 12,159.75 |
| 79321 | CHILLI LIGHTS | 2,475 | 10,071.34 |
| 82484 | WOOD BLACK BOARD ANT WHITE FINISH | 1,398 | 7,046.28 |
| 21623 | VINTAGE UNION JACK MEMOBOARD | 1,063 | 6,978.29 |
| 21137 | BLACK RECORD COVER FRAME | 2,015 | 6,852.09 |
| 85099B | JUMBO BAG RED RETROSPOT | 3,552 | 5,930.70 |
| 22189 | CREAM HEART CARD HOLDER | 2,306 | 5,741.98 |

## Generated Files

- `reports/dataset_preparation_report.json`
- `reports/quality_report.json`
- `reports/run_summary.json`
- `data/processed/marts/daily_revenue.csv`
- `data/processed/marts/customer_revenue.csv`
- `data/processed/marts/product_revenue.csv`
- `data/processed/marts/country_revenue.csv`
