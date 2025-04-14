import sys
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class CPUState:
    """
    Represents the state of the CPU at any point in time.
    This includes registers, program counter, stack, flags, and memory.
    """
    registers: List[int]       # General purpose registers (16 of them)
    pc: int                    # Program counter - holds address of next instruction
    stack: List[int]           # Stack for function call/return and temporary storage
    flags: Dict[str, bool]     # Condition flags (Z=Zero, C=Carry, N=Negative)
    memory: Dict[int, int]     # Memory - maps addresses to 32-bit values
    halted: bool = False       # Whether the CPU has been halted

class InstructionSetSimulator:
    """
    Simulates a custom CPU architecture with a 32-bit instruction set.
    Includes support for ALU operations, control flow, and stack operations.
    """
    def __init__(self):
        """Initialize the simulator with a default CPU state and define opcodes."""
        self.state = CPUState(
            registers=[0] * 16,             # 16 registers, all initialized to 0
            pc=0,                           # Program counter starts at address 0
            stack=[],                       # Empty stack
            flags={'Z': False, 'C': False, 'N': False},  # Default flag values
            memory={}                       # Empty memory
        )
        # Define opcode mapping to instance methods
        self.opcodes = {
            0b0001: self.call,      # Function call
            0b0010: self.ret,       # Return from function
            0b0011: self.halt,      # Halt the CPU
            0b0100: self.push,      # Push register to stack
            0b0101: self.pop,       # Pop from stack to register
            0b0110: self.beq,       # Branch if Equal (Z flag)
            0b0111: self.cmp,       # Compare instruction
            0b1000: self.add,       # Addition
            0b1001: self.sub,       # Subtraction
            0b1010: self.mul,       # Multiplication
            0b1011: self.div,       # Division
            0b1100: self.and_op,    # Bitwise AND
            0b1101: self.or_op,     # Bitwise OR
            0b1110: self.xor_op     # Bitwise XOR
        }
        self.current_instruction = 0    # Holds the current instruction being executed
        self.log: List[str] = []        # Execution log for debugging
        self.breakpoints: List[int] = [] # Memory addresses where execution should pause
        self.step_count = 0             # Counter for instruction execution steps

    def reset(self):
        """
        Reset the simulator to initial state while preserving loaded program in memory.
        """
        memory_copy = self.state.memory.copy()  # Preserve memory contents
        self.state = CPUState(
            registers=[0] * 16,
            pc=0,
            stack=[],
            flags={'Z': False, 'C': False, 'N': False},
            memory=memory_copy    # Restore memory with program still loaded
        )
        self.log = []           # Clear execution log
        self.step_count = 0     # Reset step counter

    def load_program(self, program: List[int], start_addr: int = 0):
        """
        Load program into memory starting at specified address.
        
        Args:
            program: List of 32-bit instructions
            start_addr: Starting memory address (default: 0)
        """
        for offset, instr in enumerate(program):
            # Store each instruction at 4-byte aligned addresses (word-aligned)
            self.state.memory[start_addr + offset * 4] = instr

    def fetch(self):
        """
        Fetch the next instruction from memory at the address pointed to by PC.
        Increments PC by 4 (word size) after fetching.
        """
        if self.state.pc in self.state.memory:
            self.current_instruction = self.state.memory[self.state.pc]
            self.state.pc += 4   # Move to next instruction (4 bytes per instruction)
        else:
            raise Exception(f"Invalid PC address: 0x{self.state.pc:08x}")

    def decode_execute(self):
        """
        Decode the current instruction by extracting the opcode,
        then execute the corresponding operation.
        """
        # Extract 4-bit opcode from bits 28-31 of the instruction
        opcode = (self.current_instruction >> 28) & 0b1111
        if opcode in self.opcodes:
            self.opcodes[opcode]()  # Call the corresponding method
        else:
            raise Exception(f"Unknown opcode: {opcode:04b}")
        self.step_count += 1

    # Instruction implementations
    def call(self):
        """
        Call a function by jumping to a target address and saving return address on stack.
        Format: 0001 aaaaaaaaaaaaaaaaaaaaaaaaa (address in lower 24 bits)
        """
        addr = self.current_instruction & 0x00FFFFFF  # Extract 24-bit address
        return_addr = self.state.pc                   # Current PC is return address
        self.state.stack.append(return_addr)          # Save return address on stack
        self.state.pc = addr                          # Jump to function address
        self.log.append(f"[{self.step_count}] CALL 0x{addr:08x} (Return to 0x{return_addr:08x})")

    def ret(self):
        """
        Return from a function by popping return address from stack and jumping to it.
        Format: 0010 0000000000000000000000
        """
        if not self.state.stack:
            self.log.append(f"[{self.step_count}] RET ERROR: Stack underflow!")
            raise Exception("RET called with empty stack")
        return_addr = self.state.stack.pop()  # Get return address from stack
        self.state.pc = return_addr           # Jump to return address
        self.log.append(f"[{self.step_count}] RET to 0x{return_addr:08x}")

    def halt(self):
        """
        Halt the CPU execution.
        Format: 0011 0000000000000000000000
        """
        self.state.halted = True  # Set halted flag to stop execution
        self.log.append(f"[{self.step_count}] HALT")

    def push(self):
        """
        Push register value onto the stack.
        Format: 0100 rrrr 00000000000000000000 (r = register)
        """
        reg = (self.current_instruction >> 24) & 0b1111  # Extract register number
        if reg >= len(self.state.registers):
            raise Exception(f"Invalid register R{reg}")
        self.state.stack.append(self.state.registers[reg])  # Push register value to stack
        self.log.append(f"[{self.step_count}] PUSH R{reg} (0x{self.state.registers[reg]:08x})")

    def pop(self):
        """
        Pop value from stack into register.
        Format: 0101 rrrr 00000000000000000000 (r = register)
        """
        if not self.state.stack:
            self.log.append(f"[{self.step_count}] POP ERROR: Stack underflow!")
            raise Exception("POP called with empty stack")
        reg = (self.current_instruction >> 24) & 0b1111  # Extract register number
        if reg >= len(self.state.registers):
            raise Exception(f"Invalid register R{reg}")
        self.state.registers[reg] = self.state.stack.pop()  # Pop value into register
        self.log.append(f"[{self.step_count}] POP R{reg} (0x{self.state.registers[reg]:08x})")

    def beq(self):
        """
        Branch if equal - jumps to target address if Zero flag is set.
        Format: 0110 aaaaaaaaaaaaaaaaaaaaaaaaa (a = target address)
        """
        target_addr = self.current_instruction & 0x00FFFFFF  # Extract 24-bit address
        if self.state.flags['Z']:
            self.state.pc = target_addr  # Jump to target address if Z flag is set
            self.log.append(f"[{self.step_count}] BEQ taken to 0x{target_addr:08x}")
        else:
            self.log.append(f"[{self.step_count}] BEQ not taken")

    def cmp(self):
        """
        Compare two registers and set flags based on comparison result.
        Format: 0111 0000 ssss tttt 0000000000 (s,t = source registers)
        Sets Z flag if equal, N flag if first < second, C flag if second > first
        """
        rs = (self.current_instruction >> 20) & 0b1111  # First source register
        rt = (self.current_instruction >> 16) & 0b1111  # Second source register
        
        a = self.state.registers[rs]  # Value from first register
        b = self.state.registers[rt]  # Value from second register
        
        result = a - b  # Compute difference to determine relationship
        
        # Set flags based on comparison result
        self.state.flags['Z'] = (result == 0)  # Zero flag if equal
        self.state.flags['N'] = ((result >> 31) & 1) == 1  # Negative flag if MSB is 1
        self.state.flags['C'] = b > a  # Carry flag if second > first
        
        self.log.append(f"[{self.step_count}] CMP R{rs}(0x{a:08x}) with R{rt}(0x{b:08x}) "
                       f"[Z={self.state.flags['Z']}, N={self.state.flags['N']}, C={self.state.flags['C']}]")

    def alu_operation(self, op: str, rd: int, rs: int, rt: int):
        """
        Common handler for all ALU operations (ADD, SUB, MUL, etc).
        
        Args:
            op: Operation name (ADD, SUB, etc.)
            rd: Destination register 
            rs: First source register
            rt: Second source register
        """
        a = self.state.registers[rs]  # First operand
        b = self.state.registers[rt]  # Second operand
        
        # Perform the specified operation
        if op == 'ADD':
            result = a + b
            self.state.flags['C'] = result > 0xFFFFFFFF  # Carry if overflow
        elif op == 'SUB':
            result = a - b
            self.state.flags['C'] = b > a  # Carry if borrow needed
        elif op == 'MUL':
            result = a * b
            self.state.flags['C'] = result > 0xFFFFFFFF  # Carry if overflow
        elif op == 'DIV':
            if b == 0:
                raise Exception("Division by zero")
            result = a // b  # Integer division
        elif op == 'AND':
            result = a & b   # Bitwise AND
        elif op == 'OR':
            result = a | b   # Bitwise OR
        elif op == 'XOR':
            result = a ^ b   # Bitwise XOR
        else:
            raise Exception(f"Unknown ALU operation: {op}")
        
        # Truncate to 32 bits to simulate register size
        result = result & 0xFFFFFFFF
        self.state.registers[rd] = result
        
        # Set status flags
        self.state.flags['Z'] = (result == 0)  # Zero flag
        self.state.flags['N'] = ((result >> 31) & 1) == 1  # Negative flag
        
        self.log.append(f"[{self.step_count}] {op} R{rd}=R{rs}(0x{a:08x}) {op} R{rt}(0x{b:08x}) = 0x{result:08x} "
                       f"[Z={self.state.flags['Z']}, N={self.state.flags['N']}, C={self.state.flags['C']}]")

    # ALU operations - each calls the common handler with appropriate operation name
    def add(self): self.alu_operation('ADD', *self._decode_alu_operands())
    def sub(self): self.alu_operation('SUB', *self._decode_alu_operands())
    def mul(self): self.alu_operation('MUL', *self._decode_alu_operands())
    def div(self): self.alu_operation('DIV', *self._decode_alu_operands())
    def and_op(self): self.alu_operation('AND', *self._decode_alu_operands())
    def or_op(self): self.alu_operation('OR', *self._decode_alu_operands())
    def xor_op(self): self.alu_operation('XOR', *self._decode_alu_operands())

    def _decode_alu_operands(self):
        """
        Helper to decode ALU instruction operands.
        Format for ALU ops: xxxx dddd ssss tttt 0000000000000000
        Where:
            d = destination register
            s = first source register
            t = second source register
        
        Returns:
            tuple: (destination_reg, source_reg1, source_reg2)
        """
        rd = (self.current_instruction >> 24) & 0b1111  # Destination register
        rs = (self.current_instruction >> 20) & 0b1111  # First source register
        rt = (self.current_instruction >> 16) & 0b1111  # Second source register
        return rd, rs, rt

    def run(self, start_addr: int = 0, max_steps: int = 100, interactive: bool = False, debug: bool = False):
        """
        Run the simulator from a starting address until halted or max steps reached.
        
        Args:
            start_addr: Starting memory address (default: 0)
            max_steps: Maximum number of instructions to execute (default: 100)
            interactive: Enable interactive debugging (default: False)
            debug: Print state after each instruction (default: False)
        """
        self.state.pc = start_addr  # Set program counter to start address
        
        while not self.state.halted and self.step_count < max_steps:
            try:
                # Check for breakpoints
                if self.state.pc in self.breakpoints:
                    print(f"Breakpoint hit at 0x{self.state.pc:08x}")
                    if interactive:
                        self.interactive_debug()
                
                self.fetch()             # Fetch instruction from memory
                self.decode_execute()    # Decode and execute instruction
                
                if debug:
                    self.print_state()   # Print CPU state if debug enabled
                    
                if interactive:
                    self.interactive_debug()  # Enter interactive debug mode if enabled
                    
            except Exception as e:
                self.log.append(f"Execution stopped at step {self.step_count}: {str(e)}")
                print(f"ERROR: {str(e)}")
                break

    def interactive_debug(self):
        """
        Interactive debugger interface allowing inspection and control of execution.
        Supports step-by-step execution, register viewing, and breakpoints.
        """
        self.print_state()  # Show current CPU state
        while True:
            cmd = input("(s)tep, (c)ontinue, (r)egisters, (m)emory, (b)reakpoint, (q)uit? ").lower()
            if cmd == 's':
                break  # Execute one instruction and return to debug
            elif cmd == 'c':
                return  # Continue execution without debug
            elif cmd == 'r':
                self.print_registers()  # Print register values
            elif cmd == 'm':
                addr = input("Enter memory address (hex): ")
                try:
                    addr = int(addr, 16)  # Convert hex string to int
                    print(f"0x{addr:08x}: 0x{self.state.memory.get(addr, 0):08x}")
                except ValueError:
                    print("Invalid address")
            elif cmd == 'b':
                addr = input("Enter breakpoint address (hex): ")
                try:
                    addr = int(addr, 16)  # Convert hex string to int
                    self.breakpoints.append(addr)  # Add breakpoint
                    print(f"Breakpoint set at 0x{addr:08x}")
                except ValueError:
                    print("Invalid address")
            elif cmd == 'q':
                sys.exit(0)  # Exit program
            else:
                print("Invalid command")

    def print_state(self):
        """Print current CPU state for debugging."""
        print("\n" + "="*60)
        print(f"Step {self.step_count} | PC: 0x{self.state.pc:08x} | Flags: {self.state.flags}")
        if self.state.stack:
            print(f"Stack Top: 0x{self.state.stack[-1]:08x} (Depth: {len(self.state.stack)})")
        else:
            print("Stack: Empty")
        print("Last instruction:", self.log[-1] if self.log else "None")
        print("="*60)

    def print_registers(self):
        """Print register contents in a formatted grid."""
        print("\nRegisters:")
        for i in range(0, len(self.state.registers), 4):
            regs = [f"R{i+j}: 0x{self.state.registers[i+j]:08x}" for j in range(4) if i+j < len(self.state.registers)]
            print("  ".join(regs))

def make_instruction(opcode: int, rd: int = 0, rs: int = 0, rt: int = 0, address_or_operand: int = 0) -> int:
    """
    Create a 32-bit instruction from components.
    
    Format: oooo dddd ssss tttt aaaaaaaaaaaaaaaa
    Where:
        o = opcode (4 bits)
        d = destination register (4 bits)
        s = source register 1 (4 bits)
        t = source register 2 (4 bits)
        a = address or immediate value (16 bits)
    
    For CALL/BEQ, the address is 24 bits (no register fields).
    
    Args:
        opcode: 4-bit operation code
        rd: Destination register number
        rs: Source register 1 number
        rt: Source register 2 number
        address_or_operand: Address (for CALL/BEQ) or immediate value
        
    Returns:
        32-bit instruction word
    """
    return (opcode << 28) | (rd << 24) | (rs << 20) | (rt << 16) | (address_or_operand & 0xFFFF)

def test_simple_call_sequence():
    """
    Test Scenario 1: Simple call sequence (PUSH R1; CALL 0x100; RET)
    Tests basic function call and return mechanism.
    """
    print("\n" + "="*60)
    print("TEST: Simple Call Sequence")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Initialize R1 with a test value
    sim.state.registers[1] = 0x12345678
    
    # Program layout:
    # 0x0000: PUSH R1
    # 0x0004: CALL 0x100
    # 0x0008: HALT
    # 
    # 0x0100: RET
    program = [
        make_instruction(0b0100, rd=1),      # 0x0000: PUSH R1
        make_instruction(0b0001, address_or_operand=0x0100),  # 0x0004: CALL 0x100
        make_instruction(0b0011),            # 0x0008: HALT
        
        # Padding to reach 0x100 (fill memory with zeros)
        *([0] * ((0x100 // 4) - 3)),
        
        make_instruction(0b0010)             # 0x0100: RET
    ]
    
    sim.load_program(program)
    sim.run(max_steps=10)
    
    print("\nResults:")
    print(f"Final R1: 0x{sim.state.registers[1]:08x} (Expected: 0x12345678)")
    print(f"Final Stack: {[hex(x) for x in sim.state.stack]} (Expected: [])")
    print(f"Final PC: 0x{sim.state.pc:08x} (Expected: 0x0000000c)")
    
    # Print call/ret sequence from logs
    print("\nExecution Log:")
    for entry in sim.log:
        if "CALL" in entry or "RET" in entry or "PUSH" in entry or "POP" in entry:
            print(entry)

def test_nested_call_sequence():
    """
    Test Scenario 2: Nested calls (CALL func1; func1: CALL func2; RET)
    Tests function calls within functions and proper stack handling.
    """
    print("\n" + "="*60)
    print("TEST: Nested Call Sequence")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Initialize link register
    sim.state.registers[14] = 0
    
    # Program layout:
    # 0x0000: CALL func1 (0x100)
    # 0x0004: HALT
    # 
    # 0x0100: PUSH R14 (save return address)
    # 0x0104: CALL func2 (0x200)
    # 0x0108: POP R14
    # 0x010C: RET
    # 
    # 0x0200: RET (func2)
    program = [
        make_instruction(0b0001, address_or_operand=0x0100),  # 0x0000: CALL func1
        make_instruction(0b0011),            # 0x0004: HALT
        
        # Padding to reach 0x100
        *([0] * ((0x100 // 4) - 2)),
        
        # func1 at 0x0100
        make_instruction(0b0100, rd=14),     # 0x0100: PUSH R14 (link register)
        make_instruction(0b0001, address_or_operand=0x0200),  # 0x0104: CALL func2
        make_instruction(0b0101, rd=14),     # 0x0108: POP R14
        make_instruction(0b0010),            # 0x010C: RET
        
        # Padding to reach 0x200
        *([0] * ((0x200 // 4) - (0x010C // 4 + 1))),
        
        # func2 at 0x0200
        make_instruction(0b0010)             # 0x0200: RET
    ]
    
    sim.load_program(program)
    sim.run(max_steps=20)
    
    print("\nResults:")
    print(f"Final Stack: {[hex(x) for x in sim.state.stack]} (Expected: [])")
    print(f"Final PC: 0x{sim.state.pc:08x} (Expected: 0x00000008)")
    print(f"Final R14: 0x{sim.state.registers[14]:08x} (Expected: 0x00000000)")
    
    # Print call/ret sequence from logs
    print("\nExecution Log:")
    for entry in sim.log:
        if "CALL" in entry or "RET" in entry or "PUSH" in entry or "POP" in entry:
            print(entry)

def test_alu_operations():
    """
    Test Scenario 3: ALU operations (ADD R1, R2, R3; SUB R4, R1, R5)
    Tests basic arithmetic operations and flag settings.
    """
    print("\n" + "="*60)
    print("TEST: ALU Operations")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Initialize registers with test values
    sim.state.registers[2] = 5  # R2 = 5
    sim.state.registers[3] = 3  # R3 = 3
    sim.state.registers[5] = 2  # R5 = 2
    
    # Program layout:
    # 0x0000: ADD R1 = R2 + R3
    # 0x0004: SUB R4 = R1 - R5
    # 0x0008: HALT
    program = [
        make_instruction(0b1000, rd=1, rs=2, rt=3),  # ADD R1 = R2 + R3
        make_instruction(0b1001, rd=4, rs=1, rt=5),  # SUB R4 = R1 - R5
        make_instruction(0b0011)                     # HALT
    ]
    
    sim.load_program(program)
    sim.run(max_steps=10)
    
    print("\nResults:")
    print(f"R1 (5 + 3): {sim.state.registers[1]} (Expected: 8)")
    print(f"R4 (8 - 2): {sim.state.registers[4]} (Expected: 6)")
    print(f"Flags: Z={sim.state.flags['Z']}, N={sim.state.flags['N']}, C={sim.state.flags['C']}")
    
    # Print ALU operation logs
    print("\nExecution Log:")
    for entry in sim.log:
        if "ADD" in entry or "SUB" in entry:
            print(entry)

def test_edge_cases():
    """
    Test edge cases (empty stack POP)
    Tests error handling when operations encounter invalid conditions.
    """
    print("\n" + "="*60)
    print("TEST: Edge Cases")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Program layout:
    # 0x0000: POP R1 (should fail)
    # 0x0004: HALT
    program = [
        make_instruction(0b0101, rd=1),  # POP R1 (empty stack)
        make_instruction(0b0011)         # HALT
    ]
    
    print("Testing POP with empty stack (should raise exception)")
    try:
        sim.load_program(program)
        sim.run(max_steps=10)
    except Exception as e:
        print(f"Expected exception caught: {str(e)}")
    
    print("\nExecution Log:")
    for entry in sim.log:
        print(entry)

def test_factorial_program():
    """
    Test a factorial calculation program
    Tests recursive function implementation using the simulator.
    Calculates 5! (factorial of 5 = 5*4*3*2*1 = 120)
    """
    print("\n" + "="*60)
    print("TEST: Factorial Calculation (5!)")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Set up register 15 as constant 1 for comparison
    sim.state.registers[15] = 1
    
    # Set initial values
    sim.state.registers[1] = 5  # Input value (n)
    sim.state.registers[2] = 1  # Result (initially 1)
    sim.state.registers[14] = 0  # Link register (initialized to 0)

    program = [
        # Main program
        make_instruction(0b0001, address_or_operand=0x0020),  # 0x0000: CALL factorial
        make_instruction(0b0011),                             # 0x0004: HALT
        
        # Empty space for alignment
        0, 0, 0, 0, 0, 0,
        
        # Factorial function at 0x0020
        make_instruction(0b0100, rd=14),                      # 0x0020: PUSH R14 (link register)
        make_instruction(0b0111, rs=1, rt=15),                # 0x0024: CMP R1, R15 (compare with 1)
        make_instruction(0b0110, address_or_operand=0x0040),  # 0x0028: BEQ return_one (if R1 == 1)
        make_instruction(0b1010, rd=2, rs=2, rt=1),           # 0x002C: MUL R2 = R2 * R1
        make_instruction(0b1001, rd=1, rs=1, rt=15),          # 0x0030: SUB R1 = R1 - 1
        make_instruction(0b0001, address_or_operand=0x0020),  # 0x0034: CALL factorial
        make_instruction(0b0101, rd=14),                      # 0x0038: POP R14
        make_instruction(0b0010),                             # 0x003C: RET
        
        # Base case at 0x0040
        make_instruction(0b0101, rd=14),                      # 0x0040: POP R14
        make_instruction(0b0010)                              # 0x0044: RET
    ]
    
    sim.load_program(program)
    sim.run(max_steps=100)
    
    print("\nResults:")
    print(f"5! = {sim.state.registers[2]} (Expected: 120)")
    print(f"Final Stack: {[hex(x) for x in sim.state.stack]} (Expected: [])")
    print(f"Final PC: 0x{sim.state.pc:08x} (Expected: 0x0008)")

def test_all_alu_operations():
    """
    Test all ALU operations with various inputs
    Tests all arithmetic and logical operations with different bit patterns.
    """
    print("\n" + "="*60)
    print("TEST: All ALU Operations")
    print("="*60)
    
    sim = InstructionSetSimulator()
    
    # Initialize registers with test values
    sim.state.registers[1] = 0x0000000F  # 15 decimal
    sim.state.registers[2] = 0x00000005  # 5 decimal
    sim.state.registers[3] = 0xAAAAAAAA  # 101010... pattern
    sim.state.registers[4] = 0x55555555  # 010101... pattern
    
    program = [
        make_instruction(0b1000, rd=10, rs=1, rt=2),  # ADD R10 = R1 + R2
        make_instruction(0b1001, rd=11, rs=1, rt=2),  # SUB R11 = R1 - R2
        make_instruction(0b1010, rd=12, rs=1, rt=2),  # MUL R12 = R1 * R2
        make_instruction(0b1011, rd=13, rs=1, rt=2),  # DIV R13 = R1 / R2
        make_instruction(0b1100, rd=14, rs=3, rt=4),  # AND R14 = R3 & R4
        make_instruction(0b1101, rd=15, rs=3, rt=4),  # OR R15 = R3 | R4
        make_instruction(0b1110, rd=0, rs=3, rt=4),   # XOR R0 = R3 ^ R4
        make_instruction(0b0011)                      # HALT
    ]
    
    sim.load_program(program)
    sim.run()
    
    print("\nResults:")
    print(f"ADD: R10 = 0x{sim.state.registers[10]:08x} (Expected: 0x00000014)")  # 15 + 5 = 20 (0x14)
    print(f"SUB: R11 = 0x{sim.state.registers[11]:08x} (Expected: 0x0000000A)")  # 15 - 5 = 10 (0x0A)
    print(f"MUL: R12 = 0x{sim.state.registers[12]:08x} (Expected: 0x0000004B)")  # 15 * 5 = 75 (0x4B)
    print(f"DIV: R13 = 0x{sim.state.registers[13]:08x} (Expected: 0x00000003)")  # 15 / 5 = 3
    print(f"AND: R14 = 0x{sim.state.registers[14]:08x} (Expected: 0x00000000)")  # 101010... & 010101... = 0
    print(f"OR:  R15 = 0x{sim.state.registers[15]:08x} (Expected: 0xFFFFFFFF)")  # 101010... | 010101... = all 1's
    print(f"XOR: R0  = 0x{sim.state.registers[0]:08x} (Expected: 0xFFFFFFFF)")    # 101010... ^ 010101... = all 1's
    print(f"Flags: Z={sim.state.flags['Z']}, N={sim.state.flags['N']}, C={sim.state.flags['C']}")

def main():
    """
    Main entry point with test selection.
    Parses command line arguments to determine which tests to run.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', choices=['simple_call', 'nested_call', 'alu', 'edge', 'factorial', 'all_alu', 'all'], 
                       default='all',
                       help='Specify which test to run')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    args = parser.parse_args()
    
    # Run selected test(s) based on command line arguments
    if args.test == 'simple_call' or args.test == 'all':
        test_simple_call_sequence()
    if args.test == 'nested_call' or args.test == 'all':
        test_nested_call_sequence()
    if args.test == 'alu' or args.test == 'all':
        test_alu_operations()
    if args.test == 'edge' or args.test == 'all':
        test_edge_cases()
    if args.test == 'factorial' or args.test == 'all':
        test_factorial_program()
    if args.test == 'all_alu' or args.test == 'all':
        test_all_alu_operations()

if __name__ == "__main__":
    main()  # Execute main function when script is run directly