#!/usr/bin/env python3
"""
End-to-end API testing script for RAG Factory MVP.
Tests the complete workflow: Create project → Add source → Trigger job → Monitor progress
"""

import requests
import time
import json
from typing import Dict

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = f"Test Project {int(time.time())}"

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log(message: str, color=Colors.BLUE):
    print(f"{color}{message}{Colors.END}")

def log_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def log_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def log_info(message: str):
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def test_health_check():
    """Test 1: Health check endpoint"""
    log("\n=== Test 1: Health Check ===")

    response = requests.get(f"{API_BASE_URL}/health")

    if response.status_code == 200:
        health = response.json()
        log_success(f"API is healthy")
        log_info(f"Status: {json.dumps(health, indent=2)}")
        return True
    else:
        log_error(f"Health check failed: {response.status_code}")
        return False


def test_create_project() -> Dict:
    """Test 2: Create a RAG project"""
    log("\n=== Test 2: Create RAG Project ===")

    # Using RAG Factory database for testing
    project_data = {
        "name": TEST_PROJECT_NAME,
        "description": "Automated test project for RAG Factory MVP",
        "target_db_host": "localhost",
        "target_db_port": 5433,  # RAG Factory PostgreSQL port
        "target_db_name": "rag_factory_db",
        "target_db_user": "user",
        "target_db_password": "password",
        "target_table_name": f"test_vectors_{int(time.time())}",
        "embedding_model": "jina/jina-embeddings-v2-base-es",
        "embedding_dimension": 768,
        "chunk_size": 500,
        "chunk_overlap": 100
    }

    response = requests.post(f"{API_BASE_URL}/projects", json=project_data)

    if response.status_code == 201:
        project = response.json()
        log_success(f"Created project: {project['name']} (ID: {project['id']})")
        return project
    else:
        log_error(f"Failed to create project: {response.status_code} - {response.text}")
        return None


def test_connection(project: Dict):
    """Test 3: Test database connection"""
    log("\n=== Test 3: Test Database Connection ===")

    conn_test = {
        "host": project["target_db_host"],
        "port": project["target_db_port"],
        "database": project["target_db_name"],
        "user": project["target_db_user"],
        "password": project.get("target_db_password", "password")  # Use default if not returned
    }

    response = requests.post(f"{API_BASE_URL}/test-connection", json=conn_test)

    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            log_success(f"Connection test passed")
            log_info(f"pgvector available: {result['pgvector_available']}")
            return True
        else:
            log_error(f"Connection failed: {result['message']}")
            return False
    else:
        log_error(f"Connection test endpoint failed: {response.status_code}")
        return False


def test_create_data_source(project: Dict) -> Dict:
    """Test 4: Create a data source"""
    log("\n=== Test 4: Create Data Source ===")

    source_data = {
        "project_id": project["id"],
        "name": "Chile BCN SPARQL - Test",
        "source_type": "sparql",
        "country_code": "CL",
        "region": "National",
        "tags": {
            "language": "es",
            "jurisdiction": "national",
            "test": "true"
        },
        "config": {
            "endpoint": "https://datos.bcn.cl/es/endpoint-sparql",
            "limit": 5  # Small limit for testing
        },
        "sync_frequency": "manual"
    }

    response = requests.post(f"{API_BASE_URL}/sources", json=source_data)

    if response.status_code == 201:
        source = response.json()
        log_success(f"Created data source: {source['name']} (ID: {source['id']})")
        log_info(f"Country: {source['country_code']}, Region: {source['region']}")
        return source
    else:
        log_error(f"Failed to create source: {response.status_code} - {response.text}")
        return None


def test_create_job(project: Dict, source: Dict) -> Dict:
    """Test 5: Create and enqueue ingestion job"""
    log("\n=== Test 5: Create Ingestion Job ===")

    job_data = {
        "project_id": project["id"],
        "source_id": source["id"],
        "job_type": "full_sync"
    }

    response = requests.post(f"{API_BASE_URL}/jobs", json=job_data)

    if response.status_code == 201:
        job = response.json()
        log_success(f"Created job: {job['id']} (Status: {job['status']})")
        return job
    else:
        log_error(f"Failed to create job: {response.status_code} - {response.text}")
        return None


def test_monitor_job(job: Dict, timeout: int = 120):
    """Test 6: Monitor job progress"""
    log("\n=== Test 6: Monitor Job Progress ===")

    job_id = job["id"]
    start_time = time.time()
    last_status = None

    while time.time() - start_time < timeout:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")

        if response.status_code == 200:
            job_status = response.json()
            status = job_status["status"]

            if status != last_status:
                log_info(f"Job {job_id} status: {status}")
                if job_status.get("total_documents"):
                    log_info(f"Progress: {job_status['processed_documents']}/{job_status['total_documents']} " +
                           f"(Success: {job_status['successful_documents']}, Failed: {job_status['failed_documents']})")
                last_status = status

            if status == "completed":
                log_success(f"Job completed successfully!")
                log_info(f"Total: {job_status['total_documents']}, " +
                       f"Successful: {job_status['successful_documents']}, " +
                       f"Failed: {job_status['failed_documents']}")
                return True

            elif status == "failed":
                log_error(f"Job failed!")
                if job_status.get("error_log"):
                    log_error(f"Error: {job_status['error_log']}")
                return False

        time.sleep(5)  # Poll every 5 seconds

    log_error(f"Job monitoring timed out after {timeout} seconds")
    return False


def test_get_project_stats(project: Dict):
    """Test 7: Get project statistics"""
    log("\n=== Test 7: Get Project Statistics ===")

    response = requests.get(f"{API_BASE_URL}/projects/{project['id']}/stats")

    if response.status_code == 200:
        stats = response.json()
        log_success("Retrieved project stats")
        log_info(f"Documents: {stats['total_documents']} total, " +
               f"{stats['documents_completed']} completed, " +
               f"{stats['documents_failed']} failed")
        log_info(f"Jobs: {stats['total_jobs']} total, " +
               f"{stats['jobs_completed']} completed")
        return True
    else:
        log_error(f"Failed to get stats: {response.status_code}")
        return False


def cleanup_test_project(project: Dict):
    """Cleanup: Delete test project"""
    log("\n=== Cleanup: Delete Test Project ===")

    response = requests.delete(f"{API_BASE_URL}/projects/{project['id']}")

    if response.status_code == 204:
        log_success(f"Deleted test project {project['id']}")
        return True
    else:
        log_error(f"Failed to delete project: {response.status_code}")
        return False


def main():
    """Run all tests"""
    log("=" * 60)
    log("  RAG Factory MVP - End-to-End API Test", Colors.GREEN)
    log("=" * 60)

    # Test 1: Health check
    if not test_health_check():
        log_error("Health check failed. Make sure API is running.")
        return

    # Test 2: Create project
    project = test_create_project()
    if not project:
        return

    # Test 3: Test connection
    if not test_connection(project):
        cleanup_test_project(project)
        return

    # Test 4: Create data source
    source = test_create_data_source(project)
    if not source:
        cleanup_test_project(project)
        return

    # Test 5: Create job
    job = test_create_job(project, source)
    if not job:
        cleanup_test_project(project)
        return

    # Test 6: Monitor job
    job_success = test_monitor_job(job, timeout=180)

    # Test 7: Get stats (regardless of job status)
    test_get_project_stats(project)

    # Cleanup
    log_info("\nWould you like to keep the test project for inspection? (y/n)")
    # For automated testing, we'll auto-cleanup
    # In manual mode, you could prompt for input here
    auto_cleanup = True

    if auto_cleanup:
        cleanup_test_project(project)

    # Final summary
    log("\n" + "=" * 60)
    if job_success:
        log("  ✓ ALL TESTS PASSED", Colors.GREEN)
    else:
        log("  ✗ SOME TESTS FAILED", Colors.RED)
    log("=" * 60)


if __name__ == "__main__":
    main()
