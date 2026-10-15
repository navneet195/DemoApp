# Databricks notebook source

# COMMAND ----------
from __future__ import annotations

import re
from functools import reduce
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType

# COMMAND ----------
SOURCE_TABLE = "prod_builder_strategic_insights.prospect_mine.ext_lake_ext_si_cashmere"
ROW_LIMIT = 100
USE_SYNTHETIC_DATA = False
SHOW_PERSONAL_DATA = False
PUBLISH_OUTPUT = False
OUTPUT_TABLE = ""

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
        ids.add(event_id)


validate_table(SOURCE_TABLE)
if type(ROW_LIMIT) is not int or ROW_LIMIT <= 0:
    raise ValueError("ROW_LIMIT must be a positive integer")
if not {"person_id", "life_event"}.issubset(COLUMN_MAPPING):
    raise ValueError("person_id and life_event mappings are required")
if not all(IDENTIFIER.fullmatch(v) for v in COLUMN_MAPPING.values()):
    raise ValueError("Unsafe source column identifier")
validate_events(APPROVED_EVENTS)
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
    source_df = spark.read.table(SOURCE_TABLE).limit(ROW_LIMIT)

print("Source schema:")
source_df.printSchema()

# COMMAND ----------
missing = sorted(set(COLUMN_MAPPING.values()) - set(source_df.columns))
if missing:
    raise ValueError(f"Missing Databricks source columns: {missing}")

# COMMAND ----------
normalized_df = source_df
for category, source_column in COLUMN_MAPPING.items():
    normalized_df = normalized_df.withColumn(
        f"normalized_{category}",
        F.trim(F.col(f"`{source_column}`").cast("string")),
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
    pattern = r"(?<!\w)(?:" + "|".join(
        re.escape(str(p).lower()) for p in event["patterns"]
    ) + r")(?!\w)"
    candidate_frames.append(
        valid_df.filter(trigger.rlike(pattern))
        .withColumn("event_id", F.lit(str(event["id"])))
        .withColumn("event_label", F.lit(str(event["label"])))
        .withColumn("sensitivity", F.lit(str(event["sensitivity"])))
        .withColumn("evidence_field", F.lit(COLUMN_MAPPING["life_event"]))
        .withColumn("detection_status", F.lit("CANDIDATE_UNVERIFIED"))
    )

if candidate_frames:
    candidates_df = reduce(lambda a, b: a.unionByName(b), candidate_frames)
else:
    candidates_df = (
        valid_df.limit(0)
        .withColumn("event_id", F.lit(None).cast("string"))
        .withColumn("event_label", F.lit(None).cast("string"))
        .withColumn("sensitivity", F.lit(None).cast("string"))
        .withColumn("evidence_field", F.lit(None).cast("string"))
        .withColumn("detection_status", F.lit(None).cast("string"))
    )

# COMMAND ----------
decisions_df = (
    candidates_df
    .withColumn("routing_status", F.lit("HUMAN_REVIEW_REQUIRED"))
    .withColumn("outreach_permitted", F.lit(False))
    .withColumn("priority", F.lit(None).cast("integer"))
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
}
print("Pipeline metrics:", metrics)
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
if PUBLISH_OUTPUT:
    target = validate_table(OUTPUT_TABLE)
    catalog, schema, _ = target.split(".")
    if catalog.lower().startswith("prod") or schema.lower().startswith("prod"):
        raise ValueError("Production-like output targets are blocked")
    if not APPROVED_EVENTS:
        raise ValueError("Cannot publish without an approved event catalogue")
    safe_output = decisions_df.select(
        F.col("normalized_person_id").alias("cashmere_id"),
        "event_id", "event_label", "detection_status",
        "routing_status", "outreach_permitted", "priority", "policy_reason",
    ).withColumn("processed_at", F.current_timestamp())
    safe_output.write.format("delta").mode("append").saveAsTable(target)
    print("Review-only output appended to:", target)
else:
    print("Output disabled: no Databricks tables were modified")

# COMMAND ----------
assert metrics["source_rows"] == metrics["valid_rows"] + metrics["invalid_rows"]
assert decisions_df.filter(F.col("outreach_permitted") == True).limit(1).count() == 0
assert metrics["candidate_rows"] == metrics["review_rows"]
if not APPROVED_EVENTS:
    assert metrics["candidate_rows"] == 0
print("Smoke tests passed")
