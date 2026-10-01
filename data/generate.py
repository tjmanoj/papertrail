#!/usr/bin/env python3
"""
PaperTrail synthetic data generator.

Deterministic (fixed seed), stdlib + pandas + numpy only.
Produces referentially-consistent CSVs into data/out/.

Volumes (from task spec):
  ~800 counterparties, ~1600 accounts, ~250K transactions over 18 months,
  plus alerts, cases, watchlist entries, screening results, regulatory docs.

Plants ALL SIX typologies from data-model.md §4:
  1. Structuring / Smurfing
  2. Round-Tripping
  3. Dormant Account Reactivation
  4. Sanctions Near-Match
  5. Velocity Spike
  6. Mule Network

Also produces data/out/ground_truth.csv — the held-out answer key.
"""

import os
import sys
import hashlib
import datetime
import random
import math
import tempfile
import shutil
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

# ── CLI: --verify-determinism runs the generator twice and compares ──
if "--verify-determinism" in sys.argv:
    import subprocess
    script = str(Path(__file__).resolve())
    all_pass = True
    for run_label in ("run-1", "run-2"):
        tmpdir = tempfile.mkdtemp(prefix=f"papertrail_{run_label}_")
        print(f"[determinism] {run_label} -> {tmpdir}")
        r = subprocess.run(
            [sys.executable, script, f"--out-dir={tmpdir}"],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[determinism] {run_label} FAILED:\n{r.stderr}")
            sys.exit(1)
        if run_label == "run-1":
            dir1 = tmpdir
        else:
            dir2 = tmpdir

    files1 = sorted(os.listdir(dir1))
    files2 = sorted(os.listdir(dir2))
    if files1 != files2:
        print(f"[determinism] FAIL — file lists differ: {files1} vs {files2}")
        sys.exit(1)

    for fname in files1:
        h1 = hashlib.sha256(Path(dir1, fname).read_bytes()).hexdigest()
        h2 = hashlib.sha256(Path(dir2, fname).read_bytes()).hexdigest()
        status = "PASS" if h1 == h2 else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {fname:<45} {status}  {h1[:16]}...")

    shutil.rmtree(dir1)
    shutil.rmtree(dir2)
    if all_pass:
        print("[determinism] ALL FILES PASS — output is fully deterministic.")
        sys.exit(0)
    else:
        print("[determinism] FAIL — see above.")
        sys.exit(1)

# ── reproducibility ─────────────────────────────────────────
SEED = 20260701
random.seed(SEED)
np.random.seed(SEED)

# Allow --out-dir override for determinism testing
OUT = Path(__file__).resolve().parent / "out"
for arg in sys.argv[1:]:
    if arg.startswith("--out-dir="):
        OUT = Path(arg.split("=", 1)[1])
        break
OUT.mkdir(parents=True, exist_ok=True)

# ── time window ─────────────────────────────────────────────
START_DATE = datetime.date(2025, 4, 1)
END_DATE = datetime.date(2026, 9, 30)  # 18 months
DAYS = (END_DATE - START_DATE).days + 1

# ── helpers ─────────────────────────────────────────────────
_uid_counter = 0

def uid(prefix: str) -> str:
    global _uid_counter
    _uid_counter += 1
    h = hashlib.md5(f"papertrail-{SEED}-{prefix}-{_uid_counter}".encode()).hexdigest()[:12]
    return f"{prefix}-{h}"

def rand_date(lo: datetime.date, hi: datetime.date) -> datetime.date:
    delta = (hi - lo).days
    if delta <= 0:
        return lo
    return lo + datetime.timedelta(days=random.randint(0, delta))

def rand_ts(d: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(d, datetime.time(
        random.randint(6, 22), random.randint(0, 59), random.randint(0, 59)))

FIRST_NAMES = [
    "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Christopher","Karen","Charles","Lisa","Daniel","Nancy",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Steven","Ashley",
    "Andrew","Dorothy","Paul","Kimberly","Joshua","Emily","Kenneth","Donna",
    "Kevin","Michelle","Brian","Carol","George","Amanda","Timothy","Melissa",
    "Ronald","Deborah","Edward","Stephanie","Jason","Rebecca","Jeffrey","Sharon",
    "Ryan","Laura","Jacob","Cynthia","Gary","Kathleen","Nicholas","Amy",
    "Eric","Angela","Jonathan","Shirley","Stephen","Anna","Larry","Brenda",
    "Justin","Pamela","Scott","Emma","Brandon","Nicole","Benjamin","Helen",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
    "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker",
    "Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill",
    "Flores","Green","Adams","Nelson","Baker","Hall","Rivera","Campbell",
    "Mitchell","Carter","Roberts","Gomez","Phillips","Evans","Turner","Diaz",
    "Parker","Cruz","Edwards","Collins","Reyes","Stewart","Morris","Morales",
    "Murphy","Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper","Peterson",
    "Bailey","Reed","Kelly","Howard","Ramos","Kim","Cox","Ward",
]

CORP_NAMES = [
    "Apex Holdings","Meridian Capital","Atlas Resources","Pinnacle Industries",
    "Zenith Group","Horizon Partners","Summit Enterprises","Pacific Trading",
    "Eastern Commerce","Western Mining","Southern Agricultural","Northern Logistics",
    "Delta Financial","Omega Services","Sigma Construction","Theta Technologies",
    "Lambda Consulting","Kappa Manufacturing","Iota Energy","Epsilon Shipping",
    "Coral Bay Investments","Sandstone Properties","Ironbark Resources","Banksia Finance",
    "Wattle Creek Trading","Silver Fern Exports","Jade Mountain Holdings","Golden Gate Corp",
    "Tidal Wave Logistics","Stormfront Capital","Deep Blue Ventures","Red Earth Mining",
    "Green Valley Farms","Black Diamond Resources","White Swan Capital","Blue Harbour Trading",
    "Crystal Clear Finance","Iron Fortress Holdings","Bright Star Enterprises","Opal Ridge Corp",
]

BANK_NAMES = [
    "First National Correspondent Bank","Pacific Rim Banking Corp",
    "Southern Cross Bank","Asia Pacific Financial Institution",
    "Trans-Pacific Banking Group","Oceania Banking Alliance",
]

COUNTRIES_AU = ["AU"]
COUNTRIES_SG = ["SG"]
COUNTRIES_ALL = ["AU","SG","NZ","HK","GB","US","JP","MY","ID","TH","PH","CN","IN","DE","CH"]
HIGH_RISK_COUNTRIES = ["MM","KH","LA","AF","PK","NG","VU","WS"]

INDUSTRY_CODES = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S"]
WEALTH_SOURCES = ["Employment","Business Income","Inheritance","Investment Returns",
                  "Property Sale","Family Trust","Pension","Government Benefits"]
BRANCH_CODES_AU = ["SYD-CBD","SYD-NTH","MEL-CBD","MEL-STH","BNE-CBD","PER-CBD","ADL-CBD"]
BRANCH_CODES_SG = ["SG-CBD","SG-ORCHARD","SG-MARINA"]

# ── ground truth collector ──────────────────────────────────
ground_truth = []

def record_gt(typology: str, entity_ids: dict, window: str, expected_detection: str):
    ground_truth.append({
        "typology": typology,
        "counterparty_ids": "|".join(entity_ids.get("counterparty_ids", [])),
        "account_ids": "|".join(entity_ids.get("account_ids", [])),
        "transaction_ids": "|".join(entity_ids.get("transaction_ids", [])),
        "alert_ids": "|".join(entity_ids.get("alert_ids", [])),
        "window": window,
        "expected_detection": expected_detection,
    })

# ════════════════════════════════════════════════════════════
# 1. COUNTERPARTIES
# ════════════════════════════════════════════════════════════
print("Generating counterparties...")
counterparties = []

def make_individual(cid=None, jurisdiction=None, onboard_date=None, risk="LOW"):
    c = {
        "counterparty_id": cid or uid("CP"),
        "counterparty_type": "INDIVIDUAL",
        "full_legal_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "country_of_incorporation": None,
        "country_of_residence": jurisdiction or random.choice(["AU"]*7 + ["SG"]*2 + ["NZ"]),
        "date_of_birth": (datetime.date(1955,1,1) +
                          datetime.timedelta(days=random.randint(0, 365*40))).isoformat(),
        "industry_code": random.choice(INDUSTRY_CODES),
        "risk_rating": risk,
        "risk_rating_date": rand_ts(rand_date(START_DATE, END_DATE)).isoformat(),
        "kyc_refresh_due_date": rand_date(END_DATE,
                                          END_DATE + datetime.timedelta(days=365*3)).isoformat(),
        "onboarding_date": (onboard_date or rand_date(
            START_DATE - datetime.timedelta(days=365*5), END_DATE - datetime.timedelta(days=30)
        )).isoformat(),
        "pep_flag": random.random() < 0.02,
        "source_of_wealth": random.choice(WEALTH_SOURCES),
        "relationship_manager_id": f"RM-{random.randint(1,50):03d}",
        "jurisdiction": jurisdiction or random.choice(["AU"]*7 + ["SG"]*3),
    }
    if c["jurisdiction"] in (None,):
        c["jurisdiction"] = c["country_of_residence"]
    return c

def make_corporate(cid=None, name=None, jurisdiction=None, risk="MEDIUM"):
    j = jurisdiction or random.choice(["AU"]*7 + ["SG"]*3)
    return {
        "counterparty_id": cid or uid("CP"),
        "counterparty_type": "CORPORATE",
        "full_legal_name": name or random.choice(CORP_NAMES) + f" {random.choice(['Pty Ltd','Ltd','Corp','Inc'])}",
        "country_of_incorporation": j,
        "country_of_residence": None,
        "date_of_birth": None,
        "industry_code": random.choice(INDUSTRY_CODES),
        "risk_rating": risk,
        "risk_rating_date": rand_ts(rand_date(START_DATE, END_DATE)).isoformat(),
        "kyc_refresh_due_date": rand_date(END_DATE,
                                          END_DATE + datetime.timedelta(days=365*2)).isoformat(),
        "onboarding_date": rand_date(
            START_DATE - datetime.timedelta(days=365*8),
            END_DATE - datetime.timedelta(days=60)).isoformat(),
        "pep_flag": False,
        "source_of_wealth": "Business Income",
        "relationship_manager_id": f"RM-{random.randint(1,50):03d}",
        "jurisdiction": j,
    }

def make_bank(name=None, jurisdiction=None):
    j = jurisdiction or random.choice(["AU","SG","HK","JP"])
    return {
        "counterparty_id": uid("CP"),
        "counterparty_type": "CORRESPONDENT_BANK",
        "full_legal_name": name or random.choice(BANK_NAMES),
        "country_of_incorporation": j,
        "country_of_residence": None,
        "date_of_birth": None,
        "industry_code": "K",
        "risk_rating": "LOW",
        "risk_rating_date": rand_ts(rand_date(START_DATE, END_DATE)).isoformat(),
        "kyc_refresh_due_date": rand_date(END_DATE,
                                          END_DATE + datetime.timedelta(days=365)).isoformat(),
        "onboarding_date": rand_date(
            START_DATE - datetime.timedelta(days=365*10),
            START_DATE).isoformat(),
        "pep_flag": False,
        "source_of_wealth": None,
        "relationship_manager_id": f"RM-{random.randint(1,5):03d}",
        "jurisdiction": j if j in ("AU","SG") else "AU",
    }

# Normal counterparties
n_individuals = 520
n_corporates = 260
n_banks = 8

for _ in range(n_individuals):
    counterparties.append(make_individual(
        risk=np.random.choice(["LOW","MEDIUM","HIGH","VERY_HIGH"], p=[0.55,0.30,0.10,0.05])
    ))
for _ in range(n_corporates):
    counterparties.append(make_corporate(
        risk=np.random.choice(["LOW","MEDIUM","HIGH","VERY_HIGH"], p=[0.40,0.35,0.15,0.10])
    ))
for _ in range(n_banks):
    counterparties.append(make_bank())

# ── Typology-specific counterparties (reserved IDs) ────────

# T1: Structuring — 4 counterparties
structuring_cps = []
for i in range(4):
    cp = make_individual(cid=f"CP-STRUCT-{i:02d}",
                         jurisdiction="AU", risk="LOW")
    cp["full_legal_name"] = f"Structurer-{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    counterparties.append(cp)
    structuring_cps.append(cp["counterparty_id"])

# T2: Round-Tripping — 3 counterparties (corporates)
roundtrip_cps = []
for i in range(3):
    cp = make_corporate(cid=f"CP-ROUNDTRIP-{i:02d}",
                        name=f"Apex {'Holdings' if i==0 else 'Trading' if i==1 else 'Ventures'} Pty Ltd",
                        jurisdiction="AU", risk="MEDIUM")
    counterparties.append(cp)
    roundtrip_cps.append(cp["counterparty_id"])

# T3: Dormant Reactivation — 2 counterparties
dormant_cps = []
for i in range(2):
    cp = make_individual(cid=f"CP-DORMANT-{i:02d}",
                         jurisdiction="AU",
                         onboard_date=datetime.date(2022, 6, 1),
                         risk="LOW")
    counterparties.append(cp)
    dormant_cps.append(cp["counterparty_id"])

# T4: Sanctions Near-Match — 2 counterparties
sanctions_cps = []
cp_s0 = make_individual(cid="CP-SANCTIONS-00", jurisdiction="AU", risk="MEDIUM")
cp_s0["full_legal_name"] = "Aleksandr Petrov"
counterparties.append(cp_s0)
sanctions_cps.append(cp_s0["counterparty_id"])

cp_s1 = make_individual(cid="CP-SANCTIONS-01", jurisdiction="SG", risk="LOW")
cp_s1["full_legal_name"] = "Mohammad Al-Rashid"
counterparties.append(cp_s1)
sanctions_cps.append(cp_s1["counterparty_id"])

# T5: Velocity Spike — 3 counterparties
velocity_cps = []
for i in range(3):
    cp = make_individual(cid=f"CP-VELOCITY-{i:02d}",
                         jurisdiction="AU" if i < 2 else "SG",
                         risk="LOW")
    counterparties.append(cp)
    velocity_cps.append(cp["counterparty_id"])

# T6: Mule Network — 5 counterparties (individuals, recently onboarded, LOW risk)
mule_cps = []
for i in range(5):
    cp = make_individual(
        cid=f"CP-MULE-{i:02d}",
        jurisdiction="AU",
        onboard_date=rand_date(datetime.date(2026, 4, 1), datetime.date(2026, 6, 1)),
        risk="LOW"
    )
    counterparties.append(cp)
    mule_cps.append(cp["counterparty_id"])

# Dual-role counterparty: individual who is also a beneficial owner of a corporate
dual_role_individual = make_individual(cid="CP-DUAL-IND", jurisdiction="AU", risk="HIGH")
dual_role_individual["full_legal_name"] = "Marcus Wellington"
counterparties.append(dual_role_individual)

dual_role_corporate = make_corporate(cid="CP-DUAL-CORP",
                                     name="Wellington Capital Pty Ltd",
                                     jurisdiction="AU", risk="MEDIUM")
counterparties.append(dual_role_corporate)

# Pad to ~800
while len(counterparties) < 800:
    if random.random() < 0.65:
        counterparties.append(make_individual(
            risk=np.random.choice(["LOW","MEDIUM","HIGH","VERY_HIGH"], p=[0.55,0.30,0.10,0.05])))
    else:
        counterparties.append(make_corporate(
            risk=np.random.choice(["LOW","MEDIUM","HIGH","VERY_HIGH"], p=[0.40,0.35,0.15,0.10])))

cp_df = pd.DataFrame(counterparties)
cp_ids = cp_df["counterparty_id"].tolist()
cp_lookup = {r["counterparty_id"]: r for r in counterparties}

print(f"  Counterparties: {len(cp_df)}")

# ════════════════════════════════════════════════════════════
# 2. ACCOUNTS
# ════════════════════════════════════════════════════════════
print("Generating accounts...")
accounts = []
acct_by_cp = defaultdict(list)

ACCT_TYPES_IND = ["SAVINGS","CURRENT","TERM_DEPOSIT","LOAN"]
ACCT_TYPES_CORP = ["CURRENT","LOAN","TERM_DEPOSIT"]
ACCT_TYPES_BANK = ["NOSTRO","VOSTRO"]

def make_account(counterparty_id, acct_type=None, status="ACTIVE",
                 opened=None, aid=None):
    cp = cp_lookup[counterparty_id]
    j = cp["jurisdiction"]
    if acct_type is None:
        if cp["counterparty_type"] == "INDIVIDUAL":
            acct_type = random.choice(ACCT_TYPES_IND)
        elif cp["counterparty_type"] == "CORPORATE":
            acct_type = random.choice(ACCT_TYPES_CORP)
        else:
            acct_type = random.choice(ACCT_TYPES_BANK)

    od = opened or rand_date(
        datetime.date.fromisoformat(cp["onboarding_date"]),
        END_DATE - datetime.timedelta(days=30))

    a = {
        "account_id": aid or uid("AC"),
        "counterparty_id": counterparty_id,
        "account_type": acct_type,
        "currency_code": "USD",
        "opened_date": od.isoformat() if isinstance(od, datetime.date) else od,
        "closed_date": None,
        "status": status,
        "branch_code": random.choice(BRANCH_CODES_AU if j == "AU" else BRANCH_CODES_SG),
        "jurisdiction": j,
        "average_monthly_balance_usd": round(np.random.lognormal(mean=9, sigma=2), 2),
    }
    if status == "CLOSED":
        a["closed_date"] = rand_date(
            datetime.date.fromisoformat(a["opened_date"]) + datetime.timedelta(days=90),
            END_DATE).isoformat()
    return a

# Each counterparty gets 1-3 accounts
for cp in counterparties:
    cid = cp["counterparty_id"]
    n_accts = np.random.choice([1,2,3], p=[0.40,0.40,0.20])
    for _ in range(n_accts):
        a = make_account(cid)
        accounts.append(a)
        acct_by_cp[cid].append(a)

# Structuring counterparties need 2-3 accounts each
for cid in structuring_cps:
    while len(acct_by_cp[cid]) < 3:
        a = make_account(cid, acct_type="SAVINGS")
        accounts.append(a)
        acct_by_cp[cid].append(a)

# Dormant accounts — mark specific ones as DORMANT with old open dates
dormant_accts = []
for cid in dormant_cps:
    # ensure at least one dormant account
    a = make_account(cid, acct_type="CURRENT", status="DORMANT",
                     opened=datetime.date(2022, 7, 1),
                     aid=f"AC-DORMANT-{cid[-2:]}")
    a["average_monthly_balance_usd"] = round(random.uniform(100, 500), 2)
    accounts.append(a)
    acct_by_cp[cid].append(a)
    dormant_accts.append(a["account_id"])

# Mule accounts
mule_accts = []
for cid in mule_cps:
    a = make_account(cid, acct_type="SAVINGS",
                     opened=datetime.date(2026, 4, 15),
                     aid=f"AC-MULE-{cid[-2:]}")
    accounts.append(a)
    acct_by_cp[cid].append(a)
    mule_accts.append(a["account_id"])

# Velocity spike accounts
velocity_accts = []
for cid in velocity_cps:
    a = make_account(cid, acct_type="CURRENT",
                     aid=f"AC-VELOCITY-{cid[-2:]}")
    accounts.append(a)
    acct_by_cp[cid].append(a)
    velocity_accts.append(a["account_id"])

# Round-trip accounts
roundtrip_accts = []
for cid in roundtrip_cps:
    a = make_account(cid, acct_type="CURRENT",
                     aid=f"AC-ROUNDTRIP-{cid[-2:]}")
    accounts.append(a)
    acct_by_cp[cid].append(a)
    roundtrip_accts.append(a["account_id"])

# Dual-role: separate accounts for individual and corporate
dual_ind_acct = make_account("CP-DUAL-IND", acct_type="SAVINGS", aid="AC-DUAL-IND")
accounts.append(dual_ind_acct)
acct_by_cp["CP-DUAL-IND"].append(dual_ind_acct)

dual_corp_acct = make_account("CP-DUAL-CORP", acct_type="CURRENT", aid="AC-DUAL-CORP")
accounts.append(dual_corp_acct)
acct_by_cp["CP-DUAL-CORP"].append(dual_corp_acct)

acct_df = pd.DataFrame(accounts)
acct_ids = acct_df["account_id"].tolist()
acct_lookup = {a["account_id"]: a for a in accounts}

print(f"  Accounts: {len(acct_df)}")

# ════════════════════════════════════════════════════════════
# 3. TRANSACTIONS
# ════════════════════════════════════════════════════════════
print("Generating transactions (this may take a moment)...")
transactions = []
txn_id_counter = [0]

def make_txn(account_id, txn_type, amount, txn_date, tid=None,
             originator=None, orig_country=None,
             beneficiary=None, ben_country=None,
             channel=None, is_reversal=False, reversed_id=None,
             status="SETTLED", transfer_ref=None):
    txn_id_counter[0] += 1
    acct = acct_lookup[account_id]
    ts = rand_ts(txn_date)
    # value date can differ from booking; normally same day
    value_date = txn_date
    if random.random() < 0.03:  # 3% straddle booking vs value date
        value_date = txn_date + datetime.timedelta(days=random.choice([1,2]))
    # clamp: value_date must not precede account opening
    acct_opened = datetime.date.fromisoformat(acct["opened_date"])
    if value_date < acct_opened:
        value_date = acct_opened

    return {
        "transaction_id": tid or f"TX-{txn_id_counter[0]:08d}",
        "account_id": account_id,
        "transaction_date": value_date.isoformat(),
        "transaction_timestamp": ts.isoformat(),
        "transaction_type": txn_type,
        "amount_usd": round(amount, 2),
        "originator_name": originator,
        "originator_country": orig_country,
        "beneficiary_name": beneficiary,
        "beneficiary_country": ben_country,
        "transfer_reference": transfer_ref,
        "channel": channel or random.choice(["ONLINE","MOBILE","BRANCH","SWIFT"]),
        "is_reversal": is_reversal,
        "reversed_transaction_id": reversed_id,
        "status": status,
        "reporting_entity_jurisdiction": acct["jurisdiction"],
    }

# -- Normal background transactions --
TXN_TYPES_NORMAL = ["POS","ATM","WIRE_IN","WIRE_OUT","CASH_DEPOSIT",
                     "CASH_WITHDRAWAL","INTERNAL_TRANSFER","FEE"]
TXN_WEIGHTS = [0.30, 0.15, 0.10, 0.10, 0.08, 0.07, 0.15, 0.05]

normal_accts = [a for a in accounts
                if a["status"] in ("ACTIVE","DORMANT")
                and not a["account_id"].startswith("AC-DORMANT")]

# Generate ~240K normal transactions spread over 18 months
target_normal = 240000
txns_per_acct = max(1, target_normal // len(normal_accts))

for acct in normal_accts:
    aid = acct["account_id"]
    opened = datetime.date.fromisoformat(acct["opened_date"])
    acct_start = max(opened, START_DATE)
    if acct_start >= END_DATE:
        continue

    n = max(1, int(np.random.poisson(txns_per_acct)))
    for _ in range(n):
        d = rand_date(acct_start, END_DATE)
        tt = np.random.choice(TXN_TYPES_NORMAL, p=TXN_WEIGHTS)
        if tt in ("POS","ATM","FEE"):
            amt = abs(np.random.lognormal(mean=3.5, sigma=1.2))
        elif tt in ("CASH_DEPOSIT","CASH_WITHDRAWAL"):
            amt = abs(np.random.lognormal(mean=6.5, sigma=1.0))
        else:
            amt = abs(np.random.lognormal(mean=7.5, sigma=1.5))
        amt = min(amt, 2_000_000)

        orig = benef = orig_c = ben_c = None
        ch = random.choice(["ONLINE","MOBILE","BRANCH"])
        if tt == "WIRE_IN":
            orig = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            orig_c = random.choice(COUNTRIES_ALL)
            ch = "SWIFT"
        elif tt == "WIRE_OUT":
            benef = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            ben_c = random.choice(COUNTRIES_ALL)
            ch = "SWIFT"

        st = "SETTLED"
        if random.random() < 0.02:
            st = "PENDING"

        transactions.append(make_txn(
            aid, tt, amt, d, originator=orig, orig_country=orig_c,
            beneficiary=benef, ben_country=ben_c, channel=ch,
            status=st))

# Sprinkle reversals (~0.5% of transactions so far)
n_reversals = max(1, len(transactions) // 200)
rev_candidates = [t for t in transactions if t["status"] == "SETTLED" and not t["is_reversal"]]
for t in random.sample(rev_candidates, min(n_reversals, len(rev_candidates))):
    rev_date = datetime.date.fromisoformat(t["transaction_date"]) + datetime.timedelta(days=random.randint(1,5))
    if rev_date > END_DATE:
        continue
    rev = make_txn(
        t["account_id"], t["transaction_type"], t["amount_usd"], rev_date,
        originator=t["originator_name"], orig_country=t["originator_country"],
        beneficiary=t["beneficiary_name"], ben_country=t["beneficiary_country"],
        channel=t["channel"], is_reversal=True, reversed_id=t["transaction_id"],
        status="SETTLED")
    transactions.append(rev)
    # mark original as REVERSED
    t["status"] = "REVERSED"

# Month-boundary straddlers: some transactions booked on last day of month,
# value date = 1st of next month (already handled by 3% above, but force a few)
for _ in range(50):
    acct = random.choice(normal_accts)
    acct_opened = datetime.date.fromisoformat(acct["opened_date"])
    # pick a month-end
    m = random.randint(1, 17)
    base = START_DATE + datetime.timedelta(days=30*m)
    last_day = datetime.date(base.year, base.month, 1) - datetime.timedelta(days=1)
    if last_day < START_DATE or last_day > END_DATE or last_day < acct_opened:
        continue
    first_next = last_day + datetime.timedelta(days=1)
    if first_next > END_DATE:
        continue
    t = make_txn(acct["account_id"], "WIRE_IN",
                 abs(np.random.lognormal(7.5, 1.5)), last_day,
                 originator=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                 orig_country=random.choice(COUNTRIES_ALL), channel="SWIFT")
    # booking = last day, value = first of next month
    t["transaction_timestamp"] = rand_ts(last_day).isoformat()
    t["transaction_date"] = first_next.isoformat()
    transactions.append(t)

print(f"  Normal transactions so far: {len(transactions)}")

# ── T1: Structuring ─────────────────────────────────────────
print("  Planting T1: Structuring...")
structuring_txn_ids = []
for cid in structuring_cps:
    accts_for_cp = [a["account_id"] for a in acct_by_cp[cid]]
    # 3-6 deposits per rolling 7-day window, 3 windows
    for window_start_offset in [60, 120, 200]:
        window_start = START_DATE + datetime.timedelta(days=window_start_offset)
        n_deps = random.randint(3, 6)
        for j in range(n_deps):
            d = window_start + datetime.timedelta(days=random.randint(0, 6))
            if d > END_DATE:
                continue
            # amounts just below $10K
            if j == 0:
                amt = 9999.00  # the "slip-up"
            else:
                amt = round(random.uniform(8000, 9950), 2)
            aid = random.choice(accts_for_cp)
            t = make_txn(aid, "CASH_DEPOSIT", amt, d, channel="BRANCH")
            transactions.append(t)
            structuring_txn_ids.append(t["transaction_id"])

record_gt("STRUCTURING",
          {"counterparty_ids": structuring_cps,
           "account_ids": [a["account_id"] for c in structuring_cps for a in acct_by_cp[c]],
           "transaction_ids": structuring_txn_ids},
          f"{START_DATE} to {END_DATE}",
          "Multiple cash deposits clustered in $8K-$9.95K range across accounts")

# ── T2: Round-Tripping ─────────────────────────────────────
print("  Planting T2: Round-Tripping...")
roundtrip_txn_ids = []
for idx, cid in enumerate(roundtrip_cps):
    aid = roundtrip_accts[idx]
    cp_name = cp_lookup[cid]["full_legal_name"]
    # 3+ round-trip cycles
    for cycle in range(4):
        out_date = START_DATE + datetime.timedelta(days=90 + cycle*45 + random.randint(0,10))
        if out_date > END_DATE - datetime.timedelta(days=15):
            continue
        amt_out = round(random.uniform(50000, 200000), 2)
        amt_in = round(amt_out * random.uniform(0.98, 1.02), 2)
        in_date = out_date + datetime.timedelta(days=random.randint(5, 10))
        ref = f"RT-{uid('REF')}"

        # related name: shares a word with cp_name
        name_parts = cp_name.split()
        related_name = name_parts[0] + " " + random.choice(["Trading Ltd","Exports Corp","Logistics Pty Ltd"])

        t_out = make_txn(aid, "WIRE_OUT", amt_out, out_date,
                         beneficiary=related_name,
                         ben_country=random.choice(["HK","SG","NZ"]),
                         channel="SWIFT", transfer_ref=ref)
        t_in = make_txn(aid, "WIRE_IN", amt_in, in_date,
                        originator=related_name,
                        orig_country=random.choice(["HK","SG","NZ"]),
                        channel="SWIFT", transfer_ref=ref)
        transactions.extend([t_out, t_in])
        roundtrip_txn_ids.extend([t_out["transaction_id"], t_in["transaction_id"]])

record_gt("ROUND_TRIPPING",
          {"counterparty_ids": roundtrip_cps,
           "account_ids": roundtrip_accts,
           "transaction_ids": roundtrip_txn_ids},
          f"{START_DATE} to {END_DATE}",
          "Wire out followed by wire in of similar amount from related entity within 5-10 days")

# ── T3: Dormant Account Reactivation ───────────────────────
print("  Planting T3: Dormant Reactivation...")
dormant_txn_ids = []
for idx, aid in enumerate(dormant_accts):
    cid = dormant_cps[idx]
    # No transactions for 14+ months, then sudden burst
    burst_start = datetime.date(2026, 7, 1)
    # flip status to ACTIVE
    for a in accounts:
        if a["account_id"] == aid:
            a["status"] = "ACTIVE"
            break
    # 10+ transactions within 2 weeks, totalling > $50K
    for j in range(15):
        d = burst_start + datetime.timedelta(days=random.randint(0, 13))
        if d > END_DATE:
            continue
        tt = random.choice(["WIRE_IN","WIRE_OUT"])
        amt = round(random.uniform(3000, 12000), 2)
        orig = benef = orig_c = ben_c = None
        if tt == "WIRE_IN":
            orig = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            orig_c = random.choice(COUNTRIES_ALL)
        else:
            benef = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            ben_c = random.choice(COUNTRIES_ALL)
        t = make_txn(aid, tt, amt, d, originator=orig, orig_country=orig_c,
                     beneficiary=benef, ben_country=ben_c, channel="SWIFT")
        transactions.append(t)
        dormant_txn_ids.append(t["transaction_id"])

record_gt("DORMANT_REACTIVATION",
          {"counterparty_ids": dormant_cps,
           "account_ids": dormant_accts,
           "transaction_ids": dormant_txn_ids},
          "2026-07-01 to 2026-07-14",
          "Dormant 14+ months then burst of 10+ transactions totalling >$50K in 2 weeks")

# ── T4: Sanctions Near-Match ────────────────────────────────
# (Watchlist entries + screening results planted later)

# ── T5: Velocity Spike ──────────────────────────────────────
print("  Planting T5: Velocity Spike...")
velocity_txn_ids = []
for idx, cid in enumerate(velocity_cps):
    aid = velocity_accts[idx]
    # Stable baseline: 5-10 txns/month for 6+ months
    for month_offset in range(6):
        m_start = START_DATE + datetime.timedelta(days=30*month_offset)
        n_baseline = random.randint(5, 10)
        for _ in range(n_baseline):
            d = m_start + datetime.timedelta(days=random.randint(0, 29))
            if d > END_DATE:
                continue
            amt = abs(np.random.lognormal(6, 1))
            transactions.append(make_txn(aid, random.choice(["POS","ATM","WIRE_IN"]),
                                         amt, d))

    # Spike month: 40-80 transactions (layering pattern)
    spike_start = START_DATE + datetime.timedelta(days=210 + idx*30)
    n_spike = random.randint(40, 80)
    for j in range(n_spike):
        d = spike_start + datetime.timedelta(days=random.randint(0, 29))
        if d > END_DATE:
            continue
        # alternating wire in / wire out within 24-48h pairs
        if j % 2 == 0:
            amt = round(random.uniform(5000, 75000), 2)
            orig = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            t = make_txn(aid, "WIRE_IN", amt, d,
                         originator=orig,
                         orig_country=random.choice(COUNTRIES_ALL),
                         channel="SWIFT")
        else:
            amt = round(random.uniform(4500, 74000), 2)
            benef = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            t = make_txn(aid, "WIRE_OUT", amt, d,
                         beneficiary=benef,
                         ben_country=random.choice(COUNTRIES_ALL),
                         channel="SWIFT")
        transactions.append(t)
        velocity_txn_ids.append(t["transaction_id"])

record_gt("VELOCITY_SPIKE",
          {"counterparty_ids": velocity_cps,
           "account_ids": velocity_accts,
           "transaction_ids": velocity_txn_ids},
          "spike windows starting ~month 7-9",
          "5-10x spike in monthly transaction count with layering WIRE_IN/WIRE_OUT pattern")

# ── T6: Mule Network ───────────────────────────────────────
print("  Planting T6: Mule Network...")
mule_txn_ids = []
mule_originator = "GlobalTrade Finance Corp"
mule_beneficiary = "Eastbridge Consolidated Ltd"
mule_window_start = datetime.date(2026, 6, 10)

# Fan-out from originator → each mule
total_origin = round(random.uniform(200000, 350000), 2)
per_mule = total_origin / 5

for idx, aid in enumerate(mule_accts):
    in_date = mule_window_start + datetime.timedelta(days=random.randint(0, 2))
    in_amt = round(per_mule * random.uniform(0.9, 1.1), 2)
    t_in = make_txn(aid, "WIRE_IN", in_amt, in_date,
                    originator=mule_originator,
                    orig_country="HK", channel="SWIFT")
    transactions.append(t_in)
    mule_txn_ids.append(t_in["transaction_id"])

    # Forward to beneficiary within 48h, minus ~5% commission
    out_date = in_date + datetime.timedelta(days=random.randint(0, 1))
    out_amt = round(in_amt * 0.95, 2)
    t_out = make_txn(aid, "WIRE_OUT", out_amt, out_date,
                     beneficiary=mule_beneficiary,
                     ben_country="SG", channel="SWIFT")
    transactions.append(t_out)
    mule_txn_ids.append(t_out["transaction_id"])

record_gt("MULE_NETWORK",
          {"counterparty_ids": mule_cps,
           "account_ids": mule_accts,
           "transaction_ids": mule_txn_ids},
          "2026-06-10 to 2026-06-12",
          "5 unrelated individuals all receive from same originator and forward to same beneficiary within 48h")

# ── PENDING txns (additional edge cases) ────────────────────
# Some existing pending already; add a few more explicit ones
for _ in range(200):
    acct = random.choice(normal_accts)
    d = rand_date(END_DATE - datetime.timedelta(days=30), END_DATE)
    amt = abs(np.random.lognormal(7, 1.5))
    t = make_txn(acct["account_id"], "WIRE_IN", amt, d,
                 originator=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                 orig_country=random.choice(COUNTRIES_ALL),
                 channel="SWIFT", status="PENDING")
    transactions.append(t)

txn_df = pd.DataFrame(transactions)
print(f"  Total transactions: {len(txn_df)}")

# ════════════════════════════════════════════════════════════
# 4. ALERTS
# ════════════════════════════════════════════════════════════
print("Generating alerts...")
alerts = []
alert_transactions = []  # bridge rows

# Alerts for planted typologies
def make_alert(cid, typology, severity, status, alert_date, txn_ids, aid=None):
    rule_map = {
        "STRUCTURING": ("RULE-001", "Cash Deposit Threshold Proximity"),
        "ROUND_TRIPPING": ("RULE-002", "Circular Fund Flow Detection"),
        "DORMANT_REACTIVATION": ("RULE-003", "Dormant Account Sudden Activity"),
        "SANCTIONS_NEAR_MATCH": ("RULE-004", "Sanctions Screening Fuzzy Match"),
        "VELOCITY_SPIKE": ("RULE-005", "Transaction Velocity Anomaly"),
        "MULE_NETWORK": ("RULE-006", "Fan-Out/Fan-In Pattern Detection"),
    }
    rule_id, rule_name = rule_map.get(typology, ("RULE-999", "Unknown"))
    a_id = aid or uid("ALR")
    cp = cp_lookup[cid]
    a = {
        "alert_id": a_id,
        "counterparty_id": cid,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "alert_date": alert_date.isoformat(),
        "alert_timestamp": rand_ts(alert_date).isoformat(),
        "typology": typology,
        "severity": severity,
        "status": status,
        "assigned_analyst_id": f"ANALYST-{random.randint(1,10):03d}",
        "jurisdiction": cp["jurisdiction"],
        "narrative": f"Automated alert: {rule_name} triggered for {cp['full_legal_name']}",
    }
    alerts.append(a)
    for tid in txn_ids:
        alert_transactions.append({"alert_id": a_id, "transaction_id": tid})
    return a_id

# T1 alerts
struct_alert_ids = []
for cid in structuring_cps:
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in [a["account_id"] for a in acct_by_cp[cid]]
               and t["transaction_type"] == "CASH_DEPOSIT"
               and t["amount_usd"] >= 8000]
    aid = make_alert(cid, "STRUCTURING", "HIGH", "OPEN",
                     datetime.date(2025, 8, 1), cp_txns[:10])
    struct_alert_ids.append(aid)

# T2 alerts
rt_alert_ids = []
for cid in roundtrip_cps:
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in [a["account_id"] for a in acct_by_cp[cid]]
               and t["transaction_type"] in ("WIRE_IN","WIRE_OUT")]
    aid = make_alert(cid, "ROUND_TRIPPING", "HIGH", "ESCALATED",
                     datetime.date(2025, 11, 15), cp_txns[:8])
    rt_alert_ids.append(aid)

# T3 alerts
dormant_alert_ids = []
for cid in dormant_cps:
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in [a["account_id"] for a in acct_by_cp[cid]]]
    aid = make_alert(cid, "DORMANT_REACTIVATION", "MEDIUM", "OPEN",
                     datetime.date(2026, 7, 5), cp_txns[:15])
    dormant_alert_ids.append(aid)

# T4 alerts (sanctions)
sanctions_alert_ids = []
for cid in sanctions_cps:
    aid = make_alert(cid, "SANCTIONS_NEAR_MATCH", "CRITICAL", "OPEN",
                     datetime.date(2026, 2, 1), [])
    sanctions_alert_ids.append(aid)

record_gt("SANCTIONS_NEAR_MATCH",
          {"counterparty_ids": sanctions_cps,
           "alert_ids": sanctions_alert_ids},
          "2026-02-01 screening",
          "CP-SANCTIONS-00 (Aleksandr Petrov) true positive; CP-SANCTIONS-01 (Mohammad Al-Rashid) false positive")

# T5 alerts
vel_alert_ids = []
for cid in velocity_cps:
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in [a["account_id"] for a in acct_by_cp[cid]]
               and t["transaction_type"] in ("WIRE_IN","WIRE_OUT")]
    aid = make_alert(cid, "VELOCITY_SPIKE", "HIGH", "OPEN",
                     datetime.date(2025, 12, 1), cp_txns[:20])
    vel_alert_ids.append(aid)

# T6 alerts
mule_alert_ids = []
for cid in mule_cps:
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in [a["account_id"] for a in acct_by_cp[cid]]]
    aid = make_alert(cid, "MULE_NETWORK", "CRITICAL",
                     random.choice(["OPEN","ESCALATED"]),
                     datetime.date(2026, 6, 14), cp_txns)
    mule_alert_ids.append(aid)

# Update mule ground truth with alert IDs
for gt in ground_truth:
    if gt["typology"] == "MULE_NETWORK":
        gt["alert_ids"] = "|".join(mule_alert_ids)

# Background noise alerts (~200 more for realism)
typology_cp_ids = set(structuring_cps + roundtrip_cps + dormant_cps +
                      sanctions_cps + velocity_cps + mule_cps +
                      ["CP-DUAL-IND","CP-DUAL-CORP"])
noise_cp_pool = [c for c in cp_ids if c not in typology_cp_ids]
noise_cps_for_alerts = random.sample(noise_cp_pool, min(200, len(noise_cp_pool)))
for cid in noise_cps_for_alerts:
    cp_accts = [a["account_id"] for a in acct_by_cp.get(cid, [])]
    if not cp_accts:
        continue
    cp_txns = [t["transaction_id"] for t in transactions
               if t["account_id"] in cp_accts]
    sample_txns = random.sample(cp_txns, min(3, len(cp_txns))) if cp_txns else []
    typology = random.choice(["STRUCTURING","RAPID_MOVEMENT","VELOCITY_SPIKE"])
    severity = random.choice(["LOW","MEDIUM"])
    status = np.random.choice(
        ["OPEN","ESCALATED","CLOSED_NO_ACTION","CLOSED_SAR_FILED"],
        p=[0.20,0.10,0.55,0.15])
    d = rand_date(START_DATE, END_DATE)
    make_alert(cid, typology, severity, status, d, sample_txns)

alert_df = pd.DataFrame(alerts)
at_df = pd.DataFrame(alert_transactions)
print(f"  Alerts: {len(alert_df)}, Alert-Transaction links: {len(at_df)}")

# ════════════════════════════════════════════════════════════
# 5. CASES
# ════════════════════════════════════════════════════════════
print("Generating cases...")
cases = []
case_alerts = []

# Cases for planted typologies
def make_case(cid, alert_ids_list, opened, status, priority, closed=None):
    c_id = uid("CASE")
    cp = cp_lookup[cid]
    c = {
        "case_id": c_id,
        "counterparty_id": cid,
        "opened_date": opened.isoformat(),
        "closed_date": closed.isoformat() if closed else None,
        "status": status,
        "priority": priority,
        "assigned_analyst_id": f"ANALYST-{random.randint(1,10):03d}",
        "jurisdiction": cp["jurisdiction"],
        "resolution_narrative": None if status in ("OPEN","UNDER_REVIEW") else
            f"Investigation {'resulted in SAR filing' if status == 'SAR_FILED' else 'closed with no action'}.",
    }
    cases.append(c)
    for a_id in alert_ids_list:
        case_alerts.append({"case_id": c_id, "alert_id": a_id})
    return c_id

# T1 cases
for i, cid in enumerate(structuring_cps):
    make_case(cid, [struct_alert_ids[i]], datetime.date(2025, 8, 5),
              "UNDER_REVIEW", "URGENT")

# T2 cases
for i, cid in enumerate(roundtrip_cps):
    make_case(cid, [rt_alert_ids[i]], datetime.date(2025, 11, 20),
              "ESCALATED_TO_MLRO", "CRITICAL")

# T3 cases
for i, cid in enumerate(dormant_cps):
    make_case(cid, [dormant_alert_ids[i]], datetime.date(2026, 7, 8),
              "OPEN", "ROUTINE")

# T5 velocity cases
for i, cid in enumerate(velocity_cps):
    make_case(cid, [vel_alert_ids[i]], datetime.date(2025, 12, 5),
              "UNDER_REVIEW", "URGENT")

# T6 mule cases (single case covering all mule alerts)
mule_case_id = make_case(mule_cps[0], mule_alert_ids,
                         datetime.date(2026, 6, 16),
                         "ESCALATED_TO_MLRO", "CRITICAL")

# Background noise cases
noise_alerts = [a for a in alerts if a["alert_id"] not in
                struct_alert_ids + rt_alert_ids + dormant_alert_ids +
                sanctions_alert_ids + vel_alert_ids + mule_alert_ids]
# ~40% of noise alerts get a case
for a in random.sample(noise_alerts, min(len(noise_alerts), int(len(noise_alerts)*0.4))):
    status = np.random.choice(
        ["OPEN","UNDER_REVIEW","ESCALATED_TO_MLRO","SAR_FILED","CLOSED_NO_ACTION"],
        p=[0.15,0.15,0.05,0.10,0.55])
    opened = datetime.date.fromisoformat(a["alert_date"]) + datetime.timedelta(days=random.randint(1,5))
    closed = None
    if status in ("SAR_FILED","CLOSED_NO_ACTION"):
        closed = opened + datetime.timedelta(days=random.randint(5,90))
    make_case(a["counterparty_id"], [a["alert_id"]], opened,
              status, random.choice(["ROUTINE","URGENT","CRITICAL"]), closed)

case_df = pd.DataFrame(cases)
ca_df = pd.DataFrame(case_alerts)
print(f"  Cases: {len(case_df)}, Case-Alert links: {len(ca_df)}")

# ════════════════════════════════════════════════════════════
# 6. WATCHLIST ENTRIES
# ════════════════════════════════════════════════════════════
print("Generating watchlist entries...")
watchlist_entries = []

# Near-matches for T4
w0 = {
    "watchlist_entry_id": "WL-SANCTIONS-00",
    "list_source": "OFAC_SDN",
    "listed_name": "Aleksandr V. Petroff",  # near-match for "Aleksandr Petrov"
    "listed_name_normalised": "ALEKSANDR V PETROFF",
    "country": "RU",
    "listed_date": "2023-06-15",
    "delisted_date": None,
    "entity_type": "INDIVIDUAL",
    "identifying_information": "DOB: 1978-03-22; Passport: RU4451928",
}
watchlist_entries.append(w0)

w1 = {
    "watchlist_entry_id": "WL-SANCTIONS-01",
    "list_source": "UN_SANCTIONS",
    "listed_name": "Mohammed Al Rasheed",  # near-match for "Mohammad Al-Rashid"
    "listed_name_normalised": "MOHAMMED AL RASHEED",
    "country": "YE",
    "listed_date": "2022-01-10",
    "delisted_date": None,
    "entity_type": "INDIVIDUAL",
    "identifying_information": "DOB: 1985-11-03",
}
watchlist_entries.append(w1)

# Background watchlist entries
WL_SOURCES = ["OFAC_SDN","UN_SANCTIONS","EU_SANCTIONS","AUSTRAC_PRESCRIBED","PEP_LIST"]
WL_TYPES = ["INDIVIDUAL","ENTITY","VESSEL","AIRCRAFT"]
for i in range(80):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    watchlist_entries.append({
        "watchlist_entry_id": uid("WL"),
        "list_source": random.choice(WL_SOURCES),
        "listed_name": name,
        "listed_name_normalised": name.upper().replace("-","").replace("'",""),
        "country": random.choice(COUNTRIES_ALL + HIGH_RISK_COUNTRIES),
        "listed_date": rand_date(datetime.date(2018,1,1), END_DATE).isoformat(),
        "delisted_date": rand_date(datetime.date(2023,1,1), END_DATE).isoformat() if random.random() < 0.15 else None,
        "entity_type": np.random.choice(WL_TYPES, p=[0.60,0.30,0.05,0.05]),
        "identifying_information": f"DOB: {rand_date(datetime.date(1950,1,1), datetime.date(2000,1,1)).isoformat()}" if random.random() < 0.7 else None,
    })

wl_df = pd.DataFrame(watchlist_entries)
print(f"  Watchlist entries: {len(wl_df)}")

# ════════════════════════════════════════════════════════════
# 7. WATCHLIST SCREENING RESULTS
# ════════════════════════════════════════════════════════════
print("Generating screening results...")
screening_results = []

# T4 near-matches
screening_results.append({
    "screening_id": "SCR-SANCTIONS-00",
    "counterparty_id": "CP-SANCTIONS-00",
    "watchlist_entry_id": "WL-SANCTIONS-00",
    "screening_date": "2026-02-01T09:30:00",
    "match_score": 82.5,  # between 75-89 as specified
    "match_status": "PENDING_REVIEW",  # true positive that should be caught
    "reviewed_by": None,
})
screening_results.append({
    "screening_id": "SCR-SANCTIONS-01",
    "counterparty_id": "CP-SANCTIONS-01",
    "watchlist_entry_id": "WL-SANCTIONS-01",
    "screening_date": "2026-02-01T09:30:00",
    "match_score": 78.0,
    "match_status": "FALSE_POSITIVE",  # genuinely different person
    "reviewed_by": "ANALYST-003",
})

# Background screening: every counterparty gets screened at onboarding + periodic
for cp in counterparties:
    cid = cp["counterparty_id"]
    if cid in ("CP-SANCTIONS-00","CP-SANCTIONS-01"):
        continue
    # Onboarding screening
    screening_results.append({
        "screening_id": uid("SCR"),
        "counterparty_id": cid,
        "watchlist_entry_id": None,
        "screening_date": rand_ts(datetime.date.fromisoformat(cp["onboarding_date"])).isoformat(),
        "match_score": round(random.uniform(0, 30), 2),  # low = no match
        "match_status": "NO_MATCH",
        "reviewed_by": None,
    })
    # Periodic rescreening (~40% get a second screening)
    if random.random() < 0.4:
        screening_results.append({
            "screening_id": uid("SCR"),
            "counterparty_id": cid,
            "watchlist_entry_id": None,
            "screening_date": rand_ts(rand_date(START_DATE, END_DATE)).isoformat(),
            "match_score": round(random.uniform(0, 45), 2),
            "match_status": "NO_MATCH",
            "reviewed_by": None,
        })

scr_df = pd.DataFrame(screening_results)
print(f"  Screening results: {len(scr_df)}")

# ════════════════════════════════════════════════════════════
# 8. REGULATORY DOCUMENTS & CLAUSES
# ════════════════════════════════════════════════════════════
print("Generating regulatory documents...")

reg_docs = []
reg_clauses = []

DOCS = [
    {
        "document_id": "DOC-AML-POLICY",
        "document_type": "AML_POLICY",
        "title": "Anti-Money Laundering and Counter-Terrorism Financing Policy",
        "version": "v3.1",
        "effective_date": "2024-07-01",
        "jurisdiction": "AU",
        "clauses": [
            ("5.2", "Structuring Detection",
             "The bank shall maintain automated monitoring to detect transaction structuring, "
             "defined as patterns of cash deposits or withdrawals deliberately kept below the "
             "$10,000 AUD reporting threshold. Transactions between $8,000 and $9,999 occurring "
             "in clusters of 3 or more within any rolling 7-day period shall trigger a structuring "
             "alert for investigation. This is a prescribed typology under AUSTRAC AML/CTF Rules "
             "Chapter 36."),
            ("7.3", "Monitoring Effectiveness",
             "The effectiveness of transaction monitoring shall be measured quarterly using the "
             "alert closure rate metric: the percentage of alerts generated in the period that "
             "reach a terminal disposition (CLOSED_NO_ACTION or CLOSED_SAR_FILED) within the same "
             "period. A closure rate below 60% triggers a mandatory review of monitoring capacity "
             "and alert tuning. Auto-closed alerts below the investigation threshold are excluded "
             "from this metric to prevent artificial inflation."),
            ("7.5", "Investigation Timeliness",
             "All investigation cases must reach a terminal status within 90 calendar days of "
             "opening. Cases exceeding 90 days without resolution must be escalated to the MLRO "
             "with a written justification for delay. The days_to_case_resolution metric measures "
             "calendar days between case opening and terminal status (SAR_FILED or CLOSED_NO_ACTION). "
             "Business days are not used to avoid inconsistency across jurisdictions with different "
             "holiday calendars."),
            ("8.1", "Velocity Monitoring",
             "Accounts exhibiting transaction counts exceeding 5 times their trailing 6-month "
             "monthly average within any single calendar month shall generate a velocity spike "
             "alert. The monitoring system must distinguish between legitimate seasonal increases "
             "(e.g., payroll periods) and anomalous spikes indicative of layering or account "
             "takeover."),
            ("9.1", "Mule Account Detection",
             "The bank shall monitor for money mule patterns: multiple apparently unrelated "
             "accounts receiving funds from the same originator and forwarding to the same "
             "beneficiary within a short timeframe (72 hours). Funds retention of less than 10% "
             "between receipt and forwarding is a strong indicator of mule activity."),
        ],
    },
    {
        "document_id": "DOC-SANCTIONS-PROC",
        "document_type": "SANCTIONS_PROCEDURE",
        "title": "Sanctions Screening Operational Procedure",
        "version": "v2.0",
        "effective_date": "2024-03-15",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Screening Frequency",
             "All counterparties must be screened against consolidated sanctions lists at "
             "onboarding and at each KYC refresh cycle. Batch rescreening of the entire "
             "customer base must occur within 48 hours of any sanctions list update from "
             "OFAC, UN, EU, or AUSTRAC."),
            ("3.2", "Match Threshold Management",
             "Fuzzy matching scores above 90 are auto-escalated as potential true matches. "
             "Scores between 60 and 89 require manual review by a qualified analyst. Scores "
             "below 60 are auto-dismissed. The bank maintains a near-match watch zone between "
             "75 and 89 where enhanced scrutiny is applied — these are the cases most likely "
             "to represent evasion through spelling variation, transliteration differences, or "
             "deliberate name modification."),
            ("4.1", "Escalation Path",
             "Confirmed matches must be reported to AUSTRAC within 24 hours. Pending reviews "
             "must be adjudicated within 5 business days. False positives must be documented "
             "with the rationale for dismissal and the reviewer's identity."),
        ],
    },
    {
        "document_id": "DOC-STR-GUIDANCE",
        "document_type": "STR_GUIDANCE",
        "title": "Suspicious Transaction Report Filing Guidance",
        "version": "v2.5",
        "effective_date": "2024-01-01",
        "jurisdiction": "AU",
        "clauses": [
            ("3.1", "Filing Thresholds",
             "A Suspicious Transaction Report must be filed with AUSTRAC within 72 hours of "
             "forming a suspicion. The total_suspicious_transaction_volume_usd metric — defined "
             "as the sum of settled, non-reversed transactions linked to open or escalated alerts "
             "— provides the quantitative basis for threshold reporting. Pending transactions are "
             "excluded until settlement. Reversed transactions are excluded to prevent double-counting."),
            ("4.1", "Filing Rate Expectations",
             "The sar_filing_rate metric measures the percentage of opened investigation cases "
             "that result in a SAR filing. The denominator includes all cases opened in the "
             "measurement period regardless of current status. A rate below 5% may indicate "
             "insufficient investigation rigour; a rate above 40% may indicate over-reporting "
             "or inadequate initial alert triage. Both extremes trigger regulatory review."),
            ("5.1", "Narrative Requirements",
             "Each SAR narrative must include: (a) the specific transactions that triggered "
             "suspicion with dates, amounts, and counterparties; (b) the typology or pattern "
             "identified; (c) the analyst's assessment of why the activity is suspicious; "
             "(d) any mitigating factors considered and rejected. All figures cited must be "
             "traceable to the governed metrics system."),
        ],
    },
    {
        "document_id": "DOC-KYC-POLICY",
        "document_type": "KYC_POLICY",
        "title": "Know Your Customer Refresh Policy",
        "version": "v1.8",
        "effective_date": "2024-06-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Risk-Based Refresh Cycles",
             "KYC reviews must be conducted on a risk-based schedule: HIGH and VERY_HIGH risk "
             "counterparties require annual review; MEDIUM risk requires biennial review; LOW "
             "risk requires triennial review. The high_risk_counterparty_count metric — the count "
             "of counterparties currently rated HIGH or VERY_HIGH — drives resource planning for "
             "annual review cycles. Only counterparties with at least one active account are "
             "included; exited relationships are excluded."),
            ("3.1", "Trigger-Based Refresh",
             "A KYC refresh must be triggered outside the regular cycle when: (a) a HIGH or "
             "CRITICAL severity alert is generated; (b) adverse media screening returns a hit; "
             "(c) the counterparty requests a material change to their account structure; "
             "(d) a sanctions screening result moves from NO_MATCH to PENDING_REVIEW or above."),
            ("4.1", "KYC Documentation Completeness",
             "A KYC file is considered complete only when it contains: certified identity "
             "documents, proof of address dated within 3 months, source-of-funds declaration, "
             "risk assessment form signed by the reviewing officer, and screening results "
             "(sanctions, PEP, adverse media). Incomplete files must be escalated to the "
             "KYC Quality team within 10 business days of identification. Accounts with "
             "incomplete KYC files for more than 30 calendar days must be restricted."),
            ("4.3", "Dormancy and KYC Refresh Interaction",
             "A KYC refresh is not required during the dormancy period if no customer-initiated "
             "activity occurs. However, upon reactivation of a dormant account, a full KYC "
             "refresh must be completed before unrestricted transaction processing resumes, "
             "regardless of when the last scheduled refresh occurred. This applies to all risk "
             "tiers and is additional to the dormancy reactivation alert requirement."),
        ],
    },
    {
        "document_id": "DOC-RISK-APPETITE",
        "document_type": "RISK_APPETITE_STATEMENT",
        "title": "Board Risk Appetite Statement — AML/Sanctions/Fraud",
        "version": "v4.0",
        "effective_date": "2024-09-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.4", "Concentration Limits",
             "No single counterparty's net exposure (counterparty_exposure_usd) shall exceed "
             "5% of the bank's total customer deposit base. The metric sums average_monthly_balance_usd "
             "across all ACTIVE accounts for a given counterparty. Dormant accounts are excluded; "
             "LOAN accounts are excluded from the concentration numerator (they represent the "
             "bank's exposure to the counterparty, not the counterparty's deposits). Breaches "
             "require immediate board notification."),
            ("3.1", "Alert Ageing Tolerance",
             "No more than 10% of open alerts shall be older than 30 calendar days without "
             "analyst assignment. The alert ageing metric is monitored weekly and reported to "
             "the Chief Compliance Officer."),
            ("5.1", "Round-Tripping Detection",
             "The bank has zero tolerance for round-tripping — funds that leave an account and "
             "return within 10 business days from a related entity. The monitoring system must "
             "flag wire transfers where the outbound beneficiary name shares significant tokens "
             "with the inbound originator name and the amounts match within 5%. All round-trip "
             "alerts are classified as HIGH severity minimum."),
        ],
    },
    {
        "document_id": "DOC-CORRESPONDENT",
        "document_type": "LIQUIDITY_GUIDANCE",
        "title": "Correspondent Banking Due Diligence Guidance",
        "version": "v1.2",
        "effective_date": "2024-04-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Downstream Correspondent Restrictions",
             "The bank shall not maintain correspondent relationships with institutions that "
             "permit payable-through accounts or nested correspondent arrangements without "
             "prior board approval. Nostro/vostro account activity must be monitored for "
             "unusual patterns including dormant-then-active cycles and velocity spikes."),
            ("3.1", "Dormant Account Reactivation",
             "Any account — retail or correspondent — that has been dormant (no customer-initiated "
             "transactions) for 12 or more months and then receives a transaction must generate "
             "a dormant reactivation alert. The account must be reviewed before further transactions "
             "are permitted. Transactions totalling over $50,000 within 14 days of reactivation "
             "require immediate MLRO notification."),
        ],
    },
    # ── NEW DOCUMENTS (Phase 5a expansion) ───────────────────
    {
        "document_id": "DOC-TXN-MONITORING",
        "document_type": "TXN_MONITORING_STANDARD",
        "title": "Transaction Monitoring Program Standards",
        "version": "v2.3",
        "effective_date": "2024-08-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Scope of Monitoring",
             "All customer-initiated transactions across deposit, lending, and correspondent "
             "channels shall be subject to automated monitoring. Internal book transfers, "
             "interest accruals, and fee postings are excluded from typology-based monitoring "
             "but remain subject to aggregate volume controls. The monitoring universe must be "
             "reconciled monthly against the general ledger to confirm completeness."),
            ("2.3", "Threshold Calibration",
             "Monetary thresholds used in monitoring rules must be reviewed semi-annually and "
             "recalibrated against transaction volume distributions. The $10,000 AUD reporting "
             "threshold is statutory and must not be adjusted. Internal thresholds (e.g., "
             "velocity multiples, dormancy windows) may be tightened but must not be relaxed "
             "below the levels specified in the AML Policy without MLRO sign-off."),
            ("3.1", "Real-Time vs Batch Monitoring",
             "Wire transfers exceeding $25,000 AUD must be screened in real time before release. "
             "All other transaction types may be monitored in batch with a maximum processing "
             "delay of 4 hours from settlement. Batch monitoring jobs that fail to complete "
             "within the 4-hour window must generate an operational alert to the compliance "
             "technology team."),
            ("3.4", "Cross-Channel Aggregation",
             "The monitoring system must aggregate transaction values across all accounts held "
             "by the same counterparty when evaluating thresholds. A counterparty depositing "
             "$4,500 into each of three accounts in the same day must trigger the same "
             "structuring evaluation as a single $13,500 deposit. The counterparty_exposure_usd "
             "metric provides the aggregation baseline for concentration monitoring."),
            ("4.1", "Alert Generation Standards",
             "Each generated alert must capture: the rule that fired, the triggering transactions "
             "with amounts and dates, the counterparty identifier, the risk rating at the time "
             "of trigger, and a machine-generated narrative summarising the suspicious pattern. "
             "Alerts must be assigned a severity (LOW, MEDIUM, HIGH, CRITICAL) based on the "
             "rule configuration and the counterparty's current risk rating."),
            ("4.3", "Alert Deduplication",
             "When multiple rules fire on overlapping transactions for the same counterparty "
             "within a 48-hour window, the system shall consolidate into a single alert at "
             "the highest applicable severity. Deduplication must not suppress alerts of "
             "different typology categories: a structuring alert and a velocity alert on the "
             "same counterparty must remain separate even if transactions overlap."),
            ("5.1", "Dormancy Monitoring Intervals",
             "Dormancy monitoring operates on two distinct intervals. Accounts with no "
             "customer-initiated activity for 6 months are classified as INACTIVE and subject "
             "to reduced monitoring. Accounts inactive for 12 or more months are classified as "
             "DORMANT and any subsequent activity triggers a reactivation alert per the "
             "Correspondent Banking guidance §3.1. INACTIVE accounts receiving high-value "
             "transactions (above $20,000) must also trigger an alert even before reaching "
             "DORMANT status."),
            ("5.4", "Velocity Spike Calibration",
             "The velocity monitoring rule compares the current month's transaction count to the "
             "trailing 6-month average. The default multiplier is 5x. For BUSINESS-type accounts "
             "with established seasonal patterns (documented during onboarding or KYC review), "
             "the multiplier may be raised to 8x with documented justification. The multiplier "
             "must never exceed 10x regardless of account type."),
            ("6.1", "Model Validation Frequency",
             "All statistical models and rule-based scenarios used in transaction monitoring "
             "must be independently validated at least annually. Validation must include "
             "above-the-line testing (does the model detect known typologies?) and below-the-line "
             "testing (does the model generate excessive false positives?). The alert closure "
             "rate metric from AML Policy §7.3 serves as the primary efficiency indicator."),
            ("7.1", "Reporting to Board",
             "The Head of Financial Crime must present a quarterly transaction monitoring report "
             "to the Board Risk Committee covering: total alerts generated by typology, "
             "alert closure rate, average days_to_case_resolution, SAR filing rate, and any "
             "material changes to monitoring scenarios. Significant deterioration in any metric "
             "must be reported within 5 business days of detection, not deferred to the "
             "quarterly cycle."),
            ("7.4", "Regulatory Reporting Deadlines",
             "Threshold transaction reports (TTRs) for cash transactions at or above $10,000 AUD "
             "must be submitted to AUSTRAC within 10 business days of the transaction. International "
             "funds transfer instructions (IFTIs) must be reported within 10 business days. These "
             "deadlines are distinct from the 72-hour STR filing deadline and the 24-hour sanctions "
             "reporting obligation. Failure to meet any reporting deadline must be logged as a "
             "compliance breach."),
            ("8.1", "Structuring Pattern Variants",
             "In addition to the standard structuring pattern (multiple transactions below $10,000), "
             "the monitoring system must detect: (a) round-number structuring — deposits consistently "
             "at $9,000 or $9,500; (b) sequential structuring — deposits at increasing amounts across "
             "consecutive days; (c) smurfing — multiple individuals depositing to the same account on "
             "the same day. Each variant triggers the same structuring alert but is tagged with the "
             "specific sub-pattern for investigation guidance."),
        ],
    },
    {
        "document_id": "DOC-PEP-HANDLING",
        "document_type": "PEP_PROCEDURE",
        "title": "Politically Exposed Persons Handling Procedure",
        "version": "v1.5",
        "effective_date": "2024-05-15",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "PEP Identification",
             "All counterparties must be screened against PEP databases at onboarding and at "
             "each KYC refresh. PEP status extends to immediate family members and known close "
             "associates. The screening must cover domestic PEPs (Australian government officials "
             "at federal and state level), foreign PEPs, and international organisation PEPs. "
             "PEP screening must not be limited to sanctions list matching; dedicated PEP "
             "databases must be maintained separately."),
            ("2.4", "PEP Risk Classification",
             "All identified PEPs must be classified as HIGH risk minimum, regardless of the "
             "standard risk assessment outcome. Foreign PEPs from jurisdictions rated HIGH or "
             "VERY_HIGH on the FATF mutual evaluation must be classified VERY_HIGH. The "
             "high_risk_counterparty_count metric includes PEP-classified counterparties. "
             "A counterparty's PEP status may only be downgraded after a 24-month cooling-off "
             "period following departure from the public role."),
            ("3.1", "Enhanced Monitoring for PEPs",
             "PEP accounts are subject to enhanced transaction monitoring with reduced thresholds: "
             "the structuring detection window is lowered from $8,000–$9,999 to $5,000–$9,999, "
             "and the velocity multiplier is reduced from 5x to 3x. All wire transfers by PEP "
             "counterparties exceeding $15,000 require pre-release review by a senior analyst. "
             "These thresholds apply to aggregate activity across all accounts held by the PEP."),
            ("3.4", "PEP Transaction Reporting",
             "Transactions by PEP counterparties exceeding $50,000 in aggregate within any "
             "calendar month must be reported to the MLRO within 3 business days of month-end, "
             "regardless of whether an alert was triggered. This reporting obligation is "
             "independent of the STR filing requirements and serves as an additional oversight "
             "layer for high-profile relationships."),
            ("4.1", "Senior Management Approval",
             "Onboarding a new PEP relationship requires written approval from the Chief "
             "Compliance Officer or their delegate. The approval must document: the source of "
             "the PEP's wealth, the expected transaction profile, the business rationale for "
             "the relationship, and any jurisdictional risk factors. Approval must be renewed "
             "annually as part of the KYC refresh cycle."),
            ("5.1", "PEP Exit Criteria",
             "A PEP relationship must be exited if: (a) two or more SARs have been filed in "
             "any 12-month period; (b) the counterparty refuses to provide source-of-wealth "
             "documentation requested during KYC refresh; (c) the counterparty's jurisdiction "
             "is added to a sanctions or embargo list. Exit must be completed within 90 calendar "
             "days and all open alerts must be resolved before account closure."),
            ("6.1", "PEP Dormancy Rules",
             "PEP accounts that become dormant are subject to stricter controls than standard "
             "dormant accounts. The dormancy classification period for PEP accounts is reduced "
             "from 12 months to 6 months of inactivity. Any reactivation of a dormant PEP "
             "account must be approved by a senior compliance officer before the first transaction "
             "is processed, regardless of transaction amount. This is stricter than the general "
             "dormant reactivation requirements in the Correspondent Banking guidance §3.1."),
            ("6.4", "PEP Alert Handling Priority",
             "All alerts generated on PEP counterparties must be classified as URGENT minimum "
             "priority, regardless of the alert severity assigned by the monitoring system. PEP "
             "alerts must be triaged within 4 hours rather than the standard 24-hour triage window. "
             "The alert ageing tolerance for PEP alerts is 15 calendar days, half the standard "
             "30-day tolerance defined in the Risk Appetite Statement §3.1."),
        ],
    },
    {
        "document_id": "DOC-EDD-STANDARD",
        "document_type": "EDD_STANDARD",
        "title": "Enhanced Due Diligence Standard",
        "version": "v2.0",
        "effective_date": "2024-10-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "EDD Trigger Events",
             "Enhanced due diligence must be initiated when: (a) the counterparty is rated HIGH "
             "or VERY_HIGH risk; (b) the counterparty operates in or remits funds to FATF "
             "grey-listed or black-listed jurisdictions; (c) two or more alerts of HIGH or "
             "CRITICAL severity are raised within any rolling 6-month period; (d) the total "
             "suspicious transaction volume for the counterparty exceeds $100,000 AUD. The "
             "total_suspicious_transaction_volume_usd metric is the reference measure for "
             "trigger (d)."),
            ("2.4", "EDD Documentation Requirements",
             "EDD files must contain at minimum: certified identity documents, verified "
             "source-of-funds evidence, business structure diagrams for corporate entities, "
             "beneficial ownership declarations to the 25% threshold, and a risk narrative "
             "prepared by a qualified analyst. Incomplete EDD files must generate a compliance "
             "exception that is tracked to resolution within 30 calendar days."),
            ("3.1", "Ongoing EDD Monitoring",
             "Counterparties under EDD are subject to monthly transaction reviews rather than "
             "the standard automated-only monitoring. The review must compare actual transaction "
             "patterns against the expected profile documented at onboarding. Deviations "
             "exceeding 50% of the expected monthly volume or 3x the expected transaction "
             "count must be escalated as a potential material change requiring KYC refresh "
             "per KYC Policy §3.1."),
            ("3.3", "EDD for Dormant High-Risk Accounts",
             "HIGH or VERY_HIGH risk accounts that become dormant require EDD review before "
             "reactivation, in addition to the standard dormant reactivation alert. The EDD "
             "review must confirm that the counterparty's risk profile has not materially "
             "changed during the dormancy period and must be completed within 5 business days "
             "of the reactivation request. Transactions must not be processed until the EDD "
             "review is complete."),
            ("4.1", "Jurisdictional Risk Assessment",
             "The bank maintains a tiered jurisdictional risk model: Tier 1 (LOW) — FATF "
             "members with satisfactory mutual evaluations; Tier 2 (MEDIUM) — non-FATF members "
             "with cooperative information-sharing agreements; Tier 3 (HIGH) — FATF grey-listed "
             "jurisdictions; Tier 4 (VERY_HIGH) — FATF black-listed or sanctioned jurisdictions. "
             "All transactions involving Tier 3 or Tier 4 jurisdictions must be pre-screened "
             "regardless of amount."),
            ("4.4", "Concentration Risk in High-Risk Jurisdictions",
             "Aggregate exposure to counterparties domiciled in Tier 3 or Tier 4 jurisdictions "
             "must not exceed 2% of total customer deposits. This is stricter than the general "
             "5% per-counterparty concentration limit in the Risk Appetite Statement §2.4 and "
             "is measured as a portfolio-level control. Breaches must be reported to the Board "
             "within 24 hours."),
            ("5.1", "EDD Review Cycle",
             "EDD counterparties must be reviewed every 6 months, rather than the standard "
             "annual KYC cycle for HIGH risk. The review must be documented and signed off by "
             "a senior compliance officer. If two consecutive EDD reviews identify no concerns, "
             "the counterparty may be proposed for standard HIGH-risk monitoring, subject to "
             "MLRO approval."),
            ("6.1", "Third-Party Reliance Restrictions",
             "The bank may not rely on third-party due diligence for counterparties requiring "
             "EDD. All identity verification, source-of-funds checks, and beneficial ownership "
             "investigations must be conducted directly by the bank's compliance team. "
             "Third-party screening results (sanctions, PEP, adverse media) may be used as "
             "inputs but do not satisfy the EDD documentation requirements independently."),
            ("7.1", "Threshold Amounts for EDD Escalation",
             "Single transactions exceeding $75,000 AUD by EDD-subject counterparties must be "
             "pre-approved by a senior compliance officer before processing. Aggregate weekly "
             "transactions exceeding $150,000 AUD must trigger an immediate EDD progress review. "
             "These thresholds are independent of the general $25,000 real-time screening "
             "threshold in the Transaction Monitoring Standards and the $50,000 dormancy "
             "reactivation threshold in the Correspondent Banking guidance."),
            ("7.4", "EDD Counterparty Reporting",
             "A monthly EDD portfolio report must be submitted to the MLRO within 5 business "
             "days of month-end. The report must include: total EDD counterparties by risk tier, "
             "new EDD initiations, completed reviews, overdue reviews, and the aggregate "
             "counterparty_exposure_usd for the EDD portfolio. This reporting obligation is "
             "separate from the quarterly board report under Transaction Monitoring Standards §7.1 "
             "and the PEP transaction reporting under PEP Handling §3.4."),
        ],
    },
    {
        "document_id": "DOC-RECORD-RETENTION",
        "document_type": "RECORD_RETENTION_POLICY",
        "title": "Record-Keeping and Retention Policy — Financial Crime",
        "version": "v3.0",
        "effective_date": "2024-02-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Statutory Retention Periods",
             "All transaction records must be retained for a minimum of 7 years from the date "
             "of the transaction, as required by the AML/CTF Act 2006 Part 12. KYC and CDD "
             "records must be retained for 7 years after the termination of the business "
             "relationship. Records related to SAR filings must be retained for 10 years from "
             "the date of filing."),
            ("2.3", "Alert and Investigation Records",
             "All alert records, including the triggering rule, transaction details, analyst "
             "notes, and disposition, must be retained for the greater of: (a) 7 years from "
             "alert generation; or (b) 3 years after the closure of any associated investigation "
             "case. The days_to_case_resolution metric and all supporting evidence must be "
             "preserved as part of the investigation record."),
            ("3.1", "Retrieval Standards",
             "Records must be retrievable within 3 business days of a regulatory request. "
             "AUSTRAC compliance examinations typically require production within 24 hours for "
             "urgent matters. The bank must maintain indexing that supports retrieval by "
             "counterparty, account, transaction date range, alert identifier, and case "
             "identifier. Full-text search capability over investigation narratives is "
             "recommended but not mandatory."),
            ("3.4", "Data Integrity Controls",
             "Retained records must be protected against unauthorised modification. All "
             "amendments to investigation records must be tracked with a full audit trail "
             "showing the original value, the modified value, the identity of the modifier, "
             "and the timestamp and reason for modification. Deletion of records within the "
             "retention period is prohibited except by court order."),
            ("4.1", "Reporting Deadline Records",
             "The bank must maintain a log of all regulatory reporting deadlines and actual "
             "submission timestamps. For STR filings, the 72-hour deadline from suspicion "
             "formation must be documented with the exact time suspicion was formed, the "
             "time the STR was submitted to AUSTRAC, and any justification for delay. For "
             "sanctions matches, the 24-hour reporting deadline to AUSTRAC must be similarly "
             "documented."),
            ("5.1", "Disposal Procedures",
             "Records that have exceeded their mandatory retention period may be disposed of "
             "only after confirmation that: (a) no open investigation references the record; "
             "(b) no pending or anticipated regulatory examination requires the record; "
             "(c) disposal is approved by the Records Management Officer. Disposal must be "
             "documented in the retention schedule log and is irreversible."),
            ("5.4", "Cross-Border Record Obligations",
             "When transactions involve counterparties in multiple jurisdictions, the longer "
             "retention period applies. Records relating to correspondent banking relationships "
             "must follow the retention requirements of both the home jurisdiction and the "
             "correspondent's jurisdiction. EU GDPR right-to-erasure requests do not override "
             "AML/CTF retention obligations."),
            ("6.1", "Dormant Account Records",
             "Records for dormant accounts must be retained for the full statutory period from "
             "the date of the last customer-initiated transaction, not from the date the account "
             "was classified as dormant. If a dormant account is reactivated, the retention clock "
             "resets to the date of the most recent transaction after reactivation. This ensures "
             "that dormancy patterns spanning multiple years remain available for investigation."),
            ("6.3", "SAR Supporting Documentation",
             "All documentation supporting a SAR filing must be maintained separately from the "
             "general investigation file and subject to the extended 10-year retention period. "
             "This includes: the analyst's suspicion formation notes, the MLRO's review and "
             "approval, the submitted STR form, any AUSTRAC acknowledgment, and all transaction "
             "records referenced in the filing. The total_suspicious_transaction_volume_usd "
             "calculation used in the filing must be preserved with its component transactions."),
        ],
    },
    {
        "document_id": "DOC-ALERT-HANDBOOK",
        "document_type": "INVESTIGATION_HANDBOOK",
        "title": "Alert Investigation Handbook",
        "version": "v2.1",
        "effective_date": "2024-11-01",
        "jurisdiction": "AU",
        "clauses": [
            ("2.1", "Alert Triage Process",
             "All alerts must be triaged within 24 hours of generation. Triage assigns an "
             "initial priority (ROUTINE, URGENT, CRITICAL) and determines whether the alert "
             "requires full investigation or can be resolved at triage. CRITICAL alerts must "
             "be assigned to a senior analyst immediately. URGENT alerts must be assigned "
             "within 4 hours. ROUTINE alerts must be assigned within 24 hours. Unassigned "
             "alerts older than 24 hours contribute to the alert ageing metric."),
            ("2.3", "Triage Disposition Standards",
             "An alert may be closed at triage (without full investigation) only if: (a) the "
             "triggering activity has a documented legitimate explanation on file from a prior "
             "investigation within the last 6 months; (b) the alert severity is LOW or MEDIUM; "
             "and (c) the counterparty risk rating is LOW. All other alerts must proceed to "
             "full investigation. Triage closures must be documented with the rationale and "
             "the reference to the prior investigation."),
            ("3.1", "Investigation Workflow",
             "A full investigation follows the sequence: (1) gather all transactions linked to "
             "the alert; (2) review the counterparty's profile, risk rating, and prior alerts; "
             "(3) analyse the transaction pattern against known typologies; (4) document "
             "findings in the investigation narrative; (5) make a disposition recommendation. "
             "Steps 1-3 must be completed within 10 business days. The entire investigation "
             "must conclude within the 90-day limit per AML Policy §7.5."),
            ("3.3", "Escalation to MLRO",
             "An investigation must be escalated to the MLRO when: (a) the analyst forms a "
             "suspicion that may require an STR filing; (b) the counterparty is a PEP or has "
             "a sanctions screening match; (c) the aggregate transaction value under "
             "investigation exceeds $250,000; (d) the case involves more than 3 counterparties "
             "or spans more than 2 jurisdictions. MLRO escalation must occur within 48 hours "
             "of the triggering condition being met."),
            ("4.1", "Investigation Timeliness Targets",
             "In addition to the 90-day hard limit (AML Policy §7.5), the bank targets: "
             "CRITICAL cases resolved within 30 calendar days; URGENT cases within 45 calendar "
             "days; ROUTINE cases within 60 calendar days. The days_to_case_resolution metric "
             "is reported against both the hard limit and these soft targets. Cases exceeding "
             "their soft target must have a documented reason for delay."),
            ("4.4", "SAR Filing Decision",
             "A SAR must be filed when the investigation establishes reasonable grounds to "
             "suspect money laundering, terrorism financing, or other serious financial crime. "
             "The sar_filing_rate across all investigations is monitored as a quality indicator. "
             "The filing must occur within 72 hours of forming the suspicion — this is measured "
             "from the analyst's documented suspicion timestamp, not from the date the alert "
             "was generated."),
            ("5.1", "Closure Without SAR",
             "An investigation may be closed without SAR filing when: the analyst determines "
             "that the suspicious pattern has a verifiable legitimate explanation. The closure "
             "narrative must explicitly address each red flag identified during the investigation "
             "and explain why it does not constitute grounds for suspicion. Closures of cases "
             "involving transactions over $100,000 require supervisor sign-off."),
            ("5.4", "Post-Closure Monitoring",
             "Following case closure (whether by SAR filing or no-action), the counterparty "
             "must be placed on a 6-month enhanced surveillance list. During this period, any "
             "new alert of MEDIUM severity or above on the same counterparty must reference the "
             "prior investigation. Two or more alerts during the post-closure period must trigger "
             "a new investigation regardless of individual alert severity."),
            ("6.1", "Analyst Workload Standards",
             "No analyst may carry more than 25 active investigations simultaneously. The "
             "compliance operations manager must monitor assignment levels weekly and redistribute "
             "work when any analyst exceeds 80% capacity. Overloaded queues are a leading "
             "indicator of alert ageing breaches and must be addressed proactively."),
            ("6.3", "Quality Assurance Reviews",
             "A random sample of at least 10% of closed investigations must be reviewed by a "
             "senior analyst or the MLRO each quarter. QA reviews assess: completeness of the "
             "investigation narrative, appropriateness of the disposition, timeliness, and "
             "adherence to typology-specific investigation procedures. QA findings must be "
             "documented and material deficiencies must trigger re-investigation."),
            ("7.1", "Typology-Specific Investigation Guides",
             "Each monitored typology (structuring, round-tripping, velocity spikes, dormancy "
             "reactivation, mule networks, sanctions evasion) must have a published investigation "
             "guide specifying: the specific data points to gather, the pattern characteristics "
             "to confirm, the thresholds that distinguish true positive from false positive, and "
             "the escalation criteria. Guides must be reviewed annually and updated when typology "
             "behaviour evolves."),
            ("7.4", "Dormancy Investigation Considerations",
             "Investigations triggered by dormant account reactivation require additional steps "
             "beyond the standard workflow: (a) verify the account holder's current identity and "
             "contact details; (b) obtain an explanation for the dormancy period; (c) compare the "
             "reactivation transaction pattern against the account's historical profile before "
             "dormancy; (d) check whether the counterparty has opened new accounts during the "
             "dormancy period. The $50,000 aggregate threshold from the Correspondent Banking "
             "guidance §3.1 triggers MLRO notification but does not change investigation priority."),
            ("8.1", "Threshold Confusion Safeguards",
             "Analysts must be trained to distinguish between the multiple monetary thresholds "
             "used across the regulatory framework: $10,000 (statutory reporting), $25,000 "
             "(real-time wire screening), $50,000 (dormancy reactivation MLRO notification), "
             "$75,000 (EDD pre-approval), $100,000 (EDD trigger and closure supervisor sign-off), "
             "$150,000 (EDD weekly review trigger), and $250,000 (MLRO escalation during "
             "investigation). Incorrect threshold application must be flagged in QA reviews."),
        ],
    },
]

for doc in DOCS:
    reg_docs.append({
        "document_id": doc["document_id"],
        "document_type": doc["document_type"],
        "title": doc["title"],
        "version": doc["version"],
        "effective_date": doc["effective_date"],
        "jurisdiction": doc["jurisdiction"],
        "full_text": "\n\n".join(f"§{c[0]} {c[1]}\n{c[2]}" for c in doc["clauses"]),
        "synthetic_watermark": "SYNTHETIC_DATA_PAPERTRAIL_2026",
    })
    for clause_num, clause_title, clause_text in doc["clauses"]:
        reg_clauses.append({
            "clause_id": f"{doc['document_id']}-{clause_num.replace('.', '-')}",
            "document_id": doc["document_id"],
            "clause_number": clause_num,
            "clause_title": clause_title,
            "clause_text": clause_text,
        })

doc_df = pd.DataFrame(reg_docs)
clause_df = pd.DataFrame(reg_clauses)
print(f"  Regulatory documents: {len(doc_df)}, Clauses: {len(clause_df)}")

# ════════════════════════════════════════════════════════════
# WRITE CSVs
# ════════════════════════════════════════════════════════════
print("\nWriting CSVs...")
cp_df.to_csv(OUT / "counterparty.csv", index=False)
acct_df.to_csv(OUT / "account.csv", index=False)
txn_df.to_csv(OUT / "transaction.csv", index=False)
alert_df.to_csv(OUT / "alert.csv", index=False)
at_df.to_csv(OUT / "alert_transaction.csv", index=False)
case_df.to_csv(OUT / "case_investigation.csv", index=False)
ca_df.to_csv(OUT / "case_alert.csv", index=False)
wl_df.to_csv(OUT / "watchlist_entry.csv", index=False)
scr_df.to_csv(OUT / "watchlist_screening_result.csv", index=False)
doc_df.to_csv(OUT / "regulatory_document.csv", index=False)
clause_df.to_csv(OUT / "regulatory_document_clause.csv", index=False)

# Ground truth (answer key — never loaded into Snowflake)
gt_df = pd.DataFrame(ground_truth)
gt_df.to_csv(OUT / "ground_truth.csv", index=False)

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("GENERATION SUMMARY")
print("="*60)
summary = [
    ("COUNTERPARTY", len(cp_df)),
    ("ACCOUNT", len(acct_df)),
    ("TRANSACTION", len(txn_df)),
    ("ALERT", len(alert_df)),
    ("ALERT_TRANSACTION", len(at_df)),
    ("CASE_INVESTIGATION", len(case_df)),
    ("CASE_ALERT", len(ca_df)),
    ("WATCHLIST_ENTRY", len(wl_df)),
    ("WATCHLIST_SCREENING_RESULT", len(scr_df)),
    ("REGULATORY_DOCUMENT", len(doc_df)),
    ("REGULATORY_DOCUMENT_CLAUSE", len(clause_df)),
]
print(f"\n{'Table':<35} {'Rows':>10}")
print("-"*47)
for name, count in summary:
    print(f"  {name:<33} {count:>10,}")
print("-"*47)
print(f"  {'TOTAL':<33} {sum(c for _,c in summary):>10,}")

print(f"\n{'Typology':<30} {'CPs':>5} {'Txns':>8}")
print("-"*45)
for gt in ground_truth:
    n_cps = len(gt["counterparty_ids"].split("|")) if gt["counterparty_ids"] else 0
    n_txns = len(gt["transaction_ids"].split("|")) if gt["transaction_ids"] else 0
    print(f"  {gt['typology']:<28} {n_cps:>5} {n_txns:>8}")

print(f"\nGround truth entries: {len(ground_truth)}")
print(f"Output directory: {OUT}")
print("Done.")
