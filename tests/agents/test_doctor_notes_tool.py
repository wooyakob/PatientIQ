#!/usr/bin/env python3
"""
Direct test of the doc_notes_search tool to diagnose search issues.
Tests the tool with the same queries that are failing in the UI.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def test_tool_import():
    """Test that we can import the tool."""
    logger.info("=" * 80)
    logger.info("TEST: Import doc_notes_search tool")
    logger.info("=" * 80)

    try:
        from doc_notes_search import doc_notes_search

        logger.info("✓ Tool imported successfully")
        return doc_notes_search
    except Exception as e:
        logger.error(f"✗ Failed to import tool: {e}", exc_info=True)
        return None


def test_search_medication_question(tool_func):
    """Test searching for medication discussions."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Search for medication discussions")
    logger.info("=" * 80)

    query = "What did I discuss with this patient about medication 2 weeks ago?"
    patient_id = "5"  # Emily Johnson based on the example data

    logger.info(f"Query: {query}")
    logger.info(f"Patient ID: {patient_id}")

    try:
        result = tool_func(query=query, patient_id=patient_id, top_k=5)

        logger.info("\nResult structure:")
        logger.info(f"  - Keys: {list(result.keys())}")

        if "error" in result:
            logger.error(f"  - Error: {result['error']}")

        if "docnotes_search_results" in result:
            notes = result["docnotes_search_results"]
            logger.info(f"  - Number of notes found: {len(notes)}")

            if notes:
                logger.info("\nNotes found:")
                for i, note in enumerate(notes, 1):
                    logger.info(f"\n  Note {i}:")
                    logger.info(
                        f"    - Patient: {note.get('patient_name', 'N/A')} (ID: {note.get('patient_id', 'N/A')})"
                    )
                    logger.info(f"    - Visit Date: {note.get('visit_date', 'N/A')}")
                    logger.info(f"    - Doctor: {note.get('doctor_name', 'N/A')}")
                    logger.info(f"    - Visit Notes: {note.get('visit_notes', 'N/A')[:200]}...")
                    if "similarity_score" in note:
                        logger.info(f"    - Similarity Score: {note.get('similarity_score')}")
            else:
                logger.warning("\n  ⚠️  NO NOTES FOUND - This is the problem!")

        return result
    except Exception as e:
        logger.error(f"\n✗ Search failed: {e}", exc_info=True)
        return None


def test_search_wheezes_question(tool_func):
    """Test searching for rare wheezes discussion."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Search for rare wheezes discussion")
    logger.info("=" * 80)

    query = "when did we discuss rare wheezes?"
    patient_id = "5"  # Emily Johnson

    logger.info(f"Query: {query}")
    logger.info(f"Patient ID: {patient_id}")

    try:
        result = tool_func(query=query, patient_id=patient_id, top_k=5)

        logger.info("\nResult structure:")
        logger.info(f"  - Keys: {list(result.keys())}")

        if "error" in result:
            logger.error(f"  - Error: {result['error']}")

        if "docnotes_search_results" in result:
            notes = result["docnotes_search_results"]
            logger.info(f"  - Number of notes found: {len(notes)}")

            if notes:
                logger.info("\nNotes found:")
                for i, note in enumerate(notes, 1):
                    logger.info(f"\n  Note {i}:")
                    logger.info(
                        f"    - Patient: {note.get('patient_name', 'N/A')} (ID: {note.get('patient_id', 'N/A')})"
                    )
                    logger.info(f"    - Visit Date: {note.get('visit_date', 'N/A')}")
                    logger.info(f"    - Visit Notes: {note.get('visit_notes', 'N/A')}")
                    if "similarity_score" in note:
                        logger.info(f"    - Similarity Score: {note.get('similarity_score')}")
            else:
                logger.warning("\n  ⚠️  NO NOTES FOUND - This is the problem!")

        return result
    except Exception as e:
        logger.error(f"\n✗ Search failed: {e}", exc_info=True)
        return None


def test_direct_database_query():
    """Test direct database query to verify data exists."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Direct database query for patient 5")
    logger.info("=" * 80)

    try:
        from couchbase.options import QueryOptions
        from _shared import cluster

        if not cluster:
            logger.error("✗ Database cluster not available")
            return None

        # Query all notes for patient 5
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id
            ORDER BY n.visit_date DESC
        """

        logger.info("Executing direct query for all notes for patient 5...")
        result = cluster.query(query_str, QueryOptions(named_parameters={"patient_id": "5"}))

        notes = list(result.rows())
        logger.info(f"\n✓ Found {len(notes)} total notes for patient 5")

        if notes:
            logger.info("\nAll notes for patient 5:")
            for i, note in enumerate(notes, 1):
                logger.info(f"\n  Note {i}:")
                logger.info(f"    - Visit Date: {note.get('visit_date', 'N/A')}")
                logger.info(f"    - Doctor: {note.get('doctor_name', 'N/A')}")
                logger.info(f"    - Notes: {note.get('visit_notes', 'N/A')}")

                # Check for medication keywords
                notes_text = note.get("visit_notes", "").lower()
                if "medication" in notes_text or "meds" in notes_text:
                    logger.info("    ⭐ Contains medication mention!")
                if "wheez" in notes_text:
                    logger.info("    ⭐ Contains wheezes mention!")

        return notes

    except Exception as e:
        logger.error(f"\n✗ Direct query failed: {e}", exc_info=True)
        return None


def test_embedding_generation():
    """Test that embeddings are being generated correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Embedding generation")
    logger.info("=" * 80)

    try:
        from _shared import get_nvidia_embedding

        query = "medication discussions"
        logger.info(f"Generating embedding for: '{query}'")

        embedding = get_nvidia_embedding(query)

        logger.info("✓ Embedding generated successfully")
        logger.info(f"  - Type: {type(embedding)}")
        logger.info(f"  - Length: {len(embedding) if hasattr(embedding, '__len__') else 'N/A'}")
        logger.info(
            f"  - First 5 values: {embedding[:5] if hasattr(embedding, '__getitem__') else 'N/A'}"
        )

        return embedding

    except Exception as e:
        logger.error(f"\n✗ Embedding generation failed: {e}", exc_info=True)
        return None


def test_vector_search_directly():
    """Test vector search directly with a known embedding."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Direct vector search query")
    logger.info("=" * 80)

    try:
        from couchbase.options import QueryOptions
        from _shared import cluster, get_nvidia_embedding

        if not cluster:
            logger.error("✗ Database cluster not available")
            return None

        # Generate embedding for medication query
        query = "medication discussions"
        logger.info(f"Generating embedding for: '{query}'")
        embedding = get_nvidia_embedding(query)

        logger.info(f"✓ Embedding generated: {len(embedding)} dimensions")

        # Try vector search
        query_str = """
            SELECT n.visit_date, n.visit_notes, n.doctor_name, n.patient_name, n.patient_id,
                   APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2") AS similarity_score
            FROM `Scripps`.Notes.Doctor n
            WHERE n.patient_id = $patient_id
            ORDER BY APPROX_VECTOR_DISTANCE(n.all_notes_vectorized, $query_vector, "L2")
            LIMIT 5
        """

        logger.info("Executing vector search query...")
        result = cluster.query(
            query_str,
            QueryOptions(named_parameters={"query_vector": embedding, "patient_id": "5"}),
        )

        notes = list(result.rows())
        logger.info(f"\n✓ Vector search returned {len(notes)} results")

        if notes:
            for i, note in enumerate(notes, 1):
                logger.info(f"\n  Result {i}:")
                logger.info(f"    - Similarity Score: {note.get('similarity_score', 'N/A')}")
                logger.info(f"    - Visit Date: {note.get('visit_date', 'N/A')}")
                logger.info(f"    - Notes: {note.get('visit_notes', 'N/A')[:150]}...")

        return notes

    except Exception as e:
        logger.error(f"\n✗ Vector search failed: {e}", exc_info=True)
        return None


def main():
    """Run all diagnostic tests."""
    logger.info("\n" + "=" * 80)
    logger.info("DOCTOR NOTES SEARCH TOOL DIAGNOSTICS")
    logger.info("=" * 80)

    # Test 1: Import the tool
    tool = test_tool_import()
    if not tool:
        logger.error("\n❌ Cannot proceed without tool import")
        return 1

    # Test 2: Check embedding generation
    test_embedding_generation()

    # Test 3: Direct database query (sanity check)
    test_direct_database_query()

    # Test 4: Vector search directly
    test_vector_search_directly()

    # Test 5: Test the tool with medication question
    test_search_medication_question(tool)

    # Test 6: Test the tool with wheezes question
    test_search_wheezes_question(tool)

    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTICS COMPLETE")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
