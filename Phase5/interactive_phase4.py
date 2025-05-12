import tkinter as tk
from tkinter import scrolledtext, ttk
import sys
import threading
import time

# Import from phase5.py
try:
    from phase5 import Phase4Simulator, make_instruction, format_instruction
except ImportError as e:
    print(f"Error importing from phase5.py: {e}")
    print("Make sure 'phase5.py' is in the same directory and has the required classes/functions.")
    sys.exit()


class InteractivePhase4SimulatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Interactive Phase 4 Pipelined Simulator")
        
        # Create simulator
        self.simulator = Phase4Simulator()
        
        # Example program for loading
        self.example_program = [
            make_instruction(0b1101, rd=1, address_or_operand=3),  # MOV R1, #3
            make_instruction(0b1101, rd=2, address_or_operand=5),  # MOV R2, #5
            make_instruction(0b1000, rd=0, rs=1, rt=2),           # ADD R0, R1, R2
            make_instruction(0b0011)                               # HALT
        ]
        
        # Thread management
        self.simulator_thread = None
        self.running = False
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        
        # UI components
        self.pipeline_vars = {}
        self.register_display = None
        self.memory_display = None
        self.log_display = None
        self.status_bar = None
        
        self._create_widgets()
        
        # Load example program
        self.simulator.load_program(self.example_program)
        # Add initialization log entry
        self.simulator.log.append("Program loaded. Click 'Step' or 'Run' to start execution.")
        
        # Initial UI update
        self._update_all_displays()

    def _create_widgets(self):
        # Main frame layout
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Control buttons
        ttk.Button(control_frame, text="Run", command=self._run_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Pause", command=self._pause_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Step", command=self._step_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop", command=self._stop_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Reset", command=self._reset_simulation).pack(side=tk.LEFT, padx=5)
        
        # Program loading frame
        program_frame = ttk.LabelFrame(main_frame, text="Program Load Options")
        program_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Program loading options
        ttk.Button(program_frame, text="Load Example 1 (Basic)", 
                   command=lambda: self._load_program(1)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(program_frame, text="Load Example 2 (Data Hazards)", 
                   command=lambda: self._load_program(2)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(program_frame, text="Load Example 3 (Control Hazards)", 
                   command=lambda: self._load_program(3)).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Main content area with splitters
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Pipeline status and registers (60% width)
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Pipeline status display
        pipeline_frame = ttk.LabelFrame(left_frame, text="Pipeline Status")
        pipeline_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pipeline stages
        stages_frame = ttk.Frame(pipeline_frame)
        stages_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(stages_frame, text="Fetch:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(stages_frame, text="Decode:").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(stages_frame, text="Execute:").grid(row=2, column=0, sticky=tk.W, padx=5)
        
        fetch_var = tk.StringVar(value="-")
        decode_var = tk.StringVar(value="-")
        execute_var = tk.StringVar(value="-")
        
        ttk.Label(stages_frame, textvariable=fetch_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(stages_frame, textvariable=decode_var).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(stages_frame, textvariable=execute_var).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Status indicators
        status_frame = ttk.Frame(pipeline_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        pc_var = tk.StringVar(value="PC: 0x0000")
        stall_var = tk.StringVar(value="Stall: No")
        flush_var = tk.StringVar(value="Flush: No")
        
        ttk.Label(status_frame, textvariable=pc_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=stall_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=flush_var).pack(side=tk.LEFT, padx=5)
        
        # Save pipeline variables for updating
        self.pipeline_vars = {
            'fetch': fetch_var,
            'decode': decode_var,
            'execute': execute_var,
            'pc': pc_var,
            'stall': stall_var,
            'flush': flush_var
        }
        
        # Flags frame
        flags_frame = ttk.Frame(pipeline_frame)
        flags_frame.pack(fill=tk.X, padx=5, pady=5)
        
        z_flag_var = tk.StringVar(value="Z: False")
        n_flag_var = tk.StringVar(value="N: False")
        c_flag_var = tk.StringVar(value="C: False")
        
        ttk.Label(flags_frame, textvariable=z_flag_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(flags_frame, textvariable=n_flag_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(flags_frame, textvariable=c_flag_var).pack(side=tk.LEFT, padx=5)
        
        self.pipeline_vars.update({
            'z_flag': z_flag_var,
            'n_flag': n_flag_var,
            'c_flag': c_flag_var
        })
        
        # Register frame
        register_frame = ttk.LabelFrame(left_frame, text="Registers")
        register_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Register display with scrolling
        self.register_display = scrolledtext.ScrolledText(register_frame, height=10)
        self.register_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right side: Memory & Log panel (40% width)
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))
        
        # Memory display
        memory_frame = ttk.LabelFrame(right_frame, text="Memory")
        memory_frame.pack(fill=tk.BOTH, expand=True)
        
        self.memory_display = scrolledtext.ScrolledText(memory_frame, width=30, height=10)
        self.memory_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log display
        log_frame = ttk.LabelFrame(right_frame, text="Execution Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_display = scrolledtext.ScrolledText(log_frame, width=30, height=10)
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

    def _update_pipeline_display(self):
        # Update pipeline status
        self.pipeline_vars['fetch'].set(f"{format_instruction(self.simulator.pipeline['F'])}")
        self.pipeline_vars['decode'].set(f"{format_instruction(self.simulator.pipeline['D'])}")
        self.pipeline_vars['execute'].set(f"{format_instruction(self.simulator.pipeline['E'])}")
        
        # Update status indicators
        self.pipeline_vars['pc'].set(f"PC: 0x{self.simulator.state.pc:04x}")
        self.pipeline_vars['stall'].set(f"Stall: {'Yes' if self.simulator.stall_detected else 'No'}")
        self.pipeline_vars['flush'].set(f"Flush: {'Yes' if self.simulator.flush_detected else 'No'}")
        
        # Update flags
        self.pipeline_vars['z_flag'].set(f"Z: {self.simulator.state.flags['Z']}")
        self.pipeline_vars['n_flag'].set(f"N: {self.simulator.state.flags['N']}")
        self.pipeline_vars['c_flag'].set(f"C: {self.simulator.state.flags['C']}")

    def _update_register_display(self):
        reg_text = ""
        for i in range(0, len(self.simulator.state.registers), 4):
            reg_line = "  ".join([f"R{i+j}: 0x{self.simulator.state.registers[i+j]:08x}" 
                                for j in range(4) if i+j < len(self.simulator.state.registers)])
            reg_text += reg_line + "\n"
        
        self.register_display.delete(1.0, tk.END)
        self.register_display.insert(tk.END, reg_text)

    def _update_memory_display(self):
        memory_content = ""
        # Display first 20 memory locations that are non-zero
        count = 0
        for addr in sorted(self.simulator.state.memory.keys()):
            value = self.simulator.state.memory[addr]
            if value != 0 or count < 10:  # Show at least 10 entries
                memory_content += f"0x{addr:04x}: 0x{value:08x}\n"
                count += 1
            if count >= 20:
                break
                
        self.memory_display.delete(1.0, tk.END)
        self.memory_display.insert(tk.END, memory_content)

    def _update_log_display(self):
        # Get the last 20 log entries
        log_entries = self.simulator.log[-20:] if self.simulator.log else []
        log_content = "\n".join(log_entries)
        
        self.log_display.delete(1.0, tk.END)
        self.log_display.insert(tk.END, log_content)
        self.log_display.see(tk.END)  # Scroll to see the latest logs

    def _update_all_displays(self):
        self._update_pipeline_display()
        self._update_register_display()
        self._update_memory_display()
        self._update_log_display()

    def _load_program(self, example_num):
        # Stop any running simulation
        if self.running:
            self._stop_simulation()
        
        # Reset simulator
        self.simulator = Phase4Simulator()
        
        if example_num == 1:
            # Basic program
            program = [
                make_instruction(0b1101, rd=1, address_or_operand=3),  # MOV R1, #3
                make_instruction(0b1101, rd=2, address_or_operand=5),  # MOV R2, #5
                make_instruction(0b1000, rd=0, rs=1, rt=2),           # ADD R0, R1, R2
                make_instruction(0b0011)                               # HALT
            ]
            self.status_bar.config(text="Loaded Basic Program")
            description = "Basic Program loaded: MOV R1, #3; MOV R2, #5; ADD R0, R1, R2; HALT"
            
        elif example_num == 2:
            # Program with data hazards
            program = [
                make_instruction(0b1101, rd=1, address_or_operand=10),  # MOV R1, #10
                make_instruction(0b1000, rd=2, rs=1, rt=1),             # ADD R2, R1, R1 (data hazard with R1)
                make_instruction(0b1000, rd=3, rs=2, rt=1),             # ADD R3, R2, R1 (data hazard with R2)
                make_instruction(0b0011)                                # HALT
            ]
            self.status_bar.config(text="Loaded Program with Data Hazards")
            description = "Data Hazard Program loaded: MOV R1, #10; ADD R2, R1, R1; ADD R3, R2, R1; HALT"
            
        elif example_num == 3:
            # Program with control hazards
            program = [
                make_instruction(0b1101, rd=1, address_or_operand=0),   # MOV R1, #0
                make_instruction(0b1101, rd=2, address_or_operand=10),  # MOV R2, #10
                make_instruction(0b0111, rs=1, rt=2),                   # CMP R1, R2
                make_instruction(0b0110, rs=1, address_or_operand=12),  # BEQ R1, #12 (branch if R1==0)
                make_instruction(0b1101, rd=3, address_or_operand=20),  # MOV R3, #20
                make_instruction(0b0011)                                # HALT
            ]
            self.status_bar.config(text="Loaded Program with Control Hazards")
            description = "Control Hazard Program loaded: MOV R1, #0; MOV R2, #10; CMP R1, R2; BEQ R1, #12; MOV R3, #20; HALT"
            
        self.simulator.load_program(program)
        
        # Add informative log entries
        self.simulator.log = []  # Clear previous logs
        self.simulator.log.append(f"Program loaded: Example {example_num}")
        self.simulator.log.append(description)
        self.simulator.log.append("Click 'Step' or 'Run' to start execution")
        
        # Initialize the pipeline with the first instruction
        self.simulator.fetch()  # This fills the F stage with the first instruction
        
        self._update_all_displays()

    def _run_simulation(self):
        if self.running:
            return
            
        self.running = True
        self.pause_event.clear()
        self.stop_event.clear()
        
        # Start the simulation thread
        self.simulator_thread = threading.Thread(target=self._run_simulation_thread)
        self.simulator_thread.daemon = True
        self.simulator_thread.start()
        
        self.status_bar.config(text="Running simulation...")

    def _run_simulation_thread(self):
        cycle_count = 0
        max_cycles = 100  # Prevent infinite loops
        
        while not self.stop_event.is_set() and cycle_count < max_cycles:
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue
                
            # Check if simulation is complete
            if (self.simulator.pipeline['F'] is None and 
                self.simulator.pipeline['D'] is None and 
                self.simulator.pipeline['E'] is None):
                break
                
            # Run one cycle
            self.simulator.pipeline_step()
            cycle_count += 1
            
            # Update UI
            self.master.after(0, self._update_all_displays)
            
            # Slow down simulation for visualization
            time.sleep(0.5)
            
        # Simulation complete
        self.running = False
        if cycle_count >= max_cycles:
            self.master.after(0, lambda: self.status_bar.config(text="Simulation stopped (max cycles reached)"))
        else:
            self.master.after(0, lambda: self.status_bar.config(text="Simulation complete"))

    def _pause_simulation(self):
        if not self.running:
            return
            
        self.pause_event.set()
        self.status_bar.config(text="Simulation paused")

    def _step_simulation(self):
        # If not running, we can do a single step
        if not self.running:
            if (self.simulator.pipeline['F'] is None and 
                self.simulator.pipeline['D'] is None and 
                self.simulator.pipeline['E'] is None):
                self.status_bar.config(text="Simulation complete - no more steps")
                return
                
            self.simulator.pipeline_step()
            self._update_all_displays()
            
        # If running but paused, do a single step
        elif self.pause_event.is_set():
            self.pause_event.clear()
            time.sleep(0.1)  # Allow simulation to take one step
            self.pause_event.set()
            self._update_all_displays()

    def _stop_simulation(self):
        if not self.running:
            return
            
        self.stop_event.set()
        self.pause_event.clear()
        
        # Wait for thread to finish
        if self.simulator_thread:
            self.simulator_thread.join(timeout=1.0)
            
        self.running = False
        self.status_bar.config(text="Simulation stopped")
        self._update_all_displays()

    def _reset_simulation(self):
        # Stop any running simulation
        if self.running:
            self._stop_simulation()
            
        # Create new simulator
        self.simulator = Phase4Simulator()
        
        # Load example program
        self.simulator.load_program(self.example_program)
        
        # Add informative log entry
        self.simulator.log = ["Simulator reset. Click 'Step' or 'Run' to start execution."]
        
        # Initialize the pipeline with the first instruction
        self.simulator.fetch()  # This fills the F stage with the first instruction
                
        self._update_all_displays()
        self.status_bar.config(text="Simulation reset")


def main():
    root = tk.Tk()
    root.geometry("1000x700")
    root.title("Interactive Phase 4 Pipelined Simulator")
    gui = InteractivePhase4SimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()