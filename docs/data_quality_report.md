# Data Quality Report — Maharashtra APMC Mandi Price Data

Raw monthly price records loaded: 62,429
Raw MSP reference records loaded: 155

## 1. Commodity name normalization
- Distinct commodity labels before normalizing case/whitespace: 352
- Distinct commodity labels after normalizing (upper + strip):  202
- 150 labels were pure formatting duplicates (e.g. 'Amla' / 'AMLA' / 'Amla ' all collapse to one commodity).

## 2. Price-sanity checks
- Rows where min_price > max_price (impossible range): 296
- Rows with a zero or negative price:                  216
- Rows where modal_price falls outside [min, max]:     452
- Total rows excluded from price-based analysis:       485 (0.78% of all records)

Saved: data/processed/mandi_clean.csv  (62,429 rows, all rows + flags)
Saved: data/processed/mandi_valid.csv  (61,944 rows, price-sanity passed)

## 3. MSP (Minimum Support Price) merge
- Commodities covered by an official MSP, present in this data: 19
  ['BAJRI', 'COCONUT', 'COTTON', 'GR.NUT KERNELS', 'MAIZE', 'MUSTARD', 'NIGER-SEED', 'PADDY-UNHUSKED', 'PIGEON PEA (TUR)', 'RICE(PADDY-HUS)', 'SAFFLOWER', 'SESAMUM', 'SORGUM(JAWAR)', 'SPILT GERRN GRAM', 'SPLIT BLACK GRAM', 'SUGARCANE', 'SUNFLOWER', 'WHEAT(HUSKED)', 'WHEAT(UNHUSKED)']
- MSP applies to national staple/policy crops only (cereals, pulses, oilseeds, cotton, sugarcane) — not to most fruits and vegetables, so this is expected, not a data problem.
- Rows in the MSP-eligible subset used for the compliance analysis: 20,707

Saved: data/processed/mandi_msp_merged.csv (20,707 rows)

## 4. Headline finding
- Across all MSP-eligible transactions, 26.8% were recorded at a modal market price BELOW the government's Minimum Support Price for that commodity/year.