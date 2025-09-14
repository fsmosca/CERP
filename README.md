# CERP
CERP - Chess Engine Rating Predictor

The script main.py is created with the assistance of Gemini 2.5 and GPT 5.

# A. Setup

### 1. Install Python
### 2. Install requirements.txt

`pip install -r requirements.txt`

# B. Test the engine

`python main.py ./epd/sts_v8.1.epd -p "./engines/CDrill/cdrill_200.exe" -o Hash=128 -w 4 -mt 0.1`

* -w is the number of workers to use typically number of cores of your PC minus 1, if your PC has 4 cores you can use 3
* -mt is the movetime in seconds

### Change name

`-n "CDrill 2000 tuned"`

### Change engine options

`-o PawnStructureWeight=150 -o PSTWeight=80`

# C. Output

**Strength**

| Engine | TFile | ID | Description | Points | Total | Pct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CDrill 2000 | sts_v8.1.epd | STS(v6.0) | Recapturing | 6731 | 7600 | 88.57 |
| CDrill 2000 | sts_v8.1.epd | STS(v10.0) | Simplification | 6412 | 7600 | 84.37 |
| CDrill 2000 | sts_v8.1.epd | STS(v14.0) | 7th Rank | 5286 | 7000 | 75.51 |
| CDrill 2000 | sts_v8.1.epd | STS(v5.0) | Bishop vs Knight | 6126 | 8300 | 73.81 |
| CDrill 2000 | sts_v8.1.epd | STS(v13.0) | Pawn Play in the Center | 5123 | 7200 | 71.15 |

**Weakness**

| Engine | TFile | ID | Description | Points | Total | Pct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CDrill 2000 | sts_v8.1.epd | STS(v8.0) | Advancement of f/g/h pawns | 3629 | 7900 | 45.94 |
| CDrill 2000 | sts_v8.1.epd | STS(v9.0) | Advancement of a/b/c pawns | 3483 | 6900 | 50.48 |
| CDrill 2000 | sts_v8.1.epd | STS(v7.0) | Offer of Simplification | 3442 | 6700 | 51.37 |
| CDrill 2000 | sts_v8.1.epd | STS(v11.0) | King Activity | 3043 | 5800 | 52.47 |
| CDrill 2000 | sts_v8.1.epd | STS(v1.0) | Undermine | 4845 | 8400 | 57.68 |

**Summary**

| Engine | Id | Description | MTS | Points | Total | Pct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CDrill 2000 | STS(v1.0) | Undermine | 0.1 | 4845 | 8400 | 57.68 |
| CDrill 2000 | STS(v2.2) | Open Files and Diagonals | 0.1 | 5069 | 8700 | 58.26 |
| CDrill 2000 | STS(v3.0) | Knight Outposts/Centralization/Repositioning | 0.1 | 5710 | 8300 | 68.8 |
| CDrill 2000 | STS(v4.0) | Square Vacancy | 0.1 | 5053 | 8500 | 59.45 |
| CDrill 2000 | STS(v5.0) | Bishop vs Knight | 0.1 | 6126 | 8300 | 73.81 |
| CDrill 2000 | STS(v6.0) | Recapturing | 0.1 | 6731 | 7600 | 88.57 |
| CDrill 2000 | STS(v7.0) | Offer of Simplification | 0.1 | 3442 | 6700 | 51.37 |
| CDrill 2000 | STS(v8.0) | Advancement of f/g/h pawns | 0.1 | 3629 | 7900 | 45.94 |
| CDrill 2000 | STS(v9.0) | Advancement of a/b/c pawns | 0.1 | 3483 | 6900 | 50.48 |
| CDrill 2000 | STS(v10.0) | Simplification | 0.1 | 6412 | 7600 | 84.37 |
| CDrill 2000 | STS(v11.0) | King Activity | 0.1 | 3043 | 5800 | 52.47 |
| CDrill 2000 | STS(v12.0) | Center Control | 0.1 | 3968 | 6000 | 66.13 |
| CDrill 2000 | STS(v13.0) | Pawn Play in the Center | 0.1 | 5123 | 7200 | 71.15 |
| CDrill 2000 | STS(v14.0) | 7th Rank | 0.1 | 5286 | 7000 | 75.51 |
| CDrill 2000 | STS(v15.0) | Avoid Pointless Exchange | 0.1 | 5774 | 8200 | 70.41 |

**Points**

| Engine | TFile | MTS | Points | Total | Pct |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Stockfish 17.1 | sts_v8.1.epd | 0.1 | 106166 | 113100 | 93.87 |
| Deuterium v2019.2.37.73 | sts_v8.1.epd | 0.1 | 87183 | 113100 | 77.08 |
| CDrill 2000 | sts_v8.1.epd | 0.1 | 73694 | 113100 | 65.16 |

# D. Test suite

The epd file sts_v8.1.epd is based from the STS test suite by Dann Corbit and Swaminathan Natarajan. Here are the changes.

* Remove duplicates
* Remove positions that have more zero evaluation on most pv's
* Re-analyzed by Stockfish 15 and 16 with move re-scoring
* etc

# E. Rating calculation

To be updated ...


  


