"""Program management service for upload, versioning, and deployment."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.program import Program, ProgramDeployment
from app.models.machine import Machine
from app.parsers.gcode_parser import parse_gcode


class ProgramService:
    """Service for managing NC programs and deployments."""

    def __init__(self, db: Session):
        self.db = db

    def upload_program(
        self,
        gcode_content: str,
        original_filename: str,
        machine_id: Optional[int] = None,
        deployed_filename: Optional[str] = None,
        validate: bool = True,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a new NC program and optionally deploy to machine.

        Version Detection Logic:
        1. Parse G-code and extract metadata
        2. Compute SHA-256 hash of content
        3. Check if program with this hash already exists
           - If exists: Return existing program (no duplicate)
           - If new: Continue to step 4
        4. Get MAX(version_number) for this filename
        5. Insert new program with version_number = MAX + 1

        Args:
            gcode_content: Full G-code program content
            original_filename: Original filename (e.g., "PART_123_OP1.NC")
            machine_id: Optional machine ID for deployment
            deployed_filename: Optional O-number deployment (e.g., "O2000.nc")
            validate: Whether to validate program before uploading
            validation_results: Optional validation results dict to store with deployment

        Returns:
            Dict containing:
                - program: Program object (new or existing)
                - is_new_version: bool (True if newly created)
                - deployment: ProgramDeployment object (if deployed)
                - validation_results: dict (if validated)
        """
        # Step 1: Parse G-code
        try:
            parsed_metadata = parse_gcode(gcode_content)
        except Exception as e:
            raise ValueError(f"Failed to parse G-code: {str(e)}")

        # Step 2: Compute content hash
        content_hash = Program.compute_hash(gcode_content)

        # Step 3: Check if program already exists (by hash)
        existing_program = self.db.query(Program).filter(
            Program.content_hash == content_hash
        ).first()

        if existing_program:
            # Program already exists - return existing record (no duplicate)
            result = {
                "program": existing_program,
                "is_new_version": False,
                "deployment": None,
                "validation_results": None
            }

            # If deploying existing program, still create deployment record
            if machine_id and deployed_filename:
                deployment = self.deploy_program(
                    program_id=existing_program.id,
                    machine_id=machine_id,
                    deployed_filename=deployed_filename,
                    validate=validate,
                    validation_results=validation_results
                )
                result["deployment"] = deployment

            return result

        # Step 4: Determine version number
        max_version = self.db.query(func.max(Program.version_number)).filter(
            Program.original_filename == original_filename
        ).scalar()

        version_number = (max_version or 0) + 1

        # Step 5: Create new Program record
        new_program = Program(
            original_filename=original_filename,
            content_hash=content_hash,
            posted_date=parsed_metadata.get("posted_date"),
            version_number=version_number,
            program_metadata={
                "tools": parsed_metadata.get("tools", []),
                "wcs_offset": parsed_metadata.get("wcs_offset"),
                "stock_size": parsed_metadata.get("stock_size"),
            },
            file_size_bytes=parsed_metadata.get("file_size", 0),
            line_count=parsed_metadata.get("line_count", 0),
            estimated_runtime_seconds=parsed_metadata.get("estimated_runtime_seconds"),
        )

        self.db.add(new_program)
        self.db.commit()
        self.db.refresh(new_program)

        # Step 6: If deploying to machine, handle deployment
        deployment = None
        result_validation = validation_results

        if machine_id and deployed_filename:
            deployment = self.deploy_program(
                program_id=new_program.id,
                machine_id=machine_id,
                deployed_filename=deployed_filename,
                validate=validate,
                validation_results=validation_results
            )
            result_validation = deployment.validation_results

        return {
            "program": new_program,
            "is_new_version": True,
            "deployment": deployment,
            "validation_results": result_validation
        }

    def deploy_program(
        self,
        program_id: int,
        machine_id: int,
        deployed_filename: str,
        validate: bool = True,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> ProgramDeployment:
        """
        Deploy a program to a machine with O-number mapping.

        Deployment Flow:
        1. Validate program against machine (if requested)
        2. Mark any existing deployment with same O-number as replaced
        3. Create new deployment record
        4. Update program deployment stats

        Args:
            program_id: Program ID to deploy
            machine_id: Target machine ID
            deployed_filename: O-number format (e.g., "O2000.nc")
            validate: Whether to validate before deployment
            validation_results: Optional validation results dict to store with deployment

        Returns:
            ProgramDeployment object with full details
        """
        # Get program and machine
        program = self.db.query(Program).filter(Program.id == program_id).first()
        if not program:
            raise ValueError(f"Program {program_id} not found")

        machine = self.db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            raise ValueError(f"Machine {machine_id} not found")

        # Determine if validation passed
        # If validation_results is provided, use the "valid" field (default to True if not present)
        # If validation_results is None, assume no validation was performed (validation_passed = None)
        if validation_results is not None:
            validation_passed = validation_results.get("valid", True)
        else:
            validation_results = {}
            validation_passed = None  # No validation performed

        # Construct deployment path
        deployed_path = f"{machine.path}/{deployed_filename}"

        # Mark existing deployment as replaced (if O-number already in use)
        existing_deployment = self.db.query(ProgramDeployment).filter(
            ProgramDeployment.machine_id == machine_id,
            ProgramDeployment.deployed_filename == deployed_filename,
            ProgramDeployment.is_current == True
        ).first()

        if existing_deployment:
            existing_deployment.is_current = False
            existing_deployment.replaced_at = datetime.utcnow()
            # Will set replaced_by after creating new deployment

        # Create deployment record
        deployment = ProgramDeployment(
            program_id=program_id,
            machine_id=machine_id,
            deployed_filename=deployed_filename,
            deployed_path=deployed_path,
            validation_results=validation_results,
            validation_passed=validation_passed,
            is_current=True
        )

        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        # Update existing deployment with replaced_by reference
        if existing_deployment:
            existing_deployment.replaced_by = deployment.id
            self.db.commit()

        # Update program deployment stats
        program.last_deployed_at = datetime.utcnow()
        program.deployed_count = (program.deployed_count or 0) + 1
        self.db.commit()

        return deployment

    def get_program_versions(self, filename: str) -> list:
        """Get all versions of a program by filename."""
        return self.db.query(Program).filter(
            Program.original_filename == filename
        ).order_by(Program.version_number.desc()).all()

    def get_program_by_hash(self, content_hash: str) -> Optional[Program]:
        """Get program by content hash."""
        return self.db.query(Program).filter(
            Program.content_hash == content_hash
        ).first()

    def get_current_deployment(self, machine_id: int, deployed_filename: str) -> Optional[ProgramDeployment]:
        """Get the current deployment of a program on a machine."""
        return self.db.query(ProgramDeployment).filter(
            ProgramDeployment.machine_id == machine_id,
            ProgramDeployment.deployed_filename == deployed_filename,
            ProgramDeployment.is_current == True
        ).first()

    def get_deployment_history(
        self,
        machine_id: Optional[int] = None,
        program_id: Optional[int] = None,
        limit: int = 100
    ) -> list:
        """Get deployment history with optional filtering."""
        query = self.db.query(ProgramDeployment)

        if machine_id:
            query = query.filter(ProgramDeployment.machine_id == machine_id)
        if program_id:
            query = query.filter(ProgramDeployment.program_id == program_id)

        return query.order_by(ProgramDeployment.deployed_at.desc()).limit(limit).all()
