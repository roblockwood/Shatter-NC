"""Tests for G-code parser operation extraction."""
import pytest
from app.parsers.gcode_parser import GCodeParser


class TestToolOperationExtraction:
    """Test tool operation data extraction."""

    def test_extract_single_operation_with_full_feedrates(self):
        """Test parsing operation with all feedrate macros."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
G54
M1
G17 G90 G94
N25 G100 T01 X-0.5882 Y-5.0769 G43 Z2.7122 H01 D01 S5000 M3 M8
G4 P0.6
M298 L4
#500=39.4 (CUTTING)
#503=39.4 (ENTRY)
#504=39.4 (EXIT)
#505=787.4 (DIRECT)
G0 X-0.5882 Y-5.0769
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        assert 1 in operations
        assert len(operations[1]) == 1

        op = operations[1][0]
        assert op["operation_name"] == "ADAPTIVE1"
        assert op["spindle_speed"] == 5000
        assert op["feedrate_cutting"] == 39.4
        assert op["feedrate_entry"] == 39.4
        assert op["feedrate_exit"] == 39.4
        assert op["feedrate_direct"] == 787.4
        assert op["feedrate_finish"] is None
        assert op["feedrate_plunge"] is None

    def test_extract_operation_without_name(self):
        """Test operation without name comment."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

G54
N25 G100 T01 X0 Y0 G43 Z0 H01 S5000 M3
#500=50.0 (CUTTING)
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        assert 1 in operations
        op = operations[1][0]
        assert op["operation_name"] is None
        assert op["spindle_speed"] == 5000
        assert op["feedrate_cutting"] == 50.0

    def test_extract_operation_without_spindle_speed(self):
        """Test operation missing S parameter."""
        gcode = """
(T21 D=0.1181 CR=0.0591 - ZMIN=2.0036 - PROBE - L=1.9685/1.9685)

(PROBE GEOMETRY1)
N20 G100 T21 X2.3125 Y-4.2915 G43 Z4.2871 H21
#500=39.4 (CUTTING)
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        assert 21 in operations
        op = operations[21][0]
        assert op["operation_name"] == "PROBE GEOMETRY1"
        assert op["spindle_speed"] is None
        assert op["feedrate_cutting"] == 39.4

    def test_extract_multiple_operations_same_tool(self):
        """Test multiple operations using same tool."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
G1 X1 Y1

(2D CONTOUR1)
N30 G100 T01 X2 Y2 Z0 S5000 M3
#502=50.0 (FINISH)
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        assert 1 in operations
        assert len(operations[1]) == 2

        assert operations[1][0]["operation_name"] == "ADAPTIVE1"
        assert operations[1][0]["feedrate_cutting"] == 39.4

        assert operations[1][1]["operation_name"] == "2D CONTOUR1"
        assert operations[1][1]["feedrate_finish"] == 50.0

    def test_extract_operations_multiple_tools(self):
        """Test operations across different tools."""
        gcode = """
(T21 D=0.1181 CR=0.0591 - ZMIN=2.0036 - PROBE - L=1.9685/1.9685)
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(PROBE GEOMETRY1)
N20 G100 T21 X0 Y0 Z0 S3000 M3
#500=20.0 (CUTTING)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        assert 21 in operations
        assert 1 in operations
        assert operations[21][0]["spindle_speed"] == 3000
        assert operations[1][0]["spindle_speed"] == 5000

    def test_extract_operation_with_partial_feedrates(self):
        """Test operation with only some feedrate macros."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
#505=787.4 (DIRECT)
"""
        parser = GCodeParser(gcode)
        operations = parser.extract_tool_operations()

        op = operations[1][0]
        assert op["feedrate_cutting"] == 39.4
        assert op["feedrate_direct"] == 787.4
        assert op["feedrate_entry"] is None
        assert op["feedrate_finish"] is None
        assert op["feedrate_exit"] is None

    def test_integration_parse_merges_operations(self):
        """Test that parse() merges operations into tool metadata."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
"""
        parser = GCodeParser(gcode)
        result = parser.parse()

        assert len(result["tools"]) == 1
        tool = result["tools"][0]
        assert tool["tool_number"] == 1
        assert tool["diameter"] == 0.25
        assert "operations" in tool
        assert len(tool["operations"]) == 1
        assert tool["operations"][0]["spindle_speed"] == 5000

    def test_operation_name_with_numbers_and_spaces(self):
        """Test operation names containing numbers and spaces."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(2D CONTOUR1)
N30 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
"""
        parser = GCodeParser(gcode)
        ops = parser.extract_tool_operations()
        assert ops[1][0]["operation_name"] == "2D CONTOUR1"

    def test_no_operations_in_program(self):
        """Test program without any tool operations."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
G0 X0 Y0
M30
"""
        parser = GCodeParser(gcode)
        ops = parser.extract_tool_operations()
        assert ops == {}

    def test_tool_without_operations_gets_empty_list(self):
        """Test that tools without operations get empty operations list."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
G0 X0 Y0
"""
        parser = GCodeParser(gcode)
        result = parser.parse()

        tool = result["tools"][0]
        assert "operations" in tool
        assert tool["operations"] == []

    def test_feedrate_macro_variations(self):
        """Test different feedrate macro numbers."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(TEST_OP)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
#502=45.0 (FINISH)
#507=15.0 (PLUNGE)
#509=60.0 (TRANSITION)
"""
        parser = GCodeParser(gcode)
        ops = parser.extract_tool_operations()

        op = ops[1][0]
        assert op["feedrate_cutting"] == 39.4
        assert op["feedrate_finish"] == 45.0
        assert op["feedrate_plunge"] == 15.0
        assert op["feedrate_transition"] == 60.0

    def test_modal_spindle_speed_across_operations(self):
        """Test that spindle speed is tracked modally across operations."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)

(CONTOUR1)
N30 G100 T01 X2 Y2 Z0 M3
#502=45.0 (FINISH)

(FACE1)
N35 G100 T01 X4 Y4 Z0 S6000 M3
#500=50.0 (CUTTING)

(CONTOUR2)
N40 G100 T01 X6 Y6 Z0 M3
#502=55.0 (FINISH)
"""
        parser = GCodeParser(gcode)
        ops = parser.extract_tool_operations()

        # First operation: S5000 specified
        assert ops[1][0]["operation_name"] == "ADAPTIVE1"
        assert ops[1][0]["spindle_speed"] == 5000

        # Second operation: No S parameter, should use modal S5000
        assert ops[1][1]["operation_name"] == "CONTOUR1"
        assert ops[1][1]["spindle_speed"] == 5000  # Modal from previous operation

        # Third operation: New S6000 specified
        assert ops[1][2]["operation_name"] == "FACE1"
        assert ops[1][2]["spindle_speed"] == 6000

        # Fourth operation: No S parameter, should use modal S6000
        assert ops[1][3]["operation_name"] == "CONTOUR2"
        assert ops[1][3]["spindle_speed"] == 6000  # Modal from previous operation

    def test_operations_without_tool_calls(self):
        """Test operations that don't have G100 tool call lines (modal tool)."""
        gcode = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

(ADAPTIVE1)
N25 G100 T01 X0 Y0 Z0 S5000 M3
#500=39.4 (CUTTING)
#505=787.4 (DIRECT)
G1 X1 Y1

(2D CONTOUR1)
#502=39.4 (FINISH)
#503=39.4 (ENTRY)
#504=39.4 (EXIT)
G1 X2 Y2

(FACE2)
#500=50.0 (CUTTING)
#507=15.0 (PLUNGE)
G1 X3 Y3
"""
        parser = GCodeParser(gcode)
        ops = parser.extract_tool_operations()

        # Should find 3 operations all for tool 1
        assert 1 in ops
        assert len(ops[1]) == 3

        # First operation: Has tool call
        assert ops[1][0]["operation_name"] == "ADAPTIVE1"
        assert ops[1][0]["spindle_speed"] == 5000
        assert ops[1][0]["feedrate_cutting"] == 39.4
        assert ops[1][0]["feedrate_direct"] == 787.4

        # Second operation: No tool call, uses modal tool and spindle
        assert ops[1][1]["operation_name"] == "2D CONTOUR1"
        assert ops[1][1]["spindle_speed"] == 5000  # Modal from previous
        assert ops[1][1]["feedrate_finish"] == 39.4
        assert ops[1][1]["feedrate_entry"] == 39.4
        assert ops[1][1]["feedrate_exit"] == 39.4

        # Third operation: No tool call, uses modal tool and spindle
        assert ops[1][2]["operation_name"] == "FACE2"
        assert ops[1][2]["spindle_speed"] == 5000  # Modal from first operation
        assert ops[1][2]["feedrate_cutting"] == 50.0
        assert ops[1][2]["feedrate_plunge"] == 15.0
