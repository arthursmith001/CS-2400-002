import tkinter as tk
from tkinter import scrolledtext, ttk
import sys
import threading
import time

# Import from phase5.py
try:
    from phase5 import Core, MemoryController, NUM_CORES, NUM_THREADS_PER_CORE, make_instruction, format_instruction
except ImportError as e:
    print(f"Error importing from phase5.py: {e}")
    print("Make sure 'phase5.py' is in the same directory and has the required classes/functions.")
    sys.exit()


class InteractivePhase5SimulatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Interactive Phase 5 Multicore Simulator")
        
        # Create shared memory controller
        self.memory_controller = MemoryController()
        
        # Create cores
        self.cores = [Core(i, self.memory_controller) for i in range(NUM_CORES)]
        
        # Thread management
        self.core_threads = []
        self.running = False
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        
        # Example program for loading
        self.example_program = [
            make_instruction(0b1101, rd=1, address_or_operand=3),  # MOV R1, #3
            make_instruction(0b1101, rd=2, address_or_operand=5),  # MOV R2, #5
            make_instruction(0b1000, rd=0, rs=1, rt=2),           # ADD R0, R1, R2
            make_instruction(0b0011)                               # HALT
        ]
        
        # UI components
        self.core_tabs = None
        self.log_display = None
        self.memory_display = None
        self.status_bar = None
        
        self._create_widgets()
        
        # Load example program on all cores
        for core in self.cores:
            for thread_id in range(NUM_THREADS_PER_CORE):
                core.load_program(thread_id, self.example_program)
                
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
        
        # Main content area with splitters
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Core tabs panel (70% width)
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create notebook for core tabs
        self.core_tabs = ttk.Notebook(left_frame)
        self.core_tabs.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs for each core
        self.thread_frames = {}
        for core_id in range(NUM_CORES):
            core_frame = ttk.Frame(self.core_tabs)
            self.core_tabs.add(core_frame, text=f"Core {core_id}")
            
            # Create thread tabs inside core tab
            thread_notebook = ttk.Notebook(core_frame)
            thread_notebook.pack(fill=tk.BOTH, expand=True)
            
            for thread_id in range(NUM_THREADS_PER_CORE):
                thread_frame = ttk.Frame(thread_notebook)
                thread_notebook.add(thread_frame, text=f"Thread {thread_id}")
                
                # Pipeline status
                pipeline_frame = ttk.LabelFrame(thread_frame, text="Pipeline Status")
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
                
                # Register frame
                register_frame = ttk.LabelFrame(thread_frame, text="Registers")
                register_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Create register display with scrolling
                register_scroll = ttk.Frame(register_frame)
                register_scroll.pack(fill=tk.BOTH, expand=True)
                
                reg_display = scrolledtext.ScrolledText(register_scroll, height=10)
                reg_display.pack(fill=tk.BOTH, expand=True)
                
                # Create a dict to hold all variables for this thread
                self.thread_frames[(core_id, thread_id)] = {
                    'fetch': fetch_var,
                    'decode': decode_var,
                    'execute': execute_var,
                    'pc': pc_var,
                    'stall': stall_var,
                    'flush': flush_var,
                    'registers': reg_display
                }
                
        # Right side: Memory & Log panel (30% width)
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

    def _update_thread_display(self, core_id, thread_id):
        thread = self.cores[core_id].threads[thread_id]
        thread_vars = self.thread_frames[(core_id, thread_id)]
        
        # Update pipeline status
        thread_vars['fetch'].set(f"Fetch: {format_instruction(thread.pipeline['F'])}")
        thread_vars['decode'].set(f"Decode: {format_instruction(thread.pipeline['D'])}")
        thread_vars['execute'].set(f"Execute: {format_instruction(thread.pipeline['E'])}")
        
        # Update status indicators
        thread_vars['pc'].set(f"PC: 0x{thread.state.pc:04x}")
        thread_vars['stall'].set(f"Stall: {'Yes' if thread.stall_detected else 'No'}")
        thread_vars['flush'].set(f"Flush: {'Yes' if thread.flush_detected else 'No'}")
        
        # Update registers
        reg_text = ""
        for i in range(0, len(thread.state.registers), 4):
            reg_line = "  ".join([f"R{i+j}: 0x{thread.state.registers[i+j]:08x}" 
                                for j in range(4) if i+j < len(thread.state.registers)])
            reg_text += reg_line + "\n"
        
        thread_vars['registers'].delete(1.0, tk.END)
        thread_vars['registers'].insert(tk.END, reg_text)

    def _update_memory_display(self):
        memory_content = ""
        # Display first 20 memory locations that are non-zero
        count = 0
        for i in range(0, 1024, 4):
            value = self.memory_controller.read(i)
            if value != 0 or count < 10:  # Show at least 10 entries
                memory_content += f"0x{i:04x}: 0x{value:08x}\n"
                count += 1
            if count >= 20:
                break
                
        self.memory_display.delete(1.0, tk.END)
        self.memory_display.insert(tk.END, memory_content)

    def _update_log_display(self):
        log_content = ""
        for core in self.cores:
            for thread in core.threads:
                # Get the last 5 log entries for each thread
                thread_logs = thread.log[-5:] if thread.log else []
                for log in thread_logs:
                    log_content += log + "\n"
                
        self.log_display.delete(1.0, tk.END)
        self.log_display.insert(tk.END, log_content)
        self.log_display.see(tk.END)  # Scroll to see the latest logs

    def _update_all_displays(self):
        for core_id in range(NUM_CORES):
            for thread_id in range(NUM_THREADS_PER_CORE):
                self._update_thread_display(core_id, thread_id)
        
        self._update_memory_display()
        self._update_log_display()

    def _run_simulation(self):
        if self.running:
            return
            
        self.running = True
        self.pause_event.clear()
        self.stop_event.clear()
        
        # Start a thread for each core
        self.core_threads = []
        for core_id, core in enumerate(self.cores):
            t = threading.Thread(target=self._run_core, args=(core_id,))
            self.core_threads.append(t)
            t.start()
            
        # Update UI in a separate thread
        ui_thread = threading.Thread(target=self._update_ui_thread)
        ui_thread.daemon = True
        ui_thread.start()
        
        self.status_bar.config(text="Running simulation...")

    def _update_ui_thread(self):
        while self.running and not self.stop_event.is_set():
            self.master.after(100, self._update_all_displays)
            time.sleep(0.1)

    def _run_core(self, core_id):
        core = self.cores[core_id]
        
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue
                
            # Run one cycle on the core
            active = core.cycle()
            
            # If all threads are halted, stop this core
            if not active:
                break
                
            # Slow down simulation for visualization
            time.sleep(0.2)
            
        if core_id == 0:  # Only need to check once if all cores are done
            all_done = True
            for core in self.cores:
                for thread in core.threads:
                    if not thread.state.halted:
                        all_done = False
                        break
                        
            if all_done:
                self.master.after(0, self._simulation_complete)

    def _pause_simulation(self):
        if not self.running:
            return
            
        self.pause_event.set()
        self.status_bar.config(text="Simulation paused")

    def _step_simulation(self):
        # If not running, we can do a single step
        if not self.running:
            for core in self.cores:
                core.cycle()
            self._update_all_displays()
            
        # If running but paused, do a single step
        elif self.pause_event.is_set():
            self.pause_event.clear()
            time.sleep(0.1)  # Allow core to take one step
            self.pause_event.set()
            self._update_all_displays()

    def _stop_simulation(self):
        if not self.running:
            return
            
        self.stop_event.set()
        self.pause_event.clear()
        
        # Wait for all threads to finish
        for t in self.core_threads:
            t.join(timeout=1.0)
            
        self.running = False
        self.status_bar.config(text="Simulation stopped")
        self._update_all_displays()

    def _reset_simulation(self):
        # Stop any running simulation
        if self.running:
            self._stop_simulation()
            
        # Create new cores and memory controller
        self.memory_controller = MemoryController()
        self.cores = [Core(i, self.memory_controller) for i in range(NUM_CORES)]
        
        # Load example program on all cores
        for core in self.cores:
            for thread_id in range(NUM_THREADS_PER_CORE):
                core.load_program(thread_id, self.example_program)
                
        self._update_all_displays()
        self.status_bar.config(text="Simulation reset")

    def _simulation_complete(self):
        self.running = False
        self.status_bar.config(text="Simulation complete")
        self._update_all_displays()


def main():
    root = tk.Tk()
    root.geometry("1200x800")
    gui = InteractivePhase5SimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()