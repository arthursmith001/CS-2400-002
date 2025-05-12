import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from phase5 import Phase3Simulator

class InteractiveSimulatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Instruction Set Simulator")

        self.sim = Phase3Simulator()

        self._create_widgets()
        self._update_displays()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(control_frame, text="Run", command=self._run_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Step", command=self._step_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Reset", command=self._reset_program).pack(side=tk.LEFT, padx=5)

        load_frame = ttk.LabelFrame(main_frame, text="Load Test Program")
        load_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(load_frame, text="Single Call", command=self._load_single_call).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(load_frame, text="Nested Call", command=self._load_nested_call).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(load_frame, text="ALU Operation", command=self._load_alu).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(load_frame, text="Factorial Calculator", command=self._load_factorial).pack(side=tk.LEFT, padx=5, pady=5)

        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(display_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        state_frame = ttk.LabelFrame(left_frame, text="CPU State")
        state_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.pc_var = tk.StringVar(value="PC: 0x00000000")
        self.flags_var = tk.StringVar(value="Flags: {}")

        ttk.Label(state_frame, textvariable=self.pc_var).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(state_frame, textvariable=self.flags_var).pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(state_frame, text="Registers:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.register_display = scrolledtext.ScrolledText(state_frame, height=10)
        self.register_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(state_frame, text="Stack:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.stack_display = scrolledtext.ScrolledText(state_frame, height=5)
        self.stack_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(display_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        log_frame = ttk.LabelFrame(right_frame, text="Execution Log")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_display = scrolledtext.ScrolledText(log_frame, width=50)
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _update_displays(self):
        self.pc_var.set(f"PC: 0x{self.sim.state.pc:08X}")
        self.flags_var.set(f"Flags: {self.sim.state.flags}")

        self.register_display.delete(1.0, tk.END)
        for i in range(0, len(self.sim.state.registers), 4):
            regs = [
                f"R{i + j}: 0x{self.sim.state.registers[i + j]:08X}"
                for j in range(4) if (i + j) < len(self.sim.state.registers)
            ]
            self.register_display.insert(tk.END, "  ".join(regs) + "\n")

        self.stack_display.delete(1.0, tk.END)
        if self.sim.state.stack:
            for item in reversed(self.sim.state.stack):
                self.stack_display.insert(tk.END, f"0x{item:08X}\n")
        else:
            self.stack_display.insert(tk.END, "<empty>\n")

        self.log_display.delete(1.0, tk.END)
        for entry in self.sim.log[-50:]:
            self.log_display.insert(tk.END, entry + "\n")

    def _step_program(self):
        if self.sim.state.halted:
            return
        try:
            self.sim.fetch()
            self.sim.decode_execute()
            self._update_displays()
        except Exception as e:
            messagebox.showerror("Simulator Error", str(e))

    def _run_program(self):
        def run_step():
            if not self.sim.state.halted:
                try:
                    self.sim.fetch()
                    self.sim.decode_execute()
                    self._update_displays()
                    self.master.after(50, run_step)
                except Exception as e:
                    messagebox.showerror("Simulator Error", str(e))

        run_step()

    def _reset_program(self):
        self.sim.reset()
        self._update_displays()

    def _load_single_call(self):
        self.sim.reset()
        program = [
            self.sim.make_instruction(0b1101, rd=1, address_or_operand=42),  # MOV R1, #42
            self.sim.make_instruction(0b0100, rd=1),                         # CALL R1 (simulate a call)
            self.sim.make_instruction(0b0011),                               # HALT
            *([0] * ((0x100 // 4) - 3)),
            self.sim.make_instruction(0b1101, rd=2, address_or_operand=99),  # MOV R2, #99 (subroutine)
            self.sim.make_instruction(0b0010)                                # RET
        ]
        self.sim.load_program(program)
        self._update_displays()

    def _load_nested_call(self):
        self.sim.reset()
        program = [
            self.sim.make_instruction(0b1101, rd=1, address_or_operand=0x100),  # MOV R1, subroutine1 addr
            self.sim.make_instruction(0b0100, rd=1),                            # CALL subroutine1
            self.sim.make_instruction(0b0011),                                  # HALT
            *([0] * ((0x100 // 4) - 3)),
            self.sim.make_instruction(0b1101, rd=2, address_or_operand=123),    # MOV R2, #123
            self.sim.make_instruction(0b1101, rd=3, address_or_operand=0x200),  # MOV R3, subroutine2 addr
            self.sim.make_instruction(0b0100, rd=3),                            # CALL subroutine2
            self.sim.make_instruction(0b0010),                                  # RET
            *([0] * ((0x200 // 4) - (0x10C // 4 + 1))),
            self.sim.make_instruction(0b1101, rd=4, address_or_operand=255),    # MOV R4, #255
            self.sim.make_instruction(0b0010)                                   # RET
        ]
        self.sim.load_program(program)
        self._update_displays()

    def _load_alu(self):
        self.sim.reset()
        self.sim.state.registers[2] = 5
        self.sim.state.registers[3] = 3
        self.sim.state.registers[5] = 2
        program = [
            self.sim.make_instruction(0b1000, rd=1, rs=2, rt=3),
            self.sim.make_instruction(0b1001, rd=4, rs=1, rt=5),
            self.sim.make_instruction(0b0011)
        ]
        self.sim.load_program(program)
        self._update_displays()

    def _load_factorial(self):
        self.sim.reset()
        self.sim.state.registers[15] = 1
        self.sim.state.registers[1] = 5
        self.sim.state.registers[2] = 1
        self.sim.state.registers[14] = 0

        program = [
            self.sim.make_instruction(0b0001, address_or_operand=0x0020),
            self.sim.make_instruction(0b0011),
            *([0] * ((0x20 // 4) - 2)),
            self.sim.make_instruction(0b0100, rd=14),
            self.sim.make_instruction(0b0111, rs=1, rt=15),
            self.sim.make_instruction(0b0110, rs=1, address_or_operand=0x0020),
            self.sim.make_instruction(0b1010, rd=2, rs=2, rt=1),
            self.sim.make_instruction(0b1001, rd=1, rs=1, rt=15),
            self.sim.make_instruction(0b0110, rs=1, address_or_operand=0x0040),
            self.sim.make_instruction(0b0101, rd=14),
            self.sim.make_instruction(0b0010)
        ]

        self.sim.load_program(program)
        self._update_displays()

def main():
    root = tk.Tk()
    root.geometry("900x600")
    app = InteractiveSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
