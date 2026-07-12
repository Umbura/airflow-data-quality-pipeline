# Results Snapshot

Generated from the complete UCI Online Retail CSV mirror.

## Dataset Preparation

| Metric | Value |
| --- | ---: |
| Source rows read | 541,909 |
| Normalized transaction rows | 406,789 |
| Dropped rows | 135,120 |
| Customers | 4,371 |
| Orders | 22,186 |
| Order items | 406,789 |

Main drop reason: missing `CustomerID`, with 135,080 occurrences before overlapping filters.

## Quality Gate

| Metric | Value |
| --- | ---: |
| Total checks | 25 |
| Passed checks | 25 |
| Failed checks | 0 |

## Top Countries By Revenue

| Country | Segment | Customers | Total orders | Paid | Canceled | Gross revenue |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| United Kingdom | domestic | 3,949 | 19,854 | 16,646 | 3,208 | 7,308,391.55 |
| Netherlands | export | 9 | 100 | 94 | 6 | 285,446.34 |
| EIRE | export | 3 | 319 | 260 | 59 | 265,545.90 |
| Germany | export | 95 | 603 | 457 | 146 | 228,867.14 |
| France | export | 87 | 458 | 389 | 69 | 209,024.05 |
| Australia | export | 9 | 72 | 60 | 12 | 139,911.45 |
| Spain | export | 29 | 100 | 85 | 15 | 60,372.85 |
| Switzerland | export | 20 | 73 | 52 | 21 | 56,419.29 |

## Top Products By Revenue

| Product ID | Description | Units sold | Units canceled | Gross revenue |
| --- | --- | ---: | ---: | ---: |
| 23843 | PAPER CRAFT, LITTLE BIRDIE | 80,995 | 80,995 | 168,469.60 |
| 22423 | REGENCY CAKESTAND 3 TIER | 12,402 | 857 | 142,592.95 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | 36,725 | 2,578 | 100,448.15 |
| 85099B | JUMBO BAG RED RETROSPOT | 46,181 | 1,115 | 85,220.78 |
| 23166 | MEDIUM CERAMIC TOP STORAGE JAR | 77,916 | 74,494 | 81,416.73 |
| POST | POSTAGE | 3,120 | 118 | 77,803.96 |
| 47566 | PARTY BUNTING | 15,291 | 268 | 68,844.33 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | 35,362 | 48 | 56,580.34 |

## Generated Files

- `reports/dataset_preparation_report.json`
- `reports/quality_report.json`
- `reports/run_summary.json`
- `reports/airflow_validation.json`
- `data/processed/marts/daily_revenue.csv`
- `data/processed/marts/customer_revenue.csv`
- `data/processed/marts/product_revenue.csv`
- `data/processed/marts/country_revenue.csv`
