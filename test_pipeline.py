# Databricks notebook source

# COMMAND ----------
from __future__ import annotations

import re
from functools import reduce
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, MapType, StructType, StructField, StringType

# COMMAND ----------
SOURCE_TABLE = "prod_builder_strategic_insights.prospect_mine.ext_lake_ext_si_cashmere"
ROW_LIMIT = 100
USE_SYNTHETIC_DATA = False
SHOW_PERSONAL_DATA = False
REQUIRE_50_APPROVED_EVENTS = False

EVENT_CATALOGUE_TABLE = ""

COLUMN_MAPPING = {
    "person_id": "cashmere_id",
    "name": "name",
    "age": "approx_age",
    "company": "primary_company",
    "life_event": "triggers",
}

APPROVED_EVENTS: list[dict[str, object]] = []

# COMMAND ----------
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_table(table: str) -> str:
    if not isinstance(table, str) or len(table.split(".")) != 3:
        raise ValueError("Table must be a three-part Unity Catalog identifier")
    if not all(IDENTIFIER.fullmatch(part) for part in table.split(".")):
        raise ValueError("Unsafe Unity Catalog table identifier")
    return table


def validate_events(events: list[dict[str, object]]) -> None:
    ids: set[str] = set()
    for event in events:
        event_id = event.get("id")
        patterns = event.get("patterns")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in ids:
            raise ValueError("Approved event IDs must be nonempty and unique")
        if not isinstance(event.get("label"), str) or not event["label"]:
            raise ValueError("Approved event label missing")
        if not isinstance(patterns, list) or not patterns or not all(
            isinstance(p, str) and p.strip() for p in patterns
        ):
            raise ValueError("Approved patterns must be nonempty strings")
        if event.get("sensitivity") not in ("normal", "sensitive"):
            raise ValueError("Event sensitivity must be normal or sensitive")
        for phrase in patterns:
            if len(phrase) > 200:
                raise ValueError("Event patterns must be 200 characters or fewer")
        ids.add(event_id)


def load_approved_events(table: str) -> list[dict[str, object]]:
    if not table:
        return []
    try:
        catalogue = spark.read.table(validate_table(table))
        catalogue.limit(1).collect()
    except Exception as exc:
        print(f"Catalogue unavailable; no event rules loaded: {type(exc).__name__}")
        return []
    required = {"id", "label", "patterns", "sensitivity", "approved"}
    missing = required - set(catalogue.columns)
    if missing:
        raise ValueError(f"Event catalogue missing columns: {sorted(missing)}")
    rules = catalogue.filter(F.col("approved") == F.lit(True)).select(
        "id", "label", "patterns", "sensitivity"
    )
    try:
        records = rules.limit(1001).collect()
    except Exception as exc:
        print(f"Catalogue cannot be read; no event rules loaded: {type(exc).__name__}")
        return []
    if len(records) > 1000:
        raise ValueError("Event catalogue exceeds 1000 approved rules")
    events = [row.asDict(recursive=True) for row in records]
    validate_events(events)
    return events


validate_table(SOURCE_TABLE)
if type(ROW_LIMIT) is not int or ROW_LIMIT <= 0:
    raise ValueError("ROW_LIMIT must be a positive integer")
if not {"person_id", "life_event"}.issubset(COLUMN_MAPPING):
    raise ValueError("person_id and life_event mappings are required")
if not all(IDENTIFIER.fullmatch(v) for v in COLUMN_MAPPING.values()):
    raise ValueError("Unsafe source column identifier")

if EVENT_CATALOGUE_TABLE:
    APPROVED_EVENTS = load_approved_events(EVENT_CATALOGUE_TABLE)
validate_events(APPROVED_EVENTS)
if REQUIRE_50_APPROVED_EVENTS and len(APPROVED_EVENTS) != 50:
    print("Approved 50-event catalogue unavailable or incomplete; no detection")
    APPROVED_EVENTS = []
print("Configuration valid; approved event definitions:", len(APPROVED_EVENTS))

# COMMAND ----------
if USE_SYNTHETIC_DATA:
    schema = StructType([
        StructField("cashmere_id", StringType()),
        StructField("name", StringType()),
        StructField("approx_age", StringType()),
        StructField("primary_company", StringType()),
        StructField("triggers", StringType()),
    ])
    source_df = spark.createDataFrame(
        [
            ("DEMO001", "Example Person", "45", "Example Co", "sample trigger"),
            ("DEMO002", "Another Person", "52", "Other Co", None),
        ],
        schema=schema,
    )
else:
    try:
        source_df = spark.read.table(SOURCE_TABLE).limit(ROW_LIMIT)
        source_df.limit(1).collect()
    except Exception as exc:
        raise RuntimeError(
            "Source table unavailable. Check SELECT and USE permissions; "
            "no data was changed."
        ) from exc

print("Source schema:")
source_df.printSchema()

print("Available columns:", source_df.columns)

# COMMAND ----------
required_categories = {"person_id", "life_event"}
missing_required = sorted(
    COLUMN_MAPPING[key]
    for key in required_categories
    if COLUMN_MAPPING[key] not in source_df.columns
)
if missing_required:
    raise ValueError(f"Missing required Databricks source columns: {missing_required}")

optional_missing = sorted(
    source_column
    for category, source_column in COLUMN_MAPPING.items()
    if category not in required_categories and source_column not in source_df.columns
)
if optional_missing:
    print("Optional source columns not found:", optional_missing)

# COMMAND ----------
def as_text(df: DataFrame, source_column: str):
    field_type = df.schema[source_column].dataType
    column = F.col(f"`{source_column}`")
    if isinstance(field_type, (ArrayType, StructType, MapType)):
        return F.to_json(column)
    return column.cast("string")


normalized_df = source_df
for category, source_column in COLUMN_MAPPING.items():
    if source_column in source_df.columns:
        value = as_text(source_df, source_column)
    else:
        value = F.lit(None).cast("string")
    normalized_df = normalized_df.withColumn(
        f"normalized_{category}", F.trim(value)
    )

normalized_df = normalized_df.withColumn(
    "record_valid",
    F.col("normalized_person_id").isNotNull()
    & (F.length(F.col("normalized_person_id")) > 0),
)
invalid_df = normalized_df.filter(~F.col("record_valid"))
valid_df = normalized_df.filter(F.col("record_valid"))

# COMMAND ----------
trigger = F.lower(F.col("normalized_life_event"))
candidate_frames = []
for event in APPROVED_EVENTS:
    phrases = sorted(
        {str(p).strip().lower() for p in event["patterns"]},
        key=len,
        reverse=True,
    )
    pattern = r"(?<!\w)(?:" + "|".join(re.escape(p) for p in phrases) + r")(?!\w)"
    matched = F.regexp_extract(trigger, pattern, 0)
    candidate_frames.append(
        valid_df.filter(F.length(matched) > 0)
        .withColumn("event_id", F.lit(str(event["id"])))
        .withColumn("event_label", F.lit(str(event["label"])))
        .withColumn("sensitivity", F.lit(str(event["sensitivity"])))
        .withColumn("evidence_field", F.lit(COLUMN_MAPPING["life_event"]))
        .withColumn("evidence_match", matched)
        .withColumn("evidence_source_table", F.lit(SOURCE_TABLE))
        .withColumn("evidence_observed_at", F.lit(None).cast("timestamp"))
        .withColumn("detection_method", F.lit("approved_phrase_match"))
        .withColumn("detection_status", F.lit("CANDIDATE_UNVERIFIED"))
    )

if candidate_frames:
    candidates_df = reduce(lambda a, b: a.unionByName(b), candidate_frames)
    candidates_df = candidates_df.dropDuplicates(["normalized_person_id", "event_id"])
else:
    candidates_df = valid_df.limit(0)
    for column in (
        "event_id", "event_label", "sensitivity", "evidence_field",
        "evidence_match", "evidence_source_table", "detection_method",
        "detection_status",
    ):
        candidates_df = candidates_df.withColumn(column, F.lit(None).cast("string"))
    candidates_df = candidates_df.withColumn(
        "evidence_observed_at", F.lit(None).cast("timestamp")
    )

# COMMAND ----------
decisions_df = (
    candidates_df
    .withColumn("routing_status", F.lit("HUMAN_REVIEW_REQUIRED"))
    .withColumn("outreach_permitted", F.lit(False))
    .withColumn("priority", F.lit(None).cast("integer"))
    .withColumn("review_status", F.lit("PENDING"))
    .withColumn("evidence_verified", F.lit(False))
    .withColumn(
        "policy_reason",
        F.when(
            F.col("sensitivity") == "sensitive",
            F.lit("Sensitive event: manual compliance review"),
        ).otherwise(F.lit("Evidence and consent not verified")),
    )
)

# COMMAND ----------
metrics = {
    "source_rows": source_df.count(),
    "valid_rows": valid_df.count(),
    "invalid_rows": invalid_df.count(),
    "approved_event_rules": len(APPROVED_EVENTS),
    "candidate_rows": candidates_df.count(),
    "review_rows": decisions_df.count(),
    "sensitive_candidates": decisions_df.filter(
        F.col("sensitivity") == "sensitive"
    ).count(),
}
print("Pipeline metrics:", metrics)

if not APPROVED_EVENTS:
    print("No approved event rules loaded; zero candidates are expected")
elif metrics["candidate_rows"] == 0:
    print("Rules loaded but no matching trigger text found in this sample")

if SHOW_PERSONAL_DATA:
    display(normalized_df.limit(10))
    display(decisions_df.limit(10))
else:
    display(
        decisions_df.groupBy("routing_status", "sensitivity")
        .count()
        .orderBy("routing_status", "sensitivity")
    )

# COMMAND ----------
print("Read-only run complete; no data was written")

# COMMAND ----------
assert metrics["source_rows"] == metrics["valid_rows"] + metrics["invalid_rows"]
assert decisions_df.filter(F.col("outreach_permitted") == True).limit(1).count() == 0
assert metrics["candidate_rows"] == metrics["review_rows"]
assert decisions_df.filter(F.col("review_status") != "PENDING").count() == 0
assert decisions_df.filter(F.col("evidence_verified") == True).count() == 0
if not APPROVED_EVENTS:
    assert metrics["candidate_rows"] == 0
print("Smoke tests passed")

