# OpenLibrary Wikipedia Links Migration Tool

A utility tool to help migrate Wikipedia references to Wikidata IDs in OpenLibrary author records.

## Overview

This tool assists in cleaning up legacy Wikipedia references in OpenLibrary author records by:

1. Identifying authors with Wikipedia fields that need to be migrated to Wikidata or the "Links" section as needed
2. Verifying and removing outdated Wikipedia references
3. Ensuring proper Wikidata ID linkage is maintained

## Technical Details

The project uses:
- PocketBase for data storage and management
- DuckDB for initial data analysis and extraction from OpenLibrary dumps
- Integration with My OpenLibrary Quick Statements tool for easy updates

## Workflow

1. Used DuckDB to query OpenLibrary's latest data dump to identify:
   - Authors with Wikipedia references
   - Authors with Wikidata IDs
   - Potential mismatches or outdated entries

2. Processed and imported the filtered dataset into PocketBase

3. Built a simple interface to:
   - Review author records
   - Verify Wikipedia/Wikidata relationships
   - Mark records as corrected
   - Track progress through ~1800 author records

## Purpose

This is a one-off utility project designed to:
- Learn and experiment with PocketBase
- Integrate with the OpenLibrary Quick Statements tool
- Clean up legacy data in OpenLibrary's author records

The tool will become obsolete once all ~1800 identified author records are processed and corrected.


Blog post: https://blog.rayberger.org/cleaning-up-legacy-wikipedia-links