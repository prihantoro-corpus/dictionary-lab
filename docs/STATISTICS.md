# CORTEX Dictionary Lab - Statistical Methods

This document outlines the mathematical formulas and statistical approaches used in the application.

## 1. Frequency Metrics

### Raw Frequency
The simple count of how many times a token appears in the currently filtered corpus subset.
$$ f(w) = \text{count}(w) $$

### PMW (Per Million Words)
Normalized frequency to allow comparison across corpora of different sizes.
$$ PMW = \left( \frac{f(w)}{N} \right) \times 1,000,000 $$
Where $N$ is the total number of tokens in the active corpus.

### Zipf Bands
A simplified 1-5 scale to categorize frequency for users, based on PMW. This loosely follows Zipfian distribution buckets.
- **Band 1**: $PMW < 1$ (Very Rare)
- **Band 2**: $1 \le PMW < 10$ (Rare)
- **Band 3**: $10 \le PMW < 100$ (Common)
- **Band 4**: $100 \le PMW < 1000$ (Very Common)
- **Band 5**: $PMW \ge 1000$ (Core Vocabulary)

## 2. Collocation Statistics

### The Contingency Table
For a Node word ($n$) and a Collocate candidate ($c$), we construct a $2 \times 2$ table:

| | Collocate ($c$) | Not Collocate ($\neg c$) | Totals |
|---|---|---|---|
| **Node ($n$)** | $O_{11}$ | $O_{12}$ | $R_1$ (Freq of $n$) |
| **Not Node ($\neg n$)** | $O_{21}$ | $O_{22}$ | $R_2$ |
| **Totals** | $C_1$ (Freq of $c$) | $C_2$ | $N$ (Total Tokens in Filter) |

*Note on Collocate Filtering*: If a user specifies a "Collocate Filter" (whitelist), the Contingency Table ($O_{11}$ occurrence) and subsequent Log-Likelihood ($G^2$) scores are only computed where the candidate $c$ matches the whitelist. The Total Tokens $N$ reflects the total tokens of the currently filtered sub-corpus, not just the whitelisted tokens.

Where:
- $O_{11}$: Observed frequency of $n$ and $c$ appearing together within the window span (default $\pm 5$).

### Log-Likelihood ($G^2$)
We use the Dunning Log-Likelihood Ratio because it is more robust than Mutual Information (MI) for lower frequency counts.

**Formula**:
$$ G^2 = 2 \sum_{i,j} O_{ij} \ln \left( \frac{O_{ij}}{E_{ij}} \right) $$

**Expected Values ($E_{ij}$)**:
$$ E_{ij} = \frac{R_i \times C_j}{N} $$

The application calculates this directly in SQL to ensure performance over millions of rows.

## 3. N-Grams
N-grams are extracted using raw frequency counts of adjacent tokens.
- **Bigrams**: $P(w_n | w_{n-1})$ implies looking for the most frequent word following the node.
- **Trigrams**: Extended to windows of 3.

## 5. Vocabulary Profiling

### Coverage Percentage
Measures how much of the unique corpus vocabulary (lemmas) is present in a specific wordlist (e.g., NGSL, AWL).
$$ \text{Coverage \%} = \left( \frac{\text{Unique Lemmas in Wordlist}}{\text{Total Unique Lemmas in Corpus}} \right) \times 100 $$

### Category Distribution (Breakdown)
For wordlists with internal categories (like NGSL Ranks 1-3 or CEFR Levels A1-C2), the profiler calculates the percentage of the *entire* corpus that falls into each category.
$$ \text{Category \%} = \left( \frac{\text{Lemmas in Category } X}{\text{Total Unique Lemmas in Corpus}} \right) \times 100 $$

*Note*: The profiler operates on **lemmas** to ensure that inflected forms (e.g., "walking", "walked") are mapped to their root ("walk") before wordlist comparison.
