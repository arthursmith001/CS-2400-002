import sys
import threading
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import argparse

MEMORY_SIZE = 1024  # 1024-byte shared memory
NUM_CORES = 2
NUM_THREADS_PER_CORE = 2
DEBUG = False  # Main debug flag
DEBUG_LEVEL = 1  # Debug verbosity level: 0=None, 1=Basic, 2=Detailed, 3=Verbose


@dataclass
class CPUState:
    registers: List[int]
    pc: int
    stack: List[int]
    flags: Dict[str, bool]
    memory: Dict[int, int]
    halted: bool = False


class InstructionSetSimulator:
    """Base simulator class with common functionality"""

    def __init__(self):
        self.state = CPUState(
            registers=[0] * 16,
            pc=0,
            stack=[],
            flags={"Z": False, "C": False, "N": False},
            memory={},
        )
        self.opcodes = {
            0b0000: self.nop,  # No operation
            0b0001: self.call,
            0b0010: self.ret,
            0b0011: self.halt,
            0b0100: self.push,
            0b0101: self.pop,
            0b0110: self.beq,
            0b0111: self.cmp,
            0b1000: self.add,
            0b1001: self.sub,
            0b1010: self.mul,
            0b1011: self.div,
            0b1100: self.load,
            0b1101: self.mov,
            0b1110: self.xor_op,
            0b1111: self.and_op,
            0b10000: self.store,  # Add STORE operation
        }
        self.current_instruction = 0
        self.log: List[str] = []
        self.breakpoints: List[int] = []
        self.step_count = 0

    def nop(self):
        """No operation"""
        self.log.append(f"[{self.step_count}] NOP")

    def reset(self):
        """Reset the simulator to initial state"""
        memory_copy = self.state.memory.copy()
        self.state = CPUState(
            registers=[0] * 16,
            pc=0,
            stack=[],
            flags={"Z": False, "C": False, "N": False},
            memory=memory_copy,
        )
        self.log = []
        self.step_count = 0

    def load_program(self, program: List[int], start_addr: int = 0):
        """Load program into memory starting at specified address"""
        for offset, instr in enumerate(program):
            self.state.memory[start_addr + offset * 4] = instr

    def call(self):
        addr = self.current_instruction & 0xFFFF
        self.state.stack.append(self.state.pc)
        self.state.pc = addr
        self.log.append(f"[{self.step_count}] CALL 0x{addr:04x}")

    def ret(self):
        if not self.state.stack:
            self.log.append(f"[{self.step_count}] RET ERROR: Stack underflow!")
            raise Exception("RET called with empty stack")
        return_addr = self.state.stack.pop()
        self.state.pc = return_addr
        self.log.append(f"[{self.step_count}] RET to 0x{return_addr:08x}")

    def halt(self):
        self.state.halted = True
        self.log.append(f"[{self.step_count}] HALT")

    def push(self):
        reg = (self.current_instruction >> 24) & 0b1111
        if reg >= len(self.state.registers):
            raise Exception(f"Invalid register R{reg}")
        self.state.stack.append(self.state.registers[reg])
        self.log.append(
            f"[{self.step_count}] PUSH R{reg} (0x{self.state.registers[reg]:08x})"
        )

    def pop(self):
        if not self.state.stack:
            self.log.append(f"[{self.step_count}] POP ERROR: Stack underflow!")
            raise Exception("POP called with empty stack")
        reg = (self.current_instruction >> 24) & 0b1111
        if reg >= len(self.state.registers):
            raise Exception(f"Invalid register R{reg}")
        self.state.registers[reg] = self.state.stack.pop()
        self.log.append(
            f"[{self.step_count}] POP R{reg} (0x{self.state.registers[reg]:08x})"
        )

    def beq(self):
        rs = (self.current_instruction >> 20) & 0b1111
        offset = self.current_instruction & 0xFFFF
        if offset & 0x8000:
            offset = offset - 0x10000
        if self.state.flags["Z"]:  # Changed to check Z flag instead of register value
            self.state.pc = (self.state.pc - 4) + offset
            self.log.append(
                f"[{self.step_count}] BEQ branch taken to PC=0x{self.state.pc:08x}"
            )
        else:
            self.log.append(f"[{self.step_count}] BEQ no branch")

    def cmp(self):
        rs = (self.current_instruction >> 20) & 0b1111
        rt = (self.current_instruction >> 16) & 0b1111
        a = self.state.registers[rs]
        b = self.state.registers[rt]
        result = a - b
        self.state.flags["Z"] = result == 0
        self.state.flags["N"] = ((result >> 31) & 1) == 1
        self.state.flags["C"] = b > a
        self.log.append(
            f"[{self.step_count}] CMP R{rs}(0x{a:08x}) with R{rt}(0x{b:08x})"
        )

    def alu_operation(self, op: str, rd: int, rs: int, rt: int):
        a = self.state.registers[rs]
        b = self.state.registers[rt]
        if op == "ADD":
            result = a + b
            self.state.flags["C"] = result > 0xFFFFFFFF
        elif op == "SUB":
            result = a - b
            self.state.flags["C"] = b > a
        elif op == "MUL":
            result = a * b
            self.state.flags["C"] = result > 0xFFFFFFFF
        elif op == "DIV":
            if b == 0:
                raise Exception("Division by zero")
            result = a // b
        elif op == "AND":
            result = a & b
        elif op == "OR":
            result = a | b
        elif op == "XOR":
            result = a ^ b
        else:
            raise Exception(f"Unknown ALU operation: {op}")
        result = result & 0xFFFFFFFF
        self.state.registers[rd] = result
        self.state.flags["Z"] = result == 0
        self.state.flags["N"] = ((result >> 31) & 1) == 1
        self.log.append(
            f"[{self.step_count}] {op} R{rd}=R{rs}(0x{a:08x}) {op} R{rt}(0x{b:08x}) = 0x{result:08x}"
        )

    def add(self):
        self.alu_operation("ADD", *self._decode_alu_operands())

    def sub(self):
        self.alu_operation("SUB", *self._decode_alu_operands())

    def mul(self):
        self.alu_operation("MUL", *self._decode_alu_operands())

    def div(self):
        self.alu_operation("DIV", *self._decode_alu_operands())

    def and_op(self):
        self.alu_operation("AND", *self._decode_alu_operands())

    def xor_op(self):
        self.alu_operation("XOR", *self._decode_alu_operands())

    def mov(self):
        rd = (self.current_instruction >> 24) & 0b1111
        imm = self.current_instruction & 0xFFFF
        if imm & 0x8000:
            imm = imm | 0xFFFF0000
        self.state.registers[rd] = imm
        self.log.append(f"[{self.step_count}] MOV R{rd} = {imm}")

    def load(self):
        rd = (self.current_instruction >> 24) & 0b1111
        rs = (self.current_instruction >> 20) & 0b1111
        imm = self.current_instruction & 0xFFFF
        addr = (self.state.registers[rs] + imm) & 0xFFFFFFFF
        value = self.state.memory.get(addr, 0)
        self.state.registers[rd] = value
        self.log.append(
            f"[{self.step_count}] LOAD R{rd} = MEM[R{rs} + {imm}] = {value}"
        )

    def _decode_alu_operands(self):
        rd = (self.current_instruction >> 24) & 0b1111
        rs = (self.current_instruction >> 20) & 0b1111
        rt = (self.current_instruction >> 16) & 0b1111
        return rd, rs, rt

    def print_state(self):
        print("\n" + "=" * 60)
        print(
            f"Step {self.step_count} | PC: 0x{self.state.pc:08x} | Flags: {self.state.flags}"
        )
        if self.state.stack:
            print(
                f"Stack Top: 0x{self.state.stack[-1]:08x} (Depth: {len(self.state.stack)})"
            )
        else:
            print("Stack: Empty")
        print("Last instruction:", self.log[-1] if self.log else "None")
        print("=" * 60)

    def print_registers(self):
        print("\nRegisters:")
        for i in range(0, len(self.state.registers), 4):
            regs = [
                f"R{i + j}: 0x{self.state.registers[i + j]:08x}"
                for j in range(4)
                if i + j < len(self.state.registers)
            ]
            print("  ".join(regs))

    def store(self):
        """Store register value to memory address"""
        rd = (self.current_instruction >> 24) & 0b1111
        rs = (self.current_instruction >> 20) & 0b1111
        rt = (self.current_instruction >> 16) & 0b1111
        addr = self.state.registers[rs]
        value = self.state.registers[rt]
        self.state.memory[addr] = value
        self.log.append(
            f"[{self.step_count}] STORE MEM[R{rs}(0x{addr:08x})] = R{rt}(0x{value:08x})"
        )


class Phase3Simulator(InstructionSetSimulator):
    """Phase 3 - Basic non-pipelined simulator"""

    def __init__(self):
        super().__init__()
        self.opcodes = {
            0b0000: self.nop,  # No operation
            0b0001: self.call,  # Function call
            0b0010: self.ret,  # Return from function
            0b0011: self.halt,  # Halt the CPU
            0b0100: self.push,  # Push register to stack
            0b0101: self.pop,  # Pop from stack to register
            0b0110: self.beq,  # Branch if Equal (Z flag)
            0b0111: self.cmp,  # Compare instruction
            0b1000: self.add,  # Addition
            0b1001: self.sub,  # Subtraction
            0b1010: self.mul,  # Multiplication
            0b1011: self.div,  # Division
            0b1100: self.and_op,  # Bitwise AND
            0b1101: self.or_op,  # Bitwise OR
            0b1110: self.xor_op,  # Bitwise XOR
        }

    def show_test_menu(self):
        """Display test menu and run selected test with proper return"""
        while True:  # Keep showing this menu until user chooses to exit
            print("\nTest Menu:")
            print("1. Simple Call Sequence Test")
            print("2. Nested Call Sequence Test")
            print("3. ALU Operations Test")
            print("4. Factorial Calculation Test")
            print("5. Return to Main Menu")

            choice = input("\nEnter test choice (1-5): ")
            if choice == "1":
                self.test_simple_call_sequence()
            elif choice == "2":
                self.test_nested_call_sequence()
            elif choice == "3":
                self.test_alu_operations()
            elif choice == "4":
                self.test_factorial_program()
            elif choice == "5":
                break  # Return to main menu
            else:
                print("Invalid choice. Please try again.")

    def or_op(self):
        """Bitwise OR operation"""
        self.alu_operation("OR", *self._decode_alu_operands())

    def fetch(self):
        if self.state.pc in self.state.memory:
            self.current_instruction = self.state.memory[self.state.pc]
            self.state.pc += 4
        else:
            raise Exception(f"Invalid PC address: 0x{self.state.pc:08x}")

    def decode_execute(self):
        opcode = (self.current_instruction >> 28) & 0b1111
        if opcode in self.opcodes:
            self.opcodes[opcode]()
        else:
            raise Exception(f"Unknown opcode: {opcode:04b}")
        self.step_count += 1

    def run(
        self,
        start_addr: int = 0,
        max_steps: int = 100,
        interactive: bool = False,
        debug: bool = False,
    ):
        self.state.pc = start_addr
        while not self.state.halted and self.step_count < max_steps:
            try:
                if self.state.pc in self.breakpoints:
                    print(f"Breakpoint hit at 0x{self.state.pc:08x}")
                    if interactive:
                        self.interactive_debug()
                self.fetch()
                self.decode_execute()
                if debug:
                    self.print_state()
                if interactive:
                    self.interactive_debug()
            except Exception as e:
                self.log.append(
                    f"Execution stopped at step {self.step_count}: {str(e)}"
                )
                print(f"ERROR: {str(e)}")
                break

    def interactive_debug(self):
        self.print_state()
        while True:
            cmd = input(
                "(s)tep, (c)ontinue, (r)egisters, (m)emory, (b)reakpoint, (q)uit? "
            ).lower()
            if cmd == "s":
                break
            elif cmd == "c":
                return
            elif cmd == "r":
                self.print_registers()
            elif cmd == "m":
                addr = input("Enter memory address (hex): ")
                try:
                    addr = int(addr, 16)
                    print(f"0x{addr:08x}: 0x{self.state.memory.get(addr, 0):08x}")
                except ValueError:
                    print("Invalid address")
            elif cmd == "b":
                addr = input("Enter breakpoint address (hex): ")
                try:
                    addr = int(addr, 16)
                    self.breakpoints.append(addr)
                    print(f"Breakpoint set at 0x{addr:08x}")
                except ValueError:
                    print("Invalid address")
            elif cmd == "q":
                sys.exit(0)
            else:
                print("Invalid command")

    def test_simple_call_sequence(self):
        """Test Scenario 1: Simple call sequence (PUSH R1; CALL 0x100; RET)"""
        print("\n" + "=" * 60)
        print("TEST: Simple Call Sequence")
        print("=" * 60)
        self.reset()
        self.state.registers[1] = 0x12345678
        program = [
            self.make_instruction(0b0100, rd=1),  # 0x0000: PUSH R1
            self.make_instruction(
                0b0001, address_or_operand=0x0100
            ),  # 0x0004: CALL 0x100
            self.make_instruction(
                0b0101, rd=1
            ),  # 0x0008: POP R1 (added this instruction)
            self.make_instruction(0b0011),  # 0x000C: HALT
            *([self.make_instruction(0b0000)] * ((0x100 // 4) - 4)),
            self.make_instruction(0b0010),  # 0x0100: RET
        ]
        self.load_program(program)
        self.run(max_steps=10)
        print("\nResults:")
        print(f"Final R1: 0x{self.state.registers[1]:08x} (Expected: 0x12345678)")
        print(f"Final Stack: {[hex(x) for x in self.state.stack]} (Expected: [])")
        print(f"Final PC: 0x{self.state.pc:08x} (Expected: 0x00000010)")
        print("\nExecution Log:")
        for entry in self.log:
            if (
                "CALL" in entry
                or "RET" in entry
                or "PUSH" in entry
                or "POP" in entry
                or "HALT" in entry
            ):
                print(entry)

    def test_nested_call_sequence(self):
        """Test Scenario 2: Nested calls (CALL func1; func1: CALL func2; RET) -"""
        print("\n" + "=" * 60)
        print("TEST: Nested Call Sequence ()")
        print("=" * 60)
        self.reset()
        self.state.registers[14] = 0
        program = [
            self.make_instruction(
                0b0001, address_or_operand=0x0100
            ),  # 0x0000: CALL func1
            self.make_instruction(0b0011),  # 0x0004: HALT
            *([self.make_instruction(0b0000)] * ((0x100 // 4) - 2)),
            self.make_instruction(0b0100, rd=14),  # 0x0100: PUSH R14 (link register)
            self.make_instruction(
                0b0001, address_or_operand=0x0200
            ),  # 0x0104: CALL func2
            self.make_instruction(0b0101, rd=14),  # 0x0108: POP R14
            self.make_instruction(0b0010),  # 0x010C: RET
            *([self.make_instruction(0b0000)] * ((0x200 // 4) - (0x010C // 4 + 1))),
            self.make_instruction(0b0010),  # 0x0200: RET
        ]
        self.load_program(program)
        self.run(max_steps=20)  #
        print("\nResults:")
        print(f"Final Stack: {[hex(x) for x in self.state.stack]} (Expected: [])")
        print(f"Final PC: 0x{self.state.pc:08x} (Expected: 0x00000008)")  #
        print(f"Final R14: 0x{self.state.registers[14]:08x} (Expected: 0x00000000)")  #
        print("\nExecution Log:")
        for entry in self.log:
            if (
                "CALL" in entry
                or "RET" in entry
                or "PUSH" in entry
                or "POP" in entry
                or "HALT" in entry
            ):
                print(entry)

    def test_alu_operations(self):
        """Test Scenario 3: ALU operations (ADD R1, R2, R3; SUB R4, R1, R5) -"""
        print("\n" + "=" * 60)
        print("TEST: ALU Operations ()")
        print("=" * 60)
        self.reset()
        self.state.registers[2] = 5  # R2 = 5
        self.state.registers[3] = 3  # R3 = 3
        self.state.registers[5] = 2  # R5 = 2
        program = [
            self.make_instruction(0b1000, rd=1, rs=2, rt=3),  # ADD R1 = R2 + R3
            self.make_instruction(0b1001, rd=4, rs=1, rt=5),  # SUB R4 = R1 - R5
            self.make_instruction(0b0011),  # HALT
        ]
        self.load_program(program)
        self.run(max_steps=10)  #
        print("\nResults:")
        print(f"R1 (5 + 3): {self.state.registers[1]} (Expected: 8)")  #
        print(f"R4 (8 - 2): {self.state.registers[4]} (Expected: 6)")  #
        print(
            f"Flags: Z={self.state.flags['Z']}, N={self.state.flags['N']}, C={self.state.flags['C']}"
        )  #
        print("\nExecution Log:")
        for entry in self.log:
            if "ADD" in entry or "SUB" in entry or "HALT" in entry:
                print(entry)

    def test_factorial_program(self):
        """Test a factorial calculation program (5!)"""
        print("\n" + "=" * 60)
        print("TEST: Factorial Calculation (5!)")  # Original phase5.py version
        print("=" * 60)
        self.reset()
        self.state.registers[1] = 5
        self.state.registers[2] = 1
        self.state.registers[15] = 1
        main_program_start_addr = 0x0000
        factorial_function_start_addr = 0x0008
        beq_offset_to_factorial_end = 0x0010
        program = [
            self.make_instruction(
                0b0001, address_or_operand=factorial_function_start_addr
            ),
            self.make_instruction(0b0011),
            self.make_instruction(0b0111, rs=1, rt=15),
            self.make_instruction(
                0b0110, address_or_operand=beq_offset_to_factorial_end
            ),
            self.make_instruction(0b1010, rd=2, rs=2, rt=1),
            self.make_instruction(0b1001, rd=1, rs=1, rt=15),
            self.make_instruction(
                0b0001, address_or_operand=factorial_function_start_addr
            ),
            self.make_instruction(0b0010),
        ]
        self.load_program(program, start_addr=main_program_start_addr)
        self.run(max_steps=100)
        print("\nResults:")
        print(f"5! = {self.state.registers[2]} (Expected: 120)")
        print(f"Final Stack: {[hex(x) for x in self.state.stack]} (Expected: [])")
        print(f"Final PC: 0x{self.state.pc:08x} (Expected: 0x00000008)")
        print("\nExecution Log (last 10 entries):")
        for entry in self.log[-10:]:
            print(entry)

    def make_instruction(
        self,
        opcode: int,
        rd: int = 0,
        rs: int = 0,
        rt: int = 0,
        address_or_operand: int = 0,
    ) -> int:
        return (
            (opcode << 28)
            | (rd << 24)
            | (rs << 20)
            | (rt << 16)
            | (address_or_operand & 0xFFFF)
        )


class Phase4Simulator(InstructionSetSimulator):
    """Phase 4 - Pipelined simulator"""

    def __init__(self):
        super().__init__()
        self.pipeline = {"F": None, "D": None, "E": None}
        self.stall_detected = False
        self.flush_detected = False
        self.pc_changed = False
        self.modified_registers = set()

    def execute_instruction(self):
        """Execute the current instruction in the pipeline"""
        if self.pipeline["E"] is None:
            return

        opcode = (self.pipeline["E"] >> 28) & 0b1111
        if opcode in self.opcodes:
            self.current_instruction = self.pipeline["E"]
            self.opcodes[opcode]()
            # Track modified registers for hazard detection
            if opcode in [
                0b1000,
                0b1001,
                0b1010,
                0b1011,
                0b1100,
                0b1101,
                0b1110,
                0b1111,
            ]:
                rd = (self.pipeline["E"] >> 24) & 0b1111
                self.modified_registers.add(rd)
        else:
            raise Exception(f"Unknown opcode: {opcode:04b}")

    # Rest of the Phase4Simulator class remains the same...

    def fetch(self):
        if self.state.pc not in self.state.memory:
            self.pipeline["F"] = None
            return
        instruction = self.state.memory[self.state.pc]
        self.pipeline["F"] = instruction
        self.state.pc += 4

    def pipeline_step(self):
        self.step_count += 1
        self.modified_registers = set()
        if self.has_data_hazard():
            self.pipeline["E"] = None
            self.stall_detected = True
            self.flush_detected = False
            self.log.append(f"[{self.step_count}] DATA HAZARD: Stall inserted")
        else:
            self.stall_detected = False
            self.flush_detected = False
            self.pipeline["E"] = self.pipeline["D"]
            self.pipeline["D"] = self.pipeline["F"]
            self.fetch()
        if self.pipeline["E"] is not None:
            self.current_instruction = self.pipeline["E"]
            self.execute_instruction()
        if self.pc_changed:
            self.pipeline["F"] = None
            self.pipeline["D"] = None
            self.flush_detected = True
            self.stall_detected = False
            self.pc_changed = False
            self.log.append(f"[{self.step_count}] CONTROL HAZARD: Pipeline flushed")

    def has_data_hazard(self):
        decode_instr = self.pipeline["D"]
        execute_instr = self.pipeline["E"]
        if decode_instr is None or execute_instr is None:
            return False
        d_opcode = (decode_instr >> 28) & 0b1111
        d_rs = (decode_instr >> 20) & 0b1111
        d_rt = (decode_instr >> 16) & 0b1111
        e_opcode = (execute_instr >> 28) & 0b1111
        e_rd = (execute_instr >> 24) & 0b1111
        if d_opcode in [0b1000, 0b1001, 0b1010]:
            if d_rs == e_rd or d_rt == e_rd:
                return True
        if d_opcode == 0b0110:
            if d_rs == e_rd:
                return True
        return False

    def print_pipeline_status(self, cycle_num):
        print(f"\n=== Cycle {cycle_num} ===")
        print(f"PC: 0x{self.state.pc:08x}")
        print(
            f"Flags: Z={self.state.flags['Z']}, N={self.state.flags['N']}, C={self.state.flags['C']}"
        )
        print("\nPipeline Stages:")
        print(f"Fetch (F): {format_instruction(self.pipeline['F'])}")
        print(f"Decode (D): {format_instruction(self.pipeline['D'])}")
        print(f"Execute (E): {format_instruction(self.pipeline['E'])}")
        if self.stall_detected:
            print("\nSTALL Detected (Data Hazard)")
        if self.flush_detected:
            print("\nFLUSH Detected (Control Hazard)")
        print(
            "\nModified Registers:",
            self.modified_registers if self.modified_registers else "None",
        )

    def run(
        self,
        start_addr: int = 0,
        max_steps: int = 100,
        interactive: bool = False,
        debug: bool = False,
    ):
        self.state.pc = start_addr
        for cycle in range(max_steps):
            self.print_pipeline_status(cycle + 1)
            time.sleep(1)
            self.pipeline_step()
            if (
                self.pipeline["F"] is None
                and self.pipeline["D"] is None
                and self.pipeline["E"] is None
            ):
                break
        print("\nSimulation Complete")

    def run_matrix_multiplication(self):
        """Run a parallelized matrix multiplication workload with detailed step-by-step output"""
        print("\nStarting Matrix Multiplication Workload with Detailed Debugging...")
        shared_memory = MemoryController()
        shared_memory.enable_stats(True)
        cores = [Core(i, shared_memory) for i in range(NUM_CORES)]
        matrix_size = 4

        # Memory layout constants
        MATRIX_A_BASE = 0x100
        MATRIX_B_BASE = 0x200
        MATRIX_C_BASE = 0x300

        # Initialize matrices
        matrix_a = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]]
        matrix_b = [
            [17, 18, 19, 20],
            [21, 22, 23, 24],
            [25, 26, 27, 28],
            [29, 30, 31, 32],
        ]

        # Load matrices into memory
        for i in range(matrix_size):
            for j in range(matrix_size):
                shared_memory.write(
                    MATRIX_A_BASE + (i * matrix_size + j) * 4, matrix_a[i][j]
                )
                shared_memory.write(
                    MATRIX_B_BASE + (i * matrix_size + j) * 4, matrix_b[i][j]
                )
                shared_memory.write(MATRIX_C_BASE + (i * matrix_size + j) * 4, 0)

        # Print initial matrices
        def print_matrices():
            print("\nCurrent Matrices:")
            print("Matrix A:")
            for i in range(matrix_size):
                print(
                    [
                        shared_memory.read(MATRIX_A_BASE + (i * matrix_size + j) * 4)
                        for j in range(matrix_size)
                    ]
                )
            print("Matrix B:")
            for i in range(matrix_size):
                print(
                    [
                        shared_memory.read(MATRIX_B_BASE + (i * matrix_size + j) * 4)
                        for j in range(matrix_size)
                    ]
                )
            print("Matrix C (Result):")
            for i in range(matrix_size):
                print(
                    [
                        shared_memory.read(MATRIX_C_BASE + (i * matrix_size + j) * 4)
                        for j in range(matrix_size)
                    ]
                )

        print_matrices()

        # Create programs for each thread
        programs = []
        total_threads = NUM_CORES * NUM_THREADS_PER_CORE
        rows_per_thread = max(1, matrix_size // total_threads)

        for thread_id in range(total_threads):
            start_row = thread_id * rows_per_thread
            end_row = min(start_row + rows_per_thread, matrix_size)

            program = [
                # Load constants
                make_instruction(
                    0b1101, rd=7, address_or_operand=matrix_size
                ),  # R7 = matrix_size
                make_instruction(0b1101, rd=8, address_or_operand=MATRIX_A_BASE),
                make_instruction(0b1101, rd=9, address_or_operand=MATRIX_B_BASE),
                make_instruction(0b1101, rd=10, address_or_operand=MATRIX_C_BASE),
                make_instruction(
                    0b1101, rd=0, address_or_operand=start_row
                ),  # R0 = start_row
                # Main computation loop
                make_instruction(0b0111, rs=0, rt=7),  # CMP R0, R7 (i < matrix_size?)
                make_instruction(
                    0b0110, address_or_operand=38 * 4
                ),  # BEQ to end if done
                # Initialize column counter (j)
                make_instruction(0b1101, rd=1, address_or_operand=0),  # R1 = 0
                # Column loop
                make_instruction(0b0111, rs=1, rt=7),  # CMP R1, R7 (j < matrix_size?)
                make_instruction(
                    0b0110, address_or_operand=32 * 4
                ),  # BEQ to end of column loop
                # Initialize sum and inner counter (k)
                make_instruction(0b1101, rd=6, address_or_operand=0),  # R6 = 0 (sum)
                make_instruction(0b1101, rd=2, address_or_operand=0),  # R2 = 0 (k)
                # Inner product loop
                make_instruction(0b0111, rs=2, rt=7),  # CMP R2, R7 (k < matrix_size?)
                make_instruction(
                    0b0110, address_or_operand=20 * 4
                ),  # BEQ to end of inner loop
                # Load A[i][k]
                make_instruction(0b1010, rd=3, rs=0, rt=7),  # R3 = i * matrix_size
                make_instruction(0b1000, rd=3, rs=3, rt=2),  # R3 += k
                make_instruction(0b1010, rd=3, rs=3, rt=15),  # R3 *= 4 (int size)
                make_instruction(0b1000, rd=3, rs=3, rt=8),  # R3 += MATRIX_A_BASE
                make_instruction(0b1100, rd=4, rs=3, rt=0),  # LOAD R4 = MEM[R3]
                # Load B[k][j]
                make_instruction(0b1010, rd=3, rs=2, rt=7),  # R3 = k * matrix_size
                make_instruction(0b1000, rd=3, rs=3, rt=1),  # R3 += j
                make_instruction(0b1010, rd=3, rs=3, rt=15),  # R3 *= 4
                make_instruction(0b1000, rd=3, rs=3, rt=9),  # R3 += MATRIX_B_BASE
                make_instruction(0b1100, rd=5, rs=3, rt=0),  # LOAD R5 = MEM[R3]
                # Multiply and accumulate
                make_instruction(0b1010, rd=3, rs=4, rt=5),  # R3 = A[i][k] * B[k][j]
                make_instruction(0b1000, rd=6, rs=6, rt=3),  # sum += R3
                # Increment k and loop
                make_instruction(0b1101, rd=3, address_or_operand=1),
                make_instruction(0b1000, rd=2, rs=2, rt=3),  # k++
                make_instruction(
                    0b0001, address_or_operand=12 * 4
                ),  # Jump back to inner loop
                # Store result to C[i][j]
                make_instruction(0b1010, rd=3, rs=0, rt=7),  # R3 = i * matrix_size
                make_instruction(0b1000, rd=3, rs=3, rt=1),  # R3 += j
                make_instruction(0b1010, rd=3, rs=3, rt=15),  # R3 *= 4
                make_instruction(0b1000, rd=3, rs=3, rt=10),  # R3 += MATRIX_C_BASE
                make_instruction(0b10000, rd=0, rs=3, rt=6),  # STORE MEM[R3] = R6 (sum)
                # Increment j and loop
                make_instruction(0b1101, rd=3, address_or_operand=1),
                make_instruction(0b1000, rd=1, rs=1, rt=3),  # j++
                make_instruction(
                    0b0001, address_or_operand=8 * 4
                ),  # Jump back to column loop
                # Increment i and loop
                make_instruction(0b1101, rd=3, address_or_operand=1),
                make_instruction(0b1000, rd=0, rs=0, rt=3),  # i++
                make_instruction(
                    0b0001, address_or_operand=5 * 4
                ),  # Jump back to start
                make_instruction(0b0011),  # HALT
            ]
            programs.append(program)

        # Set R15 to 4 for all threads (for multiplication by 4)
        for core in cores:
            for thread in core.threads:
                thread.state.registers[15] = 4

        # Load programs
        for core_id in range(NUM_CORES):
            for thread_id in range(NUM_THREADS_PER_CORE):
                global_thread_id = core_id * NUM_THREADS_PER_CORE + thread_id
                if global_thread_id < len(programs):
                    start_row = global_thread_id * rows_per_thread
                    end_row = min(start_row + rows_per_thread, matrix_size)
                    cores[core_id].load_program(thread_id, programs[global_thread_id])
                    print(
                        f"\nLoaded program for rows {start_row}-{end_row-1} on core {core_id} thread {thread_id}"
                    )
                    print(
                        f"Initial registers: {cores[core_id].threads[thread_id].state.registers}"
                    )

        # Run simulation with detailed output
        core_threads = []
        for core in cores:

            def core_runner(c):
                cycle = 0
                while cycle < 100:  # Max cycles
                    cycle += 1
                    print(f"\n=== Cycle {cycle} ===")

                    # Print core status
                    print(f"\nCore {c.core_id} Status:")
                    for t_idx, thread in enumerate(c.threads):
                        print(f"  Thread {t_idx}:")
                        print(f"    PC: 0x{thread.state.pc:04x}")
                        print(
                            f"    Pipeline: F={format_instruction(thread.pipeline['F'])}, D={format_instruction(thread.pipeline['D'])}, E={format_instruction(thread.pipeline['E'])}"
                        )
                        print(f"    Registers: {thread.state.registers}")
                        if thread.stall_detected:
                            print("    [STALL] Data hazard detected")
                        if thread.flush_detected:
                            print("    [FLUSH] Control hazard detected")

                    # Execute one cycle
                    if not c.cycle():
                        break

                    # Print matrix updates if any STORE occurred
                    for t_idx, thread in enumerate(c.threads):
                        if (
                            thread.pipeline["E"]
                            and ((thread.pipeline["E"] >> 28) & 0b1111) == 0b10000
                        ):  # STORE op
                            print(f"\nCore {c.core_id} Thread {t_idx} performed STORE:")
                            print_matrices()

                    time.sleep(0.5)  # Slow down for readability

            t = threading.Thread(target=core_runner, args=(core,))
            core_threads.append(t)
            t.start()

        for t in core_threads:
            t.join()

        # Verify results
        expected_c = [
            [sum(a * b for a, b in zip(row_a, col_b)) for col_b in zip(*matrix_b)]
            for row_a in matrix_a
        ]

        print("\nFinal Result Matrix C:")
        for i in range(matrix_size):
            row = []
            for j in range(matrix_size):
                addr = MATRIX_C_BASE + (i * matrix_size + j) * 4
                row.append(shared_memory.read(addr))
            print(row)

        print("\nExpected Result:")
        for row in expected_c:
            print(row)

        # Check for errors
        errors = 0
        for i in range(matrix_size):
            for j in range(matrix_size):
                addr = MATRIX_C_BASE + (i * matrix_size + j) * 4
                actual = shared_memory.read(addr)
                expected = expected_c[i][j]
                if actual != expected:
                    print(f"Mismatch at C[{i}][{j}]: Expected {expected}, Got {actual}")
                    errors += 1

        if errors == 0:
            print("\nMatrix multiplication completed successfully!")
        else:
            print(f"\nMatrix multiplication had {errors} errors.")

        # Print memory access statistics
        shared_memory.print_stats()


class MemoryController:
    """Optimized shared memory controller with synchronization for Phase 5"""

    def __init__(self, size: int = MEMORY_SIZE):
        self.memory = [0] * size
        self.lock = threading.Lock()

        # Use read-write lock pattern for better concurrency
        self.read_locks = [threading.Lock() for _ in range(16)]  # Memory segment locks
        self.write_lock = threading.Lock()  # Global write lock

        # Cache frequently accessed memory locations
        self.cache = {}
        self.cache_size = 64  # Size of cache in entries
        self.cache_lock = threading.Lock()

        # Memory access stats for profiling
        self.read_count = 0
        self.write_count = 0
        self.cache_hits = 0
        self.stats_enabled = False

    def _get_segment(self, addr: int) -> int:
        """Get memory segment for address"""
        return (addr // 64) % len(self.read_locks)

    def read(self, addr: int) -> int:
        """Read memory with optimized locking and caching"""
        # Check cache first
        with self.cache_lock:
            if addr in self.cache:
                if self.stats_enabled:
                    self.cache_hits += 1
                    self.read_count += 1
                return self.cache[addr]

        # Cache miss, read from memory with segmented locking
        segment = self._get_segment(addr)
        with self.read_locks[segment]:
            if 0 <= addr < len(self.memory):
                value = self.memory[addr]

                # Update cache
                with self.cache_lock:
                    if len(self.cache) >= self.cache_size:
                        # Simple LRU: remove random entry when full
                        if self.cache:
                            self.cache.pop(next(iter(self.cache)))
                    self.cache[addr] = value

                if self.stats_enabled:
                    self.read_count += 1
                return value
            return 0

    def write(self, addr: int, value: int) -> bool:
        """Write to memory with write-through caching"""
        # Use write lock for consistency
        with self.write_lock:
            if 0 <= addr < len(self.memory):
                self.memory[addr] = value & 0xFFFFFFFF

                # Update cache
                with self.cache_lock:
                    self.cache[addr] = value & 0xFFFFFFFF

                if self.stats_enabled:
                    self.write_count += 1
                return True
            return False

    def bulk_load(self, program: List[int], start_addr: int = 0) -> bool:
        """Efficiently load a block of memory"""
        with self.write_lock:
            if start_addr + len(program) * 4 > len(self.memory):
                return False

            # Update memory in a batch
            for offset, instr in enumerate(program):
                addr = start_addr + offset * 4
                self.memory[addr] = instr & 0xFFFFFFFF

                # Update cache for frequently accessed addresses
                with self.cache_lock:
                    self.cache[addr] = instr & 0xFFFFFFFF

            if self.stats_enabled:
                self.write_count += len(program)
            return True

    def flush_cache(self):
        """Clear the memory cache"""
        with self.cache_lock:
            self.cache.clear()

    def print_stats(self):
        """Print memory access statistics"""
        if not self.stats_enabled:
            return

        print("\nMemory Controller Statistics:")
        print(f"  Total reads: {self.read_count}")
        print(f"  Total writes: {self.write_count}")
        print(f"  Cache hits: {self.cache_hits}")
        hit_rate = (
            (self.cache_hits / self.read_count * 100) if self.read_count > 0 else 0
        )
        print(f"  Cache hit rate: {hit_rate:.2f}%")

    def enable_stats(self, enabled: bool = True):
        """Enable or disable statistics collection"""
        self.stats_enabled = enabled
        if not enabled:
            self.read_count = 0
            self.write_count = 0
            self.cache_hits = 0


class Core:
    """CPU Core with pipeline and thread support for Phase 5"""

    def __init__(self, core_id: int, memory: MemoryController):
        self.core_id = core_id
        self.memory = memory
        self.threads: List[ThreadContext] = []
        self.active_thread_idx = 0
        self.thread_lock = threading.Lock()
        for i in range(NUM_THREADS_PER_CORE):
            self.threads.append(ThreadContext(core_id, i, memory))

    def cycle(self) -> bool:
        with self.thread_lock:
            thread = self.threads[self.active_thread_idx]
            if thread.state.halted:
                self.active_thread_idx = (
                    self.active_thread_idx + 1
                ) % NUM_THREADS_PER_CORE
                thread = self.threads[self.active_thread_idx]
                if thread.state.halted:
                    return False
            thread.pipeline_step()
            return True

    def load_program(
        self, thread_id: int, program: List[int], start_addr: int = 0
    ) -> bool:
        if 0 <= thread_id < NUM_THREADS_PER_CORE:
            return self.threads[thread_id].load_program(program, start_addr)
        return False


class ThreadContext(InstructionSetSimulator):
    """Thread execution context with pipeline for Phase 5"""

    def __init__(self, core_id: int, thread_id: int, memory: MemoryController):
        super().__init__()
        self.core_id = core_id
        self.thread_id = thread_id
        self.memory = memory
        self.state = CPUState(
            registers=[0] * 16,
            pc=0,
            stack=[],
            flags={"Z": False, "C": False, "N": False},
            memory={},
        )
        self.pipeline = {"F": None, "D": None, "E": None}
        self.stall_detected = False
        self.flush_detected = False
        self.pc_changed = False
        self.modified_registers = set()

    def execute_instruction(self):
        """Execute the current instruction in the pipeline"""
        if self.pipeline["E"] is None:
            return

        opcode = (self.pipeline["E"] >> 28) & 0b1111
        if opcode == 0b10000:  # STORE operation (using 5 bits)
            rd = (self.pipeline["E"] >> 24) & 0b1111
            rs = (self.pipeline["E"] >> 20) & 0b1111
            rt = (self.pipeline["E"] >> 16) & 0b1111
            addr = self.state.registers[rs]
            value = self.state.registers[rt]
            success = self.memory.write(addr, value)
            if DEBUG:
                print(
                    f"Core {self.core_id}.{self.thread_id} storing {value} at 0x{addr:08x} (success: {success})"
                )
            self.log.append(
                f"[Core {self.core_id}.{self.thread_id}] STORE to 0x{addr:08x} = {value}"
            )
        elif opcode in self.opcodes:
            self.opcodes[opcode]()
        else:
            raise Exception(f"Unknown opcode: {opcode:04b}")

    def load_program(self, program: List[int], start_addr: int = 0) -> bool:
        self.state.pc = start_addr
        return self.memory.bulk_load(program, start_addr)

    def fetch(self):
        if self.state.pc >= MEMORY_SIZE:
            self.pipeline["F"] = None
            return
        instruction = self.memory.read(self.state.pc)
        self.pipeline["F"] = instruction
        self.state.pc += 4

    def pipeline_step(self):
        self.step_count += 1
        self.modified_registers = set()
        if DEBUG:
            print(f"\nCore {self.core_id}.{self.thread_id} Cycle {self.step_count}")
            print(
                f"Pipeline before step: F={format_instruction(self.pipeline['F'])}, D={format_instruction(self.pipeline['D'])}, E={format_instruction(self.pipeline['E'])}"
            )
        if self.has_data_hazard():
            self.pipeline["E"] = None
            self.stall_detected = True
            self.flush_detected = False
            self.log.append(
                f"[Core {self.core_id}.{self.thread_id}][{self.step_count}] DATA HAZARD: Stall inserted"
            )
            if DEBUG:
                print("Data hazard detected - stalling")
        else:
            self.stall_detected = False
            self.flush_detected = False
            self.pipeline["E"] = self.pipeline["D"]
            self.pipeline["D"] = self.pipeline["F"]
            self.fetch()
        if self.pipeline["E"] is not None:
            self.current_instruction = self.pipeline["E"]
            if DEBUG:
                print(f"Executing: {format_instruction(self.current_instruction)}")
            self.execute_instruction()
        if self.pc_changed:
            self.pipeline["F"] = None
            self.pipeline["D"] = None
            self.flush_detected = True
            self.stall_detected = False
            self.pc_changed = False
            self.log.append(
                f"[Core {self.core_id}.{self.thread_id}][{self.step_count}] CONTROL HAZARD: Pipeline flushed"
            )
            if DEBUG:
                print("Control hazard - pipeline flushed")
        if DEBUG:
            print(
                f"Pipeline after step: F={format_instruction(self.pipeline['F'])}, D={format_instruction(self.pipeline['D'])}, E={format_instruction(self.pipeline['E'])}"
            )
            print(f"PC: 0x{self.state.pc:04x}")
            print(f"Registers: {self.state.registers}")

    def has_data_hazard(self) -> bool:
        if self.pipeline["D"] is None or self.pipeline["E"] is None:
            return False
        d_opcode = (self.pipeline["D"] >> 28) & 0b1111
        d_rs = (self.pipeline["D"] >> 20) & 0b1111
        d_rt = (self.pipeline["D"] >> 16) & 0b1111
        e_opcode = (self.pipeline["E"] >> 28) & 0b1111
        e_rd = (self.pipeline["E"] >> 24) & 0b1111
        if d_opcode in [0b1000, 0b1001, 0b1010]:
            if d_rs == e_rd or d_rt == e_rd:
                return True
        if d_opcode == 0b1100:
            if d_rs == e_rd:
                return True
        return False


def make_instruction(
    opcode: int, rd: int = 0, rs: int = 0, rt: int = 0, address_or_operand: int = 0
) -> int:
    return (
        (opcode << 28)
        | (rd << 24)
        | (rs << 20)
        | (rt << 16)
        | (address_or_operand & 0xFFFF)
    )


def format_instruction(instr):
    if instr is None:
        return "-"
    opcode = (instr >> 28) & 0b1111
    rd = (instr >> 24) & 0b1111
    rs = (instr >> 20) & 0b1111
    rt = (instr >> 16) & 0b1111
    imm = instr & 0xFFFF
    if opcode == 0b0001:
        return f"CALL 0x{imm:04x}"
    elif opcode == 0b0010:
        return f"RET"
    elif opcode == 0b0011:
        return "HALT"
    elif opcode == 0b0100:
        return f"PUSH R{rd}"
    elif opcode == 0b0101:
        return f"POP R{rd}"
    elif opcode == 0b0110:
        return f"BEQ R{rs}, #{imm}"
    elif opcode == 0b0111:
        return f"CMP R{rs}, R{rt}"
    elif opcode == 0b1000:
        return f"ADD R{rd}, R{rs}, R{rt}"
    elif opcode == 0b1001:
        return f"SUB R{rd}, R{rs}, R{rt}"
    elif opcode == 0b1010:
        return f"MUL R{rd}, R{rs}, R{rt}"
    elif opcode == 0b1011:
        return f"DIV R{rd}, R{rs}, R{rt}"
    elif opcode == 0b1100:
        return f"LOAD R{rd}, [R{rs}+{imm}]"
    elif opcode == 0b1101:
        if -10000 < imm < 10000:
            return f"MOV R{rd}, #{imm}"
        else:
            return f"MOV R{rd}, #0x{imm & 0xFFFF:04x}"
    elif opcode == 0b1110:
        return f"XOR R{rd}, R{rs}, R{rt}"
    elif opcode == 0b1111:
        return f"AND R{rd}, R{rs}, R{rt}"
    else:
        return f"Unknown OPCODE {opcode:04b}"


def run_phase3():
    """Run the phase 3 (basic) simulator"""
    sim = Phase3Simulator()
    program = [
        make_instruction(0b1101, rd=1, address_or_operand=3),
        make_instruction(0b1101, rd=2, address_or_operand=5),
        make_instruction(0b1000, rd=0, rs=1, rt=2),
        make_instruction(0b0011),
    ]
    sim.load_program(program)
    sim.run(debug=True)


def run_phase4():
    """Run the phase 4 (pipelined) simulator"""
    sim = Phase4Simulator()
    program = [
        make_instruction(0b1101, rd=1, address_or_operand=3),
        make_instruction(0b1101, rd=2, address_or_operand=5),
        make_instruction(0b1000, rd=0, rs=1, rt=2),
        make_instruction(0b0011),
    ]
    sim.load_program(program)
    sim.run()


def run_phase5():
    """Run the phase 5 (multicore) simulator"""
    print("\nStarting multicore simulation...")
    shared_memory = MemoryController()
    cores = [Core(i, shared_memory) for i in range(NUM_CORES)]
    program = [
        make_instruction(0b1101, rd=1, address_or_operand=3),
        make_instruction(0b1101, rd=2, address_or_operand=5),
        make_instruction(0b1000, rd=0, rs=1, rt=2),
        make_instruction(0b0011),
    ]
    print("Loading program on all cores and threads...")
    for core in cores:
        for thread_id in range(NUM_THREADS_PER_CORE):
            core.load_program(thread_id, program)
            print(f"Loaded program on Core {core.core_id} Thread {thread_id}")
    print("\nStarting execution...")
    core_threads = []
    for core in cores:
        t = threading.Thread(target=lambda c=core: run_core(c, 100))
        core_threads.append(t)
        t.start()
        print(f"Started Core {core.core_id}")
    for t in core_threads:
        t.join()
    print("\nSimulation complete!")
    print("\nFinal register states:")
    for core in cores:
        for i, thread in enumerate(core.threads):
            print(f"Core {core.core_id} Thread {i}:")
            thread.print_registers()


def run_core(core: Core, cycles: int = 100):
    for cycle in range(cycles):
        if not core.cycle():
            break
        if DEBUG:
            print(f"Core {core.core_id} cycle {cycle}")
        time.sleep(0.01)


def main():
    print("CPU Simulator - Choose which version to run:")
    while True:  # Main program loop
        print("\nMain Menu:")
        print(
            "1. Phase 3 - Simple and Nested Calls, ALU Operations, Factorial Calculator"
        )
        print("2. Phase 4 - Pipeline with Control and Data Hazards Simulator")
        print("3. Phase 5 - Multicore/Multithread and Matrix Multiplication Simulator")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ")
        if choice == "1":
            sim = Phase3Simulator()
            sim.show_test_menu()  # Will return here when done
        elif choice == "2":
            run_phase4()
        elif choice == "3":
            while True:  # Phase 5 submenu loop
                print("\nPhase 5 - Choose simulation type:")
                print("1. Simple Multicore/Multithread")
                print("2. Matrix Multiplication")
                print("3. Back to Main Menu")

                subchoice = input("\nEnter your choice (1-3): ")
                if subchoice == "1":
                    run_phase5()
                elif subchoice == "2":
                    sim = Phase4Simulator()
                    sim.run_matrix_multiplication()
                elif subchoice == "3":
                    break  # Return to main menu
                else:
                    print("Invalid choice. Please try again.")
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
