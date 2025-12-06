"""
Comprehensive test suite for program tracking and event logging system.

Tests cover:
1. Database migration and model relationships
2. Program upload, versioning, and deduplication logic
3. Program deployment and O-number replacement
"""
import sys
sys.path.insert(0, 'backend')

from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import SessionLocal, engine, Base
from app.models import Machine, Program, ProgramDeployment, MachineStatusEvent, AlarmEvent, ProductionRun
from app.services.program_service import ProgramService
import hashlib

# Sample G-code content for testing
SAMPLE_GCODE_1 = """
; PROGRAM O2100
; DATE 2024-01-15
; PART_ID: PART_123_OP1
(T01 - 0.25" EndMill - 3" Flute)
G90 G94
M03 S3000
G00 X0 Y0 Z1.0
Z-0.25
G01 Z-0.5 F10
X1.0 Y1.0
M05
M30
"""

SAMPLE_GCODE_2 = """
; PROGRAM O2101
; DATE 2024-01-16
; PART_ID: PART_123_OP2
(T01 - 0.25" EndMill - 3" Flute)
G90 G94
M03 S3500
G00 X0 Y0 Z1.0
Z-0.3
G01 Z-0.6 F12
X2.0 Y2.0
M05
M30
"""

# Identical content to SAMPLE_GCODE_1 (for deduplication test)
SAMPLE_GCODE_DUPLICATE = SAMPLE_GCODE_1


def test_database_models():
    """Test 1: Database migration and model relationships."""
    print("\n" + "=" * 80)
    print("TEST 1: DATABASE MODELS AND RELATIONSHIPS")
    print("=" * 80)

    try:
        # Create all tables (should be idempotent)
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")

        # Verify tables exist by querying SQLAlchemy metadata
        table_names = [table.name for table in Base.metadata.tables.values()]
        required_tables = ['machines', 'programs', 'program_deployments',
                          'machine_status_events', 'alarm_events', 'production_runs']

        for table in required_tables:
            if table in table_names:
                print(f"✓ Table '{table}' verified")
            else:
                print(f"✗ Table '{table}' NOT FOUND")
                return False

        # Test model instantiation with a session
        db = SessionLocal()
        try:
            # Create test machine if it doesn't exist
            test_machine = db.query(Machine).filter(Machine.name == "TEST_MACHINE").first()
            if not test_machine:
                test_machine = Machine(
                    name="TEST_MACHINE",
                    ip_address="192.168.1.100",
                    http_port=8080,
                    ftp_port=21,
                    enabled=True,
                    path="/PROGRAM"
                )
                db.add(test_machine)
                db.commit()
                print("✓ Test machine created")
            else:
                print("✓ Test machine already exists")

            # Verify all model relationships
            print(f"✓ Machine ID: {test_machine.id}")
            print(f"✓ Machine relationships accessible: program_deployments={len(test_machine.program_deployments)}")

        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False


def test_program_versioning():
    """Test 2: Program upload, versioning, and deduplication."""
    print("\n" + "=" * 80)
    print("TEST 2: PROGRAM UPLOAD, VERSIONING, AND DEDUPLICATION")
    print("=" * 80)

    db = SessionLocal()
    try:
        service = ProgramService(db)

        # Test 2.1: Upload first program
        print("\n[2.1] Uploading PART_123_OP1 (first version)...")
        result1 = service.upload_program(
            gcode_content=SAMPLE_GCODE_1,
            original_filename="PART_123_OP1.NC",
            validate=False
        )

        prog1 = result1["program"]
        print(f"✓ Program created: ID={prog1.id}, Version={prog1.version_number}")
        assert prog1.version_number == 1, "First version should be 1"
        assert result1["is_new_version"] == True, "Should indicate new version"
        hash1 = prog1.content_hash
        print(f"✓ Content hash: {hash1}")

        # Test 2.2: Upload same content again (deduplication)
        print("\n[2.2] Uploading PART_123_OP1.NC again (identical content)...")
        result_dup = service.upload_program(
            gcode_content=SAMPLE_GCODE_DUPLICATE,
            original_filename="PART_123_OP1.NC",
            validate=False
        )

        prog_dup = result_dup["program"]
        print(f"✓ Program returned: ID={prog_dup.id}, Version={prog_dup.version_number}")
        assert prog_dup.id == prog1.id, "Should return same program (dedup by hash)"
        assert result_dup["is_new_version"] == False, "Should indicate NOT new"
        print("✓ Content deduplication works correctly")

        # Test 2.3: Upload different content with same filename (new version)
        print("\n[2.3] Uploading PART_123_OP1.NC with different content (new version)...")
        result2 = service.upload_program(
            gcode_content=SAMPLE_GCODE_2,
            original_filename="PART_123_OP1.NC",
            validate=False
        )

        prog2 = result2["program"]
        print(f"✓ Program created: ID={prog2.id}, Version={prog2.version_number}")
        assert prog2.version_number == 2, "Second version should be 2"
        assert prog2.id != prog1.id, "Should be different program (different content)"
        assert result2["is_new_version"] == True, "Should indicate new version"
        hash2 = prog2.content_hash
        print(f"✓ Content hash: {hash2}")
        assert hash1 != hash2, "Different content should have different hash"

        # Test 2.4: Query program versions
        print("\n[2.4] Querying program versions...")
        versions = service.get_program_versions("PART_123_OP1.NC")
        print(f"✓ Found {len(versions)} versions")
        assert len(versions) == 2, "Should have exactly 2 versions"
        assert versions[0].version_number == 2, "Most recent should be first"
        assert versions[1].version_number == 1, "Older should be second"
        print("✓ Program versioning works correctly")

        # Test 2.5: Query by hash
        print("\n[2.5] Querying program by hash...")
        found = service.get_program_by_hash(hash1)
        assert found.id == prog1.id, "Should find program by hash"
        print(f"✓ Found program by hash: {found.original_filename} v{found.version_number}")

        return True, prog1, prog2

    except Exception as e:
        print(f"✗ Program versioning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None
    finally:
        db.close()


def test_program_deployment(prog1, prog2):
    """Test 3: Program deployment and O-number replacement."""
    print("\n" + "=" * 80)
    print("TEST 3: PROGRAM DEPLOYMENT AND O-NUMBER REPLACEMENT")
    print("=" * 80)

    db = SessionLocal()
    try:
        service = ProgramService(db)

        # Get test machine
        machine = db.query(Machine).filter(Machine.name == "TEST_MACHINE").first()
        assert machine, "Test machine should exist"

        # Test 3.1: Deploy first program with O-number
        print("\n[3.1] Deploying program v1 to machine with O2000...")
        deploy1 = service.deploy_program(
            program_id=prog1.id,
            machine_id=machine.id,
            deployed_filename="O2000.nc",
            validate=False
        )

        print(f"✓ Deployment created: ID={deploy1.id}")
        print(f"  Deployed filename: {deploy1.deployed_filename}")
        print(f"  Deployed path: {deploy1.deployed_path}")
        assert deploy1.is_current == True, "First deployment should be current"
        assert deploy1.replaced_at is None, "First deployment should not be replaced"

        # Test 3.2: Deploy second program with same O-number
        print("\n[3.2] Deploying program v2 to same O-number on same machine...")
        deploy2 = service.deploy_program(
            program_id=prog2.id,
            machine_id=machine.id,
            deployed_filename="O2000.nc",
            validate=False
        )

        print(f"✓ Deployment created: ID={deploy2.id}")
        assert deploy2.is_current == True, "New deployment should be current"

        # Test 3.3: Verify old deployment marked as replaced
        print("\n[3.3] Verifying old deployment marked as replaced...")
        deploy1_updated = db.query(ProgramDeployment).filter(ProgramDeployment.id == deploy1.id).first()
        print(f"✓ Old deployment is_current: {deploy1_updated.is_current}")
        print(f"✓ Old deployment replaced_at: {deploy1_updated.replaced_at}")
        print(f"✓ Old deployment replaced_by: {deploy1_updated.replaced_by}")
        assert deploy1_updated.is_current == False, "Old deployment should not be current"
        assert deploy1_updated.replaced_at is not None, "Old deployment should have replaced_at"
        assert deploy1_updated.replaced_by == deploy2.id, "Should reference new deployment"

        # Test 3.4: Get current deployment
        print("\n[3.4] Querying current deployment for O2000...")
        current = service.get_current_deployment(machine.id, "O2000.nc")
        assert current.id == deploy2.id, "Should return latest deployment"
        print(f"✓ Current deployment: {current.deployed_filename} <- program v{current.program.version_number}")

        # Test 3.5: Deploy to different O-number
        print("\n[3.5] Deploying program v1 to different O-number (O2001)...")
        deploy3 = service.deploy_program(
            program_id=prog1.id,
            machine_id=machine.id,
            deployed_filename="O2001.nc",
            validate=False
        )

        print(f"✓ Deployment created: ID={deploy3.id}")
        assert deploy3.deployed_filename == "O2001.nc"
        assert deploy3.is_current == True

        # Verify O2000 is still pointing to prog2
        current_2000 = service.get_current_deployment(machine.id, "O2000.nc")
        current_2001 = service.get_current_deployment(machine.id, "O2001.nc")
        assert current_2000.program_id == prog2.id
        assert current_2001.program_id == prog1.id
        print("✓ Both O-numbers point to correct programs")

        # Test 3.6: Get deployment history
        print("\n[3.6] Querying deployment history...")
        history = service.get_deployment_history(machine_id=machine.id)
        print(f"✓ Found {len(history)} deployment records")
        assert len(history) >= 3, "Should have at least 3 deployments"

        return True

    except Exception as e:
        print(f"✗ Program deployment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_event_models():
    """Test 4: Event logging models."""
    print("\n" + "=" * 80)
    print("TEST 4: EVENT LOGGING MODELS")
    print("=" * 80)

    db = SessionLocal()
    try:
        machine = db.query(Machine).filter(Machine.name == "TEST_MACHINE").first()

        # Test 4.1: Create status event
        print("\n[4.1] Creating machine status event...")
        status_event = MachineStatusEvent(
            time=datetime.utcnow(),
            machine_id=machine.id,
            status="running",
            previous_status="idle",
            program_name="PART_123_OP1.NC",
            o_number="O2000",
            metrics={"cycle_time_seconds": 45.5, "power_on_hours": 1234.5}
        )
        db.add(status_event)
        db.commit()
        print(f"✓ Status event created: {status_event.status}")

        # Test 4.2: Create alarm event
        print("\n[4.2] Creating alarm event...")
        alarm_event = AlarmEvent(
            time=datetime.utcnow(),
            machine_id=machine.id,
            alarm_code="PS002",
            alarm_message="Spindle not ready",
            alarm_type="spindle",
            severity="high"
        )
        db.add(alarm_event)
        db.commit()
        print(f"✓ Alarm event created: {alarm_event.alarm_code}")

        # Test 4.3: Create production run
        print("\n[4.3] Creating production run...")
        prod_run = ProductionRun(
            machine_id=machine.id,
            program_name="PART_123_OP1.NC",
            o_number="O2000",
            started_at=datetime.utcnow(),
            cycle_count=0,
            parts_produced=0
        )
        db.add(prod_run)
        db.commit()
        print(f"✓ Production run created: {prod_run.program_name}")

        # Test 4.4: Update production run (completion)
        print("\n[4.4] Completing production run...")
        prod_run.ended_at = datetime.utcnow()
        prod_run.duration_seconds = 600
        prod_run.parts_produced = 10
        prod_run.completion_status = "completed"
        db.commit()
        print(f"✓ Production run completed: {prod_run.duration_seconds}s, {prod_run.parts_produced} parts")

        return True

    except Exception as e:
        print(f"✗ Event models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PROGRAM TRACKING SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    results = []

    # Test 1: Database models
    success = test_database_models()
    results.append(("Database Models", success))
    if not success:
        print("\n✗ Stopping tests - database models failed")
        return

    # Test 2: Program versioning
    success, prog1, prog2 = test_program_versioning()
    results.append(("Program Versioning", success))
    if not success or not prog1 or not prog2:
        print("\n✗ Stopping tests - program versioning failed")
        return

    # Test 3: Program deployment
    success = test_program_deployment(prog1, prog2)
    results.append(("Program Deployment", success))

    # Test 4: Event models
    success = test_event_models()
    results.append(("Event Models", success))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Program tracking system is ready.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
