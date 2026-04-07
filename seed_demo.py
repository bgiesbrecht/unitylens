"""Seed the UnityLens database with realistic demo data."""

from unitylens.store import db
from unitylens.sources.base import CatalogMeta, SchemaMeta, TableMeta, ColumnMeta

SOURCES = [
    ("prod_databricks", "databricks", "https://adb-1234567890.cloud.databricks.com"),
    ("analytics_snowflake", "snowflake", "analytics.us-east-1.snowflakecomputing.com"),
    ("legacy_oracle", "oracle", "oracle-prod.internal.corp"),
]

CATALOG_TREE = {
    "prod_databricks": {
        "clinical": {
            "ehr": [
                {
                    "name": "encounters",
                    "type": "MANAGED",
                    "comment": "Patient encounter records including admissions, discharges, and transfers",
                    "owner": "data_engineering",
                    "columns": [
                        ("encounter_id", "STRING", False, "Unique encounter identifier"),
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("admission_date", "DATE", False, "Date of admission"),
                        ("discharge_date", "DATE", True, "Date of discharge"),
                        ("encounter_type", "STRING", False, "Inpatient, Outpatient, Emergency"),
                        ("department", "STRING", True, "Admitting department"),
                        ("attending_provider_id", "STRING", True, "Attending physician NPI"),
                        ("diagnosis_code", "STRING", True, "Primary ICD-10 diagnosis code"),
                        ("status", "STRING", False, "Active, Discharged, Transferred"),
                        ("created_at", "TIMESTAMP", False, "Record creation timestamp"),
                    ],
                },
                {
                    "name": "patients",
                    "type": "MANAGED",
                    "comment": "Patient demographics and registration data",
                    "owner": "data_engineering",
                    "columns": [
                        ("patient_id", "STRING", False, "Medical record number"),
                        ("first_name", "STRING", False, "Patient first name"),
                        ("last_name", "STRING", False, "Patient last name"),
                        ("date_of_birth", "DATE", False, "Date of birth"),
                        ("gender", "STRING", True, "Patient gender"),
                        ("address_line1", "STRING", True, "Street address"),
                        ("city", "STRING", True, "City"),
                        ("state", "STRING", True, "State code"),
                        ("zip_code", "STRING", True, "ZIP code"),
                        ("phone", "STRING", True, "Primary phone number"),
                        ("insurance_plan_id", "STRING", True, "Insurance plan identifier"),
                        ("created_at", "TIMESTAMP", False, "Record creation timestamp"),
                    ],
                },
                {
                    "name": "vitals",
                    "type": "MANAGED",
                    "comment": "Patient vital signs recorded during encounters",
                    "owner": "clinical_analytics",
                    "columns": [
                        ("vital_id", "STRING", False, "Unique vital record ID"),
                        ("encounter_id", "STRING", False, "Associated encounter"),
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("recorded_at", "TIMESTAMP", False, "Time of recording"),
                        ("heart_rate", "INT", True, "Heart rate (bpm)"),
                        ("blood_pressure_systolic", "INT", True, "Systolic BP (mmHg)"),
                        ("blood_pressure_diastolic", "INT", True, "Diastolic BP (mmHg)"),
                        ("temperature", "DOUBLE", True, "Body temperature (F)"),
                        ("respiratory_rate", "INT", True, "Respiratory rate (breaths/min)"),
                        ("oxygen_saturation", "DOUBLE", True, "SpO2 percentage"),
                    ],
                },
            ],
            "pharmacy": [
                {
                    "name": "medications",
                    "type": "MANAGED",
                    "comment": "Medication master list with NDC codes and formulary status",
                    "owner": "pharmacy_ops",
                    "columns": [
                        ("medication_id", "STRING", False, "Medication identifier"),
                        ("ndc_code", "STRING", False, "National Drug Code"),
                        ("generic_name", "STRING", False, "Generic drug name"),
                        ("brand_name", "STRING", True, "Brand name"),
                        ("drug_class", "STRING", True, "Pharmacological class"),
                        ("form", "STRING", True, "Dosage form (tablet, injection, etc.)"),
                        ("strength", "STRING", True, "Dosage strength"),
                        ("formulary_status", "STRING", False, "On-formulary, Off-formulary"),
                    ],
                },
                {
                    "name": "prescriptions",
                    "type": "MANAGED",
                    "comment": "Prescription orders linked to encounters and patients",
                    "owner": "pharmacy_ops",
                    "columns": [
                        ("prescription_id", "STRING", False, "Prescription identifier"),
                        ("encounter_id", "STRING", False, "Associated encounter"),
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("medication_id", "STRING", False, "Prescribed medication"),
                        ("prescriber_id", "STRING", False, "Prescribing provider NPI"),
                        ("dosage", "STRING", True, "Prescribed dosage"),
                        ("frequency", "STRING", True, "Dosing frequency"),
                        ("start_date", "DATE", False, "Prescription start date"),
                        ("end_date", "DATE", True, "Prescription end date"),
                        ("status", "STRING", False, "Active, Completed, Discontinued"),
                    ],
                },
            ],
            "lab": [
                {
                    "name": "lab_orders",
                    "type": "MANAGED",
                    "comment": "Laboratory test orders with LOINC codes",
                    "owner": "lab_informatics",
                    "columns": [
                        ("order_id", "STRING", False, "Lab order identifier"),
                        ("encounter_id", "STRING", False, "Associated encounter"),
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("loinc_code", "STRING", False, "LOINC test code"),
                        ("test_name", "STRING", False, "Test display name"),
                        ("ordered_at", "TIMESTAMP", False, "Order timestamp"),
                        ("ordering_provider_id", "STRING", False, "Ordering provider NPI"),
                        ("status", "STRING", False, "Ordered, In Progress, Completed"),
                        ("priority", "STRING", False, "Routine, STAT, ASAP"),
                    ],
                },
                {
                    "name": "lab_results",
                    "type": "MANAGED",
                    "comment": "Laboratory test results with reference ranges and flags",
                    "owner": "lab_informatics",
                    "columns": [
                        ("result_id", "STRING", False, "Result identifier"),
                        ("order_id", "STRING", False, "Associated lab order"),
                        ("loinc_code", "STRING", False, "LOINC test code"),
                        ("value", "STRING", True, "Result value"),
                        ("unit", "STRING", True, "Unit of measure"),
                        ("reference_range_low", "DOUBLE", True, "Normal range lower bound"),
                        ("reference_range_high", "DOUBLE", True, "Normal range upper bound"),
                        ("abnormal_flag", "STRING", True, "H, L, HH, LL, or null"),
                        ("resulted_at", "TIMESTAMP", False, "Result timestamp"),
                    ],
                },
            ],
        },
        "finance": {
            "billing": [
                {
                    "name": "claims",
                    "type": "MANAGED",
                    "comment": "Insurance claims submitted for reimbursement",
                    "owner": "revenue_cycle",
                    "columns": [
                        ("claim_id", "STRING", False, "Claim identifier"),
                        ("encounter_id", "STRING", False, "Associated encounter"),
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("payer_id", "STRING", False, "Insurance payer"),
                        ("total_charges", "DECIMAL(12,2)", False, "Total billed charges"),
                        ("submitted_at", "TIMESTAMP", False, "Submission timestamp"),
                        ("status", "STRING", False, "Submitted, Accepted, Denied, Paid"),
                        ("drg_code", "STRING", True, "Diagnosis-Related Group code"),
                    ],
                },
                {
                    "name": "payments",
                    "type": "MANAGED",
                    "comment": "Payment transactions from payers and patients",
                    "owner": "revenue_cycle",
                    "columns": [
                        ("payment_id", "STRING", False, "Payment identifier"),
                        ("claim_id", "STRING", False, "Associated claim"),
                        ("amount", "DECIMAL(12,2)", False, "Payment amount"),
                        ("payment_date", "DATE", False, "Date of payment"),
                        ("payment_type", "STRING", False, "Insurance, Patient, Adjustment"),
                        ("payer_id", "STRING", True, "Paying entity"),
                    ],
                },
            ],
            "general_ledger": [
                {
                    "name": "accounts",
                    "type": "MANAGED",
                    "comment": "Chart of accounts for general ledger",
                    "owner": "accounting",
                    "columns": [
                        ("account_id", "STRING", False, "GL account number"),
                        ("account_name", "STRING", False, "Account description"),
                        ("account_type", "STRING", False, "Asset, Liability, Revenue, Expense"),
                        ("parent_account_id", "STRING", True, "Parent account for hierarchy"),
                        ("is_active", "BOOLEAN", False, "Whether account is active"),
                    ],
                },
                {
                    "name": "journal_entries",
                    "type": "MANAGED",
                    "comment": "General ledger journal entries and line items",
                    "owner": "accounting",
                    "columns": [
                        ("entry_id", "STRING", False, "Journal entry identifier"),
                        ("account_id", "STRING", False, "GL account"),
                        ("entry_date", "DATE", False, "Transaction date"),
                        ("debit", "DECIMAL(12,2)", True, "Debit amount"),
                        ("credit", "DECIMAL(12,2)", True, "Credit amount"),
                        ("description", "STRING", True, "Line item description"),
                        ("posted_by", "STRING", False, "User who posted"),
                        ("period", "STRING", False, "Fiscal period (YYYY-MM)"),
                    ],
                },
            ],
        },
    },
    "analytics_snowflake": {
        "analytics": {
            "reporting": [
                {
                    "name": "daily_census",
                    "type": "VIEW",
                    "comment": "Daily patient census by department and unit",
                    "owner": "analytics_team",
                    "columns": [
                        ("census_date", "DATE", False, "Census date"),
                        ("department", "STRING", False, "Department name"),
                        ("unit", "STRING", True, "Nursing unit"),
                        ("patient_count", "INT", False, "Number of patients"),
                        ("bed_capacity", "INT", False, "Total bed capacity"),
                        ("occupancy_rate", "DOUBLE", False, "Occupancy percentage"),
                    ],
                },
                {
                    "name": "readmission_rates",
                    "type": "VIEW",
                    "comment": "30-day readmission rates by diagnosis and department",
                    "owner": "quality_improvement",
                    "columns": [
                        ("period", "STRING", False, "Reporting period (YYYY-MM)"),
                        ("department", "STRING", False, "Department name"),
                        ("diagnosis_category", "STRING", False, "Diagnosis grouping"),
                        ("total_discharges", "INT", False, "Total discharges in period"),
                        ("readmissions", "INT", False, "30-day readmission count"),
                        ("readmission_rate", "DOUBLE", False, "Readmission rate percentage"),
                    ],
                },
                {
                    "name": "revenue_summary",
                    "type": "VIEW",
                    "comment": "Monthly revenue summary by service line and payer category",
                    "owner": "finance_analytics",
                    "columns": [
                        ("month", "STRING", False, "Fiscal month (YYYY-MM)"),
                        ("service_line", "STRING", False, "Service line category"),
                        ("payer_category", "STRING", False, "Insurance type grouping"),
                        ("gross_charges", "DECIMAL(14,2)", False, "Total gross charges"),
                        ("net_revenue", "DECIMAL(14,2)", False, "Net collected revenue"),
                        ("denial_rate", "DOUBLE", True, "Claim denial rate"),
                    ],
                },
            ],
            "data_science": [
                {
                    "name": "patient_risk_scores",
                    "type": "TABLE",
                    "comment": "ML-generated patient risk stratification scores",
                    "owner": "data_science_team",
                    "columns": [
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("score_date", "DATE", False, "Score calculation date"),
                        ("readmission_risk", "DOUBLE", False, "30-day readmission probability"),
                        ("mortality_risk", "DOUBLE", False, "In-hospital mortality probability"),
                        ("sepsis_risk", "DOUBLE", False, "Sepsis onset probability"),
                        ("model_version", "STRING", False, "Scoring model version"),
                    ],
                },
                {
                    "name": "feature_store",
                    "type": "TABLE",
                    "comment": "Pre-computed feature vectors for ML models",
                    "owner": "data_science_team",
                    "columns": [
                        ("patient_id", "STRING", False, "Patient MRN"),
                        ("feature_date", "DATE", False, "Feature computation date"),
                        ("age", "INT", False, "Patient age"),
                        ("comorbidity_index", "DOUBLE", False, "Charlson comorbidity index"),
                        ("prior_admissions_12m", "INT", False, "Admissions in prior 12 months"),
                        ("avg_los", "DOUBLE", True, "Average length of stay"),
                        ("medication_count", "INT", False, "Active medication count"),
                        ("lab_abnormal_count_30d", "INT", False, "Abnormal labs in 30 days"),
                    ],
                },
            ],
        },
    },
    "legacy_oracle": {
        "hr_system": {
            "personnel": [
                {
                    "name": "employees",
                    "type": "TABLE",
                    "comment": "Employee master records for all staff",
                    "owner": "hr_admin",
                    "columns": [
                        ("employee_id", "NUMBER", False, "Employee identifier"),
                        ("first_name", "VARCHAR2", False, "First name"),
                        ("last_name", "VARCHAR2", False, "Last name"),
                        ("department_id", "NUMBER", False, "Department reference"),
                        ("title", "VARCHAR2", True, "Job title"),
                        ("hire_date", "DATE", False, "Date of hire"),
                        ("status", "VARCHAR2", False, "Active, Inactive, Terminated"),
                        ("manager_id", "NUMBER", True, "Direct manager employee ID"),
                        ("email", "VARCHAR2", True, "Corporate email address"),
                    ],
                },
                {
                    "name": "departments",
                    "type": "TABLE",
                    "comment": "Department hierarchy and cost center mapping",
                    "owner": "hr_admin",
                    "columns": [
                        ("department_id", "NUMBER", False, "Department identifier"),
                        ("department_name", "VARCHAR2", False, "Department name"),
                        ("cost_center", "VARCHAR2", False, "Cost center code"),
                        ("parent_department_id", "NUMBER", True, "Parent department"),
                        ("head_count_budget", "NUMBER", True, "Budgeted headcount"),
                    ],
                },
            ],
            "scheduling": [
                {
                    "name": "shifts",
                    "type": "TABLE",
                    "comment": "Staff shift schedules and assignments",
                    "owner": "scheduling_admin",
                    "columns": [
                        ("shift_id", "NUMBER", False, "Shift identifier"),
                        ("employee_id", "NUMBER", False, "Assigned employee"),
                        ("shift_date", "DATE", False, "Shift date"),
                        ("start_time", "TIMESTAMP", False, "Shift start time"),
                        ("end_time", "TIMESTAMP", False, "Shift end time"),
                        ("department_id", "NUMBER", False, "Department assignment"),
                        ("shift_type", "VARCHAR2", False, "Day, Evening, Night, On-Call"),
                    ],
                },
            ],
        },
    },
}


def seed():
    db.init_db()
    conn = db.get_connection()
    try:
        # Insert sources
        for name, stype, host in SOURCES:
            db.upsert_source(conn, name, stype, host)
            db.update_source_status(conn, name, "connected", "", "2026-03-31T14:30:00Z")
        conn.commit()

        for source_name, catalogs in CATALOG_TREE.items():
            all_catalogs = []
            all_schemas = []
            all_tables = []
            all_columns = []

            for catalog_name, schemas in catalogs.items():
                all_catalogs.append(CatalogMeta(
                    source_name=source_name,
                    catalog_name=catalog_name,
                    comment=f"{catalog_name.replace('_', ' ').title()} data catalog",
                    owner="platform_admin",
                ))

                for schema_name, tables in schemas.items():
                    all_schemas.append(SchemaMeta(
                        source_name=source_name,
                        catalog_name=catalog_name,
                        schema_name=schema_name,
                        comment=f"{schema_name.replace('_', ' ').title()} schema",
                        owner="data_engineering",
                    ))

                    for tbl in tables:
                        all_tables.append(TableMeta(
                            source_name=source_name,
                            catalog_name=catalog_name,
                            schema_name=schema_name,
                            table_name=tbl["name"],
                            table_type=tbl["type"],
                            comment=tbl["comment"],
                            owner=tbl["owner"],
                        ))

                        for pos, (col_name, dtype, nullable, comment) in enumerate(tbl["columns"], 1):
                            all_columns.append(ColumnMeta(
                                source_name=source_name,
                                catalog_name=catalog_name,
                                schema_name=schema_name,
                                table_name=tbl["name"],
                                column_name=col_name,
                                data_type=dtype,
                                ordinal_position=pos,
                                is_nullable=nullable,
                                comment=comment,
                            ))

            db.delete_source_data(conn, source_name)
            db.insert_catalogs(conn, all_catalogs)
            db.insert_schemas(conn, all_schemas)
            db.insert_tables(conn, all_tables)
            db.insert_columns(conn, all_columns)
            conn.commit()

        db.rebuild_search_index(conn)
        conn.commit()

        # Print summary
        for label, table in [("Sources", "sources"), ("Catalogs", "catalogs"), ("Schemas", "schemas"), ("Tables", "tables"), ("Columns", "columns")]:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {label}: {cnt}")

        print("\nDemo data seeded successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
