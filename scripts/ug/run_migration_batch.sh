#!/bin/bash
# Migration batch runner - Run this command to process next 10,000 records

cd /Users/anuprash/Desktop/projects/pup-umis-backend
poetry run python scripts/ug/migrate_ug_sem_result_current.py
