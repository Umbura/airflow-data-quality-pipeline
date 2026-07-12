# Dataset Attribution

This project uses normalized tables derived from the UCI Machine Learning Repository **Online Retail** dataset.

- Dataset: Online Retail
- Creator: Daqing Chen
- Repository: UCI Machine Learning Repository
- DOI: https://doi.org/10.24432/C5BW33
- Source page: https://archive.ics.uci.edu/dataset/352/online%2Bretail
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)

Citation:

```text
Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33
```

The upstream source file is not committed to this repository. Normalized tables generated from all 541,909 source rows are committed under `data/raw/` for reproducible validation. Use `uv run retail-prepare-uci` to read the documented CSV mirror and regenerate those files.
